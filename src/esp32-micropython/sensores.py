import time
import uasyncio  # type: ignore

import config
import estado as contratos
import hardware
import utilidades


def _ahora_ms():
    return time.ticks_ms()


def _calcular_rpm(delta, intervalo_ms, pasos_por_vuelta):
    if intervalo_ms is None:
        return None
    if (
        not utilidades.numero_finito(delta)
        or not utilidades.numero_finito(intervalo_ms)
        or not utilidades.numero_finito(pasos_por_vuelta)
        or intervalo_ms <= 0
        or pasos_por_vuelta <= 0
    ):
        raise ValueError("datos invalidos para calcular RPM")
    rpm = (
        config.SIGNO_RPM_ENCODER
        * delta
        * 60000.0
        / (pasos_por_vuelta * intervalo_ms)
    )
    return 0.0 if rpm == 0 else rpm


async def leer_imu(sistema):
    muestra = sistema["sensores"]["imu"]
    iniciado = False
    while True:
        if not iniciado:
            try:
                hardware.imu.iniciar(rango=250)
                hardware.imu.calibrar_bias_gyro(muestras=150, delay_ms=3)
                iniciado = True
            except Exception as exc:
                contratos.publicar_error(muestra, exc, _ahora_ms())
                await uasyncio.sleep_ms(1000)
                continue
        try:
            heading, gz = hardware.imu.actualizar_orientacion()
            if not utilidades.numero_finito(heading) or not utilidades.numero_finito(gz):
                raise ValueError("IMU produjo un valor no finito")
            heading = utilidades.normalizar_angulo(heading)
            contratos.publicar_imu(muestra, heading, gz, _ahora_ms())
        except Exception as exc:
            contratos.publicar_error(muestra, exc, _ahora_ms())
            iniciado = False
            await uasyncio.sleep_ms(250)
            continue
        await uasyncio.sleep_ms(config.PERIODO_IMU_MS)


async def _leer_un_sonar(sensor, muestra):
    try:
        valor = sensor.leer_cm()
        if valor is None:
            # El timeout del eco significa que no hay obstaculo dentro del
            # alcance; es informacion necesaria para detectar una apertura.
            limite = getattr(sensor, "distancia_max_cm", config.SONAR_MAX_CM)
            contratos.publicar_muestra(
                muestra,
                limite,
                _ahora_ms(),
                fuera_rango=True,
            )
            return
        if not utilidades.numero_finito(valor) or valor <= 0:
            raise ValueError("distancia sonar invalida")
        contratos.publicar_muestra(muestra, valor, _ahora_ms())
    except Exception as exc:
        contratos.publicar_error(muestra, exc, _ahora_ms())


async def leer_sonares(sistema):
    buzones = sistema["sensores"]["sonar"]
    canales = (
        ("frontal", hardware.sonar_frontal),
        ("izquierdo", hardware.sonar_izquierdo),
        ("derecho", hardware.sonar_derecho),
    )
    while True:
        for nombre, sensor in canales:
            await _leer_un_sonar(sensor, buzones[nombre])
            await uasyncio.sleep_ms(config.SEPARACION_SONARES_MS)
        await uasyncio.sleep_ms(config.PERIODO_SONAR_MS)


def registrar_estado_inicial_tofs(sistema, errores, ahora_ms=None):
    ahora_ms = _ahora_ms() if ahora_ms is None else ahora_ms
    for nombre, error in errores.items():
        contratos.publicar_error(sistema["sensores"]["tof"][nombre], error, ahora_ms, fuera_servicio=True)


