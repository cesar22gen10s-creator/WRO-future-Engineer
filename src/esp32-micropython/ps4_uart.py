import time


class EstadoPS4UART:
    DPAD_ARRIBA    = 1
    DPAD_ABAJO     = 2
    DPAD_DERECHA   = 4
    DPAD_IZQUIERDA = 8

    BTN_X          = 1
    BTN_CIRCULO    = 2
    BTN_CUADRADO   = 4
    BTN_TRIANGULO  = 8
    BTN_L2         = 64
    BTN_R2         = 128

    def __init__(self, conectado, stick, flechas, botones, gatillo_izq, gatillo_der):
        self.conectado = conectado
        self.stick = stick
        self.flechas = flechas
        self.botones = botones
        self.gatillo_izq = gatillo_izq
        self.gatillo_der = gatillo_der

    def __repr__(self):
        return (
            "EstadoPS4UART(conectado={}, stick={}, flechas={}, botones={}, "
            "gatillo_izq={}, gatillo_der={})"
        ).format(
            self.conectado,
            self.stick,
            self.flechas,
            self.botones,
            self.gatillo_izq,
            self.gatillo_der,
        )


class ControlUARTVehiculo:
    def __init__(
        self,
        uart,
        vehiculo,
        velocidad_max=1023,
        stick_min=-511,
        stick_max=512,
        gatillo_max=1020,
        zona_muerta_stick=25,
        zona_muerta_gatillo=15,
        paso_servo=3,
        paso_motor=40,
        centrar_al_soltar=True,
    ):
        self.uart = uart
        self.vehiculo = vehiculo
        self.motor = vehiculo.motor
        self.cfg = vehiculo.cfg

        self.velocidad_max = velocidad_max
        self.stick_min = stick_min
        self.stick_max = stick_max
        self.gatillo_max = gatillo_max
        self.zona_muerta_stick = zona_muerta_stick
        self.zona_muerta_gatillo = zona_muerta_gatillo

        self.paso_servo = paso_servo
        self.paso_motor = paso_motor
        self.centrar_al_soltar = centrar_al_soltar

        self._buffer = b""
        self.ultimo_estado = None
        self._ultimo_paquete_ms = time.ticks_ms()

        # Objetivos persistentes
        self.objetivo_direccion_deg = 0.0
        self.objetivo_velocidad = 0
        self.objetivo_sentido = "adelante"

        # Último comando realmente enviado al motor
        self._velocidad_aplicada = None
        self._sentido_aplicado = None

    # ======================================================
    # Utilidades
    # ======================================================
    def _clamp(self, valor, minimo, maximo):
        if valor < minimo:
            return minimo
        if valor > maximo:
            return maximo
        return valor

    def _map_presion_a_velocidad(self, presion):
        presion = self._clamp(int(presion), 0, self.gatillo_max)

        if presion <= self.zona_muerta_gatillo:
            return 0
        velocidad = presion
        return int(velocidad)

    def _normalizar_stick(self, stick):
        stick = self._clamp(int(stick), self.stick_min, self.stick_max)

        if abs(stick) <= self.zona_muerta_stick:
            return 0.0

        if stick < 0:
            return stick / abs(self.stick_min)
        return stick / self.stick_max

    def _direccion_objetivo_deg_desde_stick(self, stick):
        # En tu geometría:
        #   +direccion_deg = izquierda
        #   -direccion_deg = derecha
        # En el stick:
        #   negativo = izquierda
        #   positivo = derecha
        normalizado = self._normalizar_stick(stick)
        return -normalizado * self.cfg.angulo_rueda_max_deg

    # ======================================================
    # UART
    # ======================================================
    def _extraer_lineas_uart(self):
        lineas = []

        while self.uart.any():
            chunk = self.uart.read()
            if not chunk:
                break
            self._buffer += chunk

        while b"\n" in self._buffer:
            linea, self._buffer = self._buffer.split(b"\n", 1)
            linea = linea.strip()
            if linea:
                lineas.append(linea)

        return lineas

    def _parsear_linea(self, linea_bytes):
        try:
            linea = linea_bytes.decode("utf-8").strip()
        except Exception:
            return None

        partes = linea.split(",")

        if len(partes) != 8:
            return None

        if partes[0] != "P":
            return None

        try:
            conectado = int(partes[1])
            stick = int(partes[2])
            flechas = int(partes[3])
            botones = int(partes[4])
            gatillo_izq = int(partes[6])
            gatillo_der = int(partes[7])
        except ValueError:
            return None

        return EstadoPS4UART(
            conectado=conectado,
            stick=stick,
            flechas=flechas,
            botones=botones,
            gatillo_izq=gatillo_izq,
            gatillo_der=gatillo_der,
        )

    def leer_ultimo_estado(self):
        ultimo = None

        for linea in self._extraer_lineas_uart():
            estado = self._parsear_linea(linea)
            if estado is not None:
                ultimo = estado

        if ultimo is not None:
            self.ultimo_estado = ultimo
            self._ultimo_paquete_ms = time.ticks_ms()

        return ultimo

    # ======================================================
    # Objetivos persistentes
    # ======================================================
    def _actualizar_objetivos_desde_estado(self, estado):
        if estado is None:
            return

        # Dirección retenida
        self.objetivo_direccion_deg = self._direccion_objetivo_deg_desde_stick(estado.stick)

        # Tracción retenida
        vel_adelante = self._map_presion_a_velocidad(estado.gatillo_der)
        vel_atras = self._map_presion_a_velocidad(estado.gatillo_izq)

        neto = vel_adelante - vel_atras

        if neto > 0:
            self.objetivo_velocidad = neto
            self.objetivo_sentido = "adelante"
        elif neto < 0:
            self.objetivo_velocidad = abs(neto)
            self.objetivo_sentido = "atras"
        else:
            self.objetivo_velocidad = 0

    # ======================================================
    # Dirección
    # ======================================================
    def _mover_direccion_un_paso(self):
        direccion_objetivo_deg = self.objetivo_direccion_deg

        if direccion_objetivo_deg == 0.0 and not self.centrar_al_soltar:
            return

        servo_actual = (
            self.vehiculo.servo.angulo
            if self.vehiculo.servo.angulo is not None
            else self.cfg.servo_centro
        )

        servo_objetivo = self.vehiculo.direccion_deg_a_servo(direccion_objetivo_deg)

        if servo_actual < servo_objetivo:
            servo_nuevo = min(servo_actual + self.paso_servo, servo_objetivo)
        elif servo_actual > servo_objetivo:
            servo_nuevo = max(servo_actual - self.paso_servo, servo_objetivo)
        else:
            servo_nuevo = servo_actual

        if servo_nuevo != servo_actual:
            self.vehiculo.servo.mover(servo_nuevo, espera=False)

    # ======================================================
    # Motor
    # ======================================================
    def _aplicar_objetivo_motor(self, forzar=False):
        velocidad = self.objetivo_velocidad

        if velocidad == 0:
            direccion = self.motor.direccion_actual if self.motor.direccion_actual else "adelante"
        else:
            direccion = self.objetivo_sentido

        if (
            not forzar
            and self._velocidad_aplicada == velocidad
            and self._sentido_aplicado == direccion
        ):
            return

        self.motor.acelerar(
            velocidad,
            direccion=direccion,
            paso=self.paso_motor,
            delay_ms=0,
        )

        self._velocidad_aplicada = velocidad
        self._sentido_aplicado = direccion

    # ======================================================
    # Loop principal
    # ======================================================
    def actualizar(self, debug=False):
        estado_nuevo = self.leer_ultimo_estado()

        if estado_nuevo is not None:
            self._actualizar_objetivos_desde_estado(estado_nuevo)

            if debug:
                print("NUEVO:", estado_nuevo)
                print(
                    "OBJETIVOS -> direccion_deg:",
                    self.objetivo_direccion_deg,
                    "velocidad:",
                    self.objetivo_velocidad,
                    "sentido:",
                    self.objetivo_sentido,
                )

        # Seguridad opcional
        ahora = time.ticks_ms()
        dt = time.ticks_diff(ahora, self._ultimo_paquete_ms)

        # Ejecuta SIEMPRE los objetivos retenidos
        self._aplicar_objetivo_motor()
        self._mover_direccion_un_paso()

    def detener_y_centrar(self):
        self.objetivo_velocidad = 0
        self.objetivo_direccion_deg = 0.0
        self._aplicar_objetivo_motor(forzar=True)

        while True:
            actual = (
                self.vehiculo.servo.angulo
                if self.vehiculo.servo.angulo is not None
                else self.cfg.servo_centro
            )
            if actual == self.cfg.servo_centro:
                break
            self._mover_direccion_un_paso()
            time.sleep_ms(10)