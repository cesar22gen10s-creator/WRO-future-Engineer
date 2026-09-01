import uasyncio  # type: ignore

import config
import estado
import hardware
import utilidades


def _distancia_valida(valor, minimo, maximo):
    return bool(
        utilidades.numero_finito(valor)
        and minimo <= valor <= maximo
    )


async def leer_imu():
    muestra = estado.estado["imu"]
    iniciado = False

    while True:
        if not iniciado:
            try:
                hardware.imu.iniciar(rango=250)
                hardware.imu.calibrar_bias_gyro(muestras=150, delay_ms=3)
                iniciado = True
            except Exception:
                estado.marcar_invalida(muestra)
                await uasyncio.sleep_ms(1000)
                continue

        try:
            heading, gz = hardware.imu.actualizar_orientacion()
            if not (
                utilidades.numero_finito(heading)
                and utilidades.numero_finito(gz)
            ):
                raise ValueError("lectura IMU invalida")

            muestra["heading"] = utilidades.normalizar_angulo(heading)
            muestra["gz"] = gz
            muestra["valido"] = True
            muestra["seq"] += 1
        except Exception:
            estado.marcar_invalida(muestra)
            iniciado = False
            await uasyncio.sleep_ms(250)
            continue

        await uasyncio.sleep_ms(config.PERIODO_IMU_MS)


def _leer_sonar(sensor, muestra):
    try:
        valor = sensor.leer_cm()
        if valor == None:
            valor == 260
        if not _distancia_valida(
            valor,
            config.SONAR_MIN_VALIDO_CM,
            config.SONAR_MAX_CM,
        ):
            estado.marcar_invalida(muestra)
            return
        estado.publicar_lectura(muestra, valor)
    except Exception:
        estado.marcar_invalida(muestra)


async def leer_sonares():
    muestras = estado.estado["sonar"]
    sensores = (
        (hardware.sonar_frontal, muestras["frontal"]),
        (hardware.sonar_izquierdo, muestras["izquierdo"]),
        (hardware.sonar_derecho, muestras["derecho"]),
    )

    while True:
        for sensor, muestra in sensores:
            _leer_sonar(sensor, muestra)
            await uasyncio.sleep_ms(config.SEPARACION_SONARES_MS)
        await uasyncio.sleep_ms(config.PERIODO_SONAR_MS)


def _recuperar_tof(nombre, muestra):
    sensor, _ = hardware.reinicializar_tof(nombre)
    if sensor is None:
        estado.marcar_invalida(muestra)
        return False
    return True


async def leer_tofs():
    muestras = estado.estado["tof"]
    nombres = hardware.NOMBRES_TOF
    errores = {nombre: 0 for nombre in nombres}
    ciclos_sin_muestra = {nombre: 0 for nombre in nombres}
    espera_recuperacion = {nombre: 0 for nombre in nombres}

    while True:
        for nombre in nombres:
            muestra = muestras[nombre]
            sensor = hardware.obtener_tof(nombre)

            if espera_recuperacion[nombre] > 0:
                espera_recuperacion[nombre] -= 1

            if sensor is None:
                estado.marcar_invalida(muestra)
                errores[nombre] += 1
            else:
                try:
                    mm = sensor.read_disponible()
                    if mm is None:
                        ciclos_sin_muestra[nombre] += 1
                        if (
                            ciclos_sin_muestra[nombre]
                            >= config.CICLOS_MAX_SIN_TOF
                        ):
                            estado.marcar_invalida(muestra)
                            errores[nombre] += 1
                    else:
                        if not utilidades.numero_finito(mm):
                            raise ValueError("lectura ToF no numerica")

                        if mm >= config.TOF_SIN_OBJETIVO_DESDE_MM:
                            cm = config.TOF_DISTANCIA_ABIERTA_CM
                        else:
                                cm = mm / 10.0
                                if not _distancia_valida(
                                    cm,
                                    config.TOF_MIN_VALIDO_CM,
                                    config.TOF_MAX_VALIDO_CM,
                                ):
                                    raise ValueError("lectura ToF invalida")

                        estado.publicar_lectura(muestra, cm)
                        errores[nombre] = 0
                        ciclos_sin_muestra[nombre] = 0
                except Exception:
                    estado.marcar_invalida(muestra)
                    errores[nombre] += 1

            if (
                errores[nombre] >= config.TOF_ERRORES_ANTES_REINICIO
                and espera_recuperacion[nombre] == 0
            ):
                recuperado = _recuperar_tof(nombre, muestra)
                errores[nombre] = (
                    0 if recuperado else config.TOF_ERRORES_ANTES_REINICIO
                )
                ciclos_sin_muestra[nombre] = 0
                if not recuperado:
                    espera_recuperacion[nombre] = (
                        config.CICLOS_ENTRE_RECUPERACIONES_TOF
                    )

            await uasyncio.sleep_ms(config.PERIODO_TOF_MS)


async def leer_encoder():
    muestra = estado.estado["encoder"]

    while True:
        try:
            delta = hardware.encoder.actualizar()
            if not utilidades.numero_finito(delta):
                raise ValueError("delta de encoder invalido")

            pasos = hardware.encoder.pasos_acumulados()
            distancia = (
                config.SIGNO_DISTANCIA_ENCODER
                * pasos
                * config.DISTANCIA_POR_VUELTA_RUEDA_CM
                / hardware.encoder.PASOS_POR_VUELTA
            )
            muestra["delta"] = delta
            muestra["pasos"] = pasos
            muestra["distancia"] = distancia
            muestra["movimiento"] = (
                abs(delta) >= config.DELTA_ENCODER_MOVIMIENTO_MIN
            )
            muestra["valido"] = True
            muestra["seq"] += 1
        except Exception:
            estado.marcar_invalida(muestra)

        await uasyncio.sleep_ms(config.PERIODO_ENCODER_MS)


async def leer_boton_start():
    muestra = estado.estado["entradas"]["boton_start"]

    while True:
        try:
            estado.publicar_lectura(muestra, hardware.btn_a.value() == 0)
        except Exception:
            estado.marcar_invalida(muestra)
        await uasyncio.sleep_ms(config.PERIODO_ENTRADAS_MS)


async def leer_ps4():
    muestra = estado.estado["entradas"]["ps4"]
    ciclos_sin_paquete = 0

    while True:
        try:
            paquete = hardware.lector_ps4.leer()
            if paquete is None:
                ciclos_sin_paquete += 1
                if ciclos_sin_paquete >= config.CICLOS_MAX_SIN_PS4:
                    estado.marcar_invalida(muestra)
            else:
                estado.publicar_lectura(muestra, paquete)
                ciclos_sin_paquete = 0
        except Exception:
            estado.marcar_invalida(muestra)

        await uasyncio.sleep_ms(config.PERIODO_ENTRADAS_MS)


async def leer_camara():
    muestra = estado.estado["camara"]
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
            estado.publicar_lectura(muestra, detecciones)
        except Exception:
            modo_color = False
            estado.marcar_invalida(muestra)
            await uasyncio.sleep_ms(1000)
            continue

        await uasyncio.sleep_ms(config.PERIODO_CAMARA_MS)