async def leer_tofs(sistema):
    buzones = sistema["sensores"]["tof"]
    nombres = ("frontal", "izquierdo", "derecho")
    ahora = _ahora_ms()
    ultima_muestra = {nombre: ahora for nombre in nombres}
    ultimo_reinicio = {nombre: (ahora if hardware.obtener_tof(nombre) is None else time.ticks_add(ahora, -config.TOF_BACKOFF_REINICIO_MS)) for nombre in nombres}

    while True:
        for nombre in nombres:
            ahora = _ahora_ms()
            muestra = buzones[nombre]
            sensor = hardware.obtener_tof(nombre)

            if sensor is None:
                if not muestra.get("fuera_servicio"):
                    contratos.publicar_error(muestra, "ToF fuera de servicio", ahora, fuera_servicio=True)

                motor = sistema["actuadores"]["motor"]
                detenido = (
                    motor["pwm_aplicado"] == 0
                    or motor["direccion"] == 0
                )

                if (detenido and utilidades.diferencia_ms(ahora, ultimo_reinicio[nombre]) >= config.TOF_BACKOFF_REINICIO_MS):
                    ultimo_reinicio[nombre] = ahora
                    sensor, error = hardware.reinicializar_tof(nombre)
                    if sensor is None:
                        contratos.publicar_error(muestra, error, _ahora_ms(), fuera_servicio=True,)
                    else:
                        ultima_muestra[nombre] = _ahora_ms()

                await uasyncio.sleep_ms(config.PERIODO_TOF_POLL_MS)
                continue

            try:
                mm = sensor.read_disponible()
                if mm is None:
                    if (utilidades.diferencia_ms(ahora, ultima_muestra[nombre]) > config.TOF_TIMEOUT_MUESTRA_MS):
                        contratos.publicar_error(muestra, "ToF sin muestra nueva", ahora)
                        ultima_muestra[nombre] = ahora

                    if (muestra.get("errores_consecutivos", 0) >= config.TOF_ERRORES_ANTES_REINICIO):
                        hardware.poner_tof_fuera_servicio(nombre)

                    await uasyncio.sleep_ms(config.PERIODO_TOF_POLL_MS)
                    continue

                cm = mm / 10.0

                if not utilidades.numero_finito(cm) or cm <= 0:
                    raise ValueError("distancia ToF invalida")

                limite_rango = (
                    config.TOF_FRONTAL_RANGO_UTIL_CM
                    if nombre == "frontal"
                    else config.TOF_LATERAL_RANGO_UTIL_CM
                )
                fuera_rango = cm >= limite_rango
                contratos.publicar_muestra(muestra, cm, ahora, fuera_rango=fuera_rango)
                ultima_muestra[nombre] = ahora

            except Exception as exc:

                contratos.publicar_error(muestra, exc, ahora)

                if (muestra.get("errores_consecutivos", 0) >= config.TOF_ERRORES_ANTES_REINICIO):
                    hardware.poner_tof_fuera_servicio(nombre)

            await uasyncio.sleep_ms(config.PERIODO_TOF_POLL_MS)


async def leer_encoder(sistema):
    muestra = sistema["sensores"]["encoder"]
    ultima_captura_ms = None
    while True:
        try:
            delta = hardware.encoder.actualizar()
            ahora = _ahora_ms()
            intervalo_ms = (
                None
                if ultima_captura_ms is None
                else utilidades.diferencia_ms(ahora, ultima_captura_ms)
            )
            ultima_captura_ms = ahora
            pasos = hardware.encoder.pasos_acumulados()
            rpm = _calcular_rpm(
                delta,
                intervalo_ms,
                hardware.encoder.PASOS_POR_VUELTA,
            )
            distancia = (
                config.SIGNO_RPM_ENCODER
                * pasos
                * config.DISTANCIA_POR_VUELTA_RUEDA_CM
                / hardware.encoder.PASOS_POR_VUELTA
            )
            movimiento = abs(delta) >= config.DELTA_ENCODER_MOVIMIENTO_MIN
            contratos.publicar_encoder(
                muestra,
                delta,
                pasos,
                distancia,
                rpm,
                movimiento,
                ahora,
            )
        except Exception as exc:
            contratos.publicar_error(muestra, exc, _ahora_ms())
        await uasyncio.sleep_ms(config.PERIODO_ENCODER_MS)


async def leer_boton_start(sistema):
    muestra = sistema["entradas"]["boton_start"]
    while True:
        try:
            contratos.publicar_muestra(muestra, hardware.btn_a.value() == 0, _ahora_ms())
        except Exception as exc:
            contratos.publicar_error(muestra, exc, _ahora_ms())
        await uasyncio.sleep_ms(config.PERIODO_ENTRADAS_MS)


async def leer_control_ps4(sistema):
    muestra = sistema["entradas"]["ps4"]
    ultima_trama_ms = None
    while True:
        try:
            paquete = hardware.lector_ps4.leer()
            if paquete is not None:
                ahora = _ahora_ms()
                if (
                    ultima_trama_ms is not None
                    and utilidades.diferencia_ms(ahora, ultima_trama_ms)
                    > config.TIMEOUT_SIN_UART_PS4_MS
                ):
                    muestra["cortes_uart"] = (
                        muestra.get("cortes_uart", 0) + 1
                    )
                ultima_trama_ms = ahora
                contratos.publicar_muestra(muestra, paquete, ahora)
        except Exception as exc:
            contratos.publicar_error(muestra, exc, _ahora_ms())
        await uasyncio.sleep_ms(4)


async def leer_camara(sistema):
    """Disponible para Obstacle Challenge; no se crea en Open Challenge."""
    muestra = sistema["sensores"]["camara"]
    modo_color = False
    while True:
        try:
            if not modo_color:
                if not hardware.camara.is_present():
                    raise OSError("WonderCam no encontrada")
                if not hardware.camara.iniciar_modo_color():
                    raise OSError("WonderCam no entra en modo color")
                modo_color = True
            detecciones = hardware.camara.get_color_detections()
            contratos.publicar_muestra(muestra, detecciones, _ahora_ms())
        except Exception as exc:
            modo_color = False
            contratos.publicar_error(muestra, exc, _ahora_ms())
            await uasyncio.sleep_ms(1000)
            continue
        await uasyncio.sleep_ms(50)
