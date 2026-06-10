# movimiento_vehiculo.py
import time
import math

class ConfigVehiculo:
    def __init__(self):
        # Geometría del carro
        self.distancia_entre_ejes_cm = 14.5
        self.ancho_via_cm = 16
        self.perimetro_rueda = 10.9

        # Servo de dirección
        self.servo_centro = 45
        self.servo_izquierda_max = 90
        self.servo_derecha_max = 0
        self.paso_servo = 10
        self.angulo_rueda_max_deg = 35.0
        self.tamano_celda_cm = 20.0

        # Calibraciones
        self.factor_distancia = 1.0     # corrige encoder
        self.factor_angulo = 1.0        # corrige giro estimado o IMU
        self.offset_angulo = 0.0

        # Tolerancias
        self.tolerancia_distancia_cm = 0.5
        self.tolerancia_angulo_deg = 3.0

        # Movimiento
        self.velocidad_crucero = 900
        self.velocidad_giro = 700


class MovimientoDelVehiculo:
    def __init__(self, motor, servo, encoder=None, imu=None, config=None):
        self.motor = motor
        self.servo = servo
        self.encoder = encoder
        self.imu = imu
        self.cfg = config if config else ConfigVehiculo()

        # Estado odométrico estimado
        self.x_cm = 0.0
        self.y_cm = 0.0
        self.heading_deg = 0.0

        self._distancia_anterior_cm = 0.0

    # -------------------------
    # DIRECCIÓN
    # -------------------------
    def set_direccion_deg(self, direccion_deg, suave=False, paso=2, delay_ms=40):
        servo_destino = self.direccion_deg_a_servo(direccion_deg)
        if suave:
            self.mover_direccion_suave(servo_destino, paso=paso, delay_ms=delay_ms)
        else:
            self.servo.mover(servo_destino, espera=False)

    def mover_direccion_suave(self, angulo_destino, paso=2, delay_ms=50):
        actual = self.servo.angulo if self.servo.angulo is not None else self.cfg.servo_centro
        if actual < angulo_destino:
            while actual < angulo_destino:
                actual = min(actual + paso, angulo_destino)
                self.servo.mover(actual, espera=False)
                time.sleep_ms(delay_ms)
        else:
            while actual > angulo_destino:
                actual = max(actual - paso, angulo_destino)
                self.servo.mover(actual, espera=False)
                time.sleep_ms(delay_ms)

    # -------------------------
    # DISTANCIA / ÁNGULO
    # -------------------------
    def distancia_encoder_cm(self):
        if not self.encoder:
            return 0.0
        distancia = self.encoder.vueltas() * self.config.perimetro_rueda
        return distancia

    def angulo_imu_deg(self):
        if not self.imu:
            return self.heading_deg
        angulo, _ = self.imu.actualizar_orientacion()
        return (angulo * self.cfg.factor_angulo) + self.cfg.offset_angulo

    def reset_odometria(self):
        self.x_cm = 0.0
        self.y_cm = 0.0
        self.heading_deg = 0.0
        self._distancia_anterior_cm = 0.0

        if self.encoder:
            self.encoder.reset_encoder()

        if self.imu:
            self.imu.angulo_z = 0.0

    def actualizar_odometria(self):
        distancia_total = self.distancia_encoder_cm()
        delta_d = distancia_total - self._distancia_anterior_cm
        self._distancia_anterior_cm = distancia_total

        if self.imu:
            self.heading_deg = self.angulo_imu_deg()

        heading_rad = math.radians(self.heading_deg)
        self.x_cm += delta_d * math.cos(heading_rad)
        self.y_cm += delta_d * math.sin(heading_rad)

        return self.x_cm, self.y_cm, self.heading_deg

    # -------------------------
    # GEOMETRÍA DE GIRO
    # -------------------------        
    def servo_a_direccion_deg(self, servo_angulo):
        centro = self.cfg.servo_centro
        izq = self.cfg.servo_izquierda_max
        der = self.cfg.servo_derecha_max
        rueda_max = self.cfg.angulo_rueda_max_deg
        servo_angulo = max(der, min(izq, servo_angulo))
        if servo_angulo >= centro:
            tramo = izq - centro
            if tramo == 0:
                return 0.0
            return ((servo_angulo - centro) / tramo) * rueda_max
        tramo = centro - der
        if tramo == 0:
            return 0.0
        return -((centro - servo_angulo) / tramo) * rueda_max

    def direccion_deg_a_servo(self, direccion_deg):
        """
        Convierte un ángulo real de rueda (en grados) al ángulo del servo.
        - positivo  -> izquierda
        - negativo  -> derecha
        """
        centro = self.cfg.servo_centro
        izq = self.cfg.servo_izquierda_max
        der = self.cfg.servo_derecha_max
        rueda_max = self.cfg.angulo_rueda_max_deg

        if rueda_max <= 0:
            return centro

        direccion_deg = max(-rueda_max, min(rueda_max, direccion_deg))

        if direccion_deg >= 0:
            tramo = izq - centro
            if tramo == 0:
                return centro
            servo = centro + (direccion_deg / rueda_max) * tramo
        else:
            tramo = centro - der
            if tramo == 0:
                return centro
            servo = centro - (abs(direccion_deg) / rueda_max) * tramo

        return int(round(servo))

    # -------------------------
    # MOVIMIENTOS
    # -------------------------
    def avanzar_distancia(self, distancia_cm, velocidad=None):
        if velocidad is None:
            velocidad = self.cfg.velocidad_crucero

        if self.encoder:
            self.encoder.reset_encoder()

        self.motor.adelante(velocidad)

        while True:
            if self.encoder:
                self.encoder.actualizar()
                d = self.distancia_encoder_cm()
                print("distancia: ", d)
                self.actualizar_odometria()
                if d >= distancia_cm - self.cfg.tolerancia_distancia_cm:
                    break
            else:
                break

            time.sleep_ms(20)

        self.motor.detener()
        self.centrar_direccion()

    def retroceder_distancia(self, distancia_cm, velocidad=None):
        if velocidad is None:
            velocidad = self.cfg.velocidad_crucero

        if self.encoder:
            self.encoder.reset_encoder()

        self.motor.atras(velocidad)

        while True:
            if self.encoder:
                self.encoder.actualizar()
                d = abs(self.distancia_encoder_cm())
                self.actualizar_odometria()
                if d >= distancia_cm - self.cfg.tolerancia_distancia_cm:
                    break
            else:
                break

            time.sleep_ms(20)

        self.motor.detener()
        self.centrar_direccion()