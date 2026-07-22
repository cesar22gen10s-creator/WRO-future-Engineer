from hardware import ToF, imu, servo, btn_a, sonar_frontal, sonar_izquierdo, sonar_derecho, motor, encoder, camara
import time 
import uasyncio #type: ignore
from machine import Pin, I2C  # type: ignore
import config
import estado
import utilidades 

async def movimiento():
    while True:
        try:
            distancia_tof = estado.estado["sonar"]["tof"]
            distancia_frontal = estado.estado["sonar"]["frontal"]
            distancia_izquierda = estado.estado["sonar"]["izquierdo"]
            distancia_derecha = estado.estado["sonar"]["derecho"]
            intencion_giro = "NINGUNA"
            heading_ref = estado.imu_estado["heading_ref"]
            heading = estado.imu_estado["heading"]
            heading_error = estado.imu_estado["heading_error"]
            probabilidad_giro = 0.0
            maniobra = estado.motor_estado["maniobra"]


            if distancia_izquierda is not None and distancia_derecha is not None and (distancia_izquierda + distancia_derecha) != 0:
                probabilidad_giro = (distancia_izquierda - distancia_derecha) / (distancia_izquierda + distancia_derecha)

            if probabilidad_giro > 0.35:
                intencion_giro = "IZQ"
            elif probabilidad_giro < -0.35:
                intencion_giro = "DER"

            if maniobra == "avance":
                if (distancia_frontal is not None and distancia_frontal <= 2 * config.FRONTAL_MIN_ANTES_GIRO_CM) or (distancia_tof is not None and distancia_tof <= 2* config.FRONTAL_MIN_ANTES_GIRO_CM):
                    maniobra = "aproximacion"
                elif (distancia_frontal is not None and distancia_frontal < 1.5 * config.FRONTAL_MIN_ANTES_GIRO_CM) or (distancia_frontal is not None and distancia_frontal < 1.5 * config.FRONTAL_MIN_ANTES_GIRO_CM) and intencion_giro != "NINGUNA":
                    estado.imu_estado["heading_ref"] = 90 if intencion_giro == "DER" else -90
                    maniobra = "girando_derecha" if intencion_giro == "DER" else "girando_izquierda"

            elif maniobra == "aproximacion":
                if distancia_frontal is not None and distancia_frontal < config.FRONTAL_MIN_ANTES_GIRO_CM:
                    maniobra = "freno"
                elif distancia_frontal is not None and distancia_frontal > 2 * config.FRONTAL_MIN_ANTES_GIRO_CM:
                    maniobra = "avance"
                elif distancia_frontal is not None and distancia_frontal < 1.5 * config.FRONTAL_MIN_ANTES_GIRO_CM and intencion_giro != "NINGUNA":
                    estado.imu_estado["heading_ref"] = 90 if intencion_giro == "DER" else -90
                    maniobra = "girando_derecha" if intencion_giro == "DER" else "girando_izquierda"

            elif maniobra == "freno":

                if distancia_frontal is not None and distancia_frontal > config.FRONTAL_MIN_ANTES_GIRO_CM:
                    maniobra = "aproximacion"
                elif distancia_frontal is not None and distancia_frontal < 1.5 * config.FRONTAL_MIN_ANTES_GIRO_CM and intencion_giro != "NINGUNA":
                    estado.imu_estado["heading_ref"] = 90 if intencion_giro == "DER" else -90
                    maniobra = "girando_derecha" if intencion_giro == "DER" else "girando_izquierda"

            elif maniobra in ("girando_derecha", "girando_izquierda") and heading_centrado:
                maniobra = "aproximacion"

            estado.motor_estado["maniobra"] = maniobra

            if maniobra == "avance":
                estado.motor_estado["direccion"] = 1
                estado.motor_estado["velocidad"] = config.VELOCIDAD_AVANCE
            elif maniobra == "aproximacion":
                estado.motor_estado["direccion"] = 1
                estado.motor_estado["velocidad"] = config.VELOCIDAD_APROXIMACION
            elif maniobra == "freno":
                estado.motor_estado["direccion"] = -1
                estado.motor_estado["velocidad"] = config.VELOCIDAD_RETROCESO
            elif maniobra in ("girando_derecha", "girando_izquierda"):
                estado.motor_estado["direccion"] = 1
                estado.motor_estado["velocidad"] = config.VELOCIDAD_AVANCE

        except Exception as e:
            print("Error al determinar movimiento: ", e)
        await uasyncio.sleep_ms(10)

async def actualizar_motor():
    while True:
        try:
            if estado.motor_estado["activo"] == False:
                estado.motor_estado["velocidad"] = 0
                estado.motor_estado["direccion"] = 0
                motor.detener()            
            else:
                motor.mover_directo(estado.motor_estado["velocidad"], estado.motor_estado["direccion"])

        except Exception as e:
            print("Error al mover motor: ", e)
        await uasyncio.sleep_ms(10)



async def leer_imu():

    try:

        imu.iniciar(rango=250)
        imu.calibrar_bias_gyro(muestras=150, delay_ms=3)
        estado.imu_estado["ok"] = True
        print("IMU iniciada")

    except Exception as e:

        estado.imu_estado["ok"] = False
        estado.imu_estado["error"] = str(e)
        print("Error IMU:", e)

    while True:

        try:

            heading, gz = imu.actualizar_orientacion()
            estado.imu_estado["heading"] = heading
            estado.imu_estado["gz"] = gz
            estado.imu_estado["velocidad"] = imu.actualizar_velocidad_x()[1]

            if estado.imu_estado["heading_ref"] is None:

                estado.imu_estado["heading_error"] = None
            else:

                estado.imu_estado["heading_error"] = utilidades.normalizar_angulo(estado.imu_estado["heading_ref"] - heading)
            
            heading_error = estado.imu_estado["heading_error"]
            global heading_centrado 
            heading_centrado = (heading_error is not None and abs(heading_error) <= config.ERROR_GIRO_PERMITIDO)
            estado.imu_estado["timestamp"] = time.ticks_ms()
            estado.imu_estado["actualizaciones"] += 1
            estado.imu_estado["ok"] = True
            
            
            if (estado.motor_estado["maniobra"] in ("girando_derecha", "girando_izquierda") and estado.imu_estado["heading_error"] is not None and abs(estado.imu_estado["heading_error"]) < 5):
                time.sleep_ms(100)
                estado.motor_estado["maniobra"] = "avance"
        
        except Exception as e:
        
            estado.imu_estado["ok"] = False
            estado.imu_estado["error"] = str(e)
        
        await uasyncio.sleep_ms(10)


async def leer_sonares():

    while True:

        try:
            estado.estado["sonar"]["tof"] = ToF.read()/10
            estado.estado["sonar"]["frontal"] = sonar_frontal.leer_cm()
            estado.estado["sonar"]["izquierdo"] = sonar_izquierdo.leer_cm()
            estado.estado["sonar"]["derecho"] = sonar_derecho.leer_cm()
            estado.estado["sonar"]["timestamp"] = time.ticks_ms()
            estado.estado["sonar"]["actualizaciones"] += 1
            estado.estado["sonar"]["ok"] = True
            estado.estado["sonar"]["error"] = None
            global pasillo
            global derecha_abierta
            global izquierda_abierta
            global obstaculo_frontal
            global frontal_liberado
            global frontal_minimo
            frontal_minimo = (estado.estado["sonar"]["frontal"] is not None and estado.estado["sonar"]["frontal"] <= config.FRONTAL_MIN_ANTES_GIRO_CM)  
            obstaculo_frontal = (estado.estado["sonar"]["frontal"] is not None and estado.estado["sonar"]["frontal"] <= config.DISTANCIA_FRONTAL_FRENADO_CM)
            frontal_liberado = (estado.estado["sonar"]["frontal"] is not None and estado.estado["sonar"]["frontal"] >= config.DISTANCIA_FRONTAL_FIN_FRENADO_CM)
            pasillo = (estado.estado["sonar"]["izquierdo"] is not None and estado.estado["sonar"]["derecho"] is not None and(abs(estado.estado["sonar"]["izquierdo"]+estado.estado["sonar"]["derecho"]) <= config.PASILLO_CM) and not obstaculo_frontal)
            derecha_abierta = ((estado.estado["sonar"]["derecho"] is None) or (estado.estado["sonar"]["derecho"] >= config.DISTANCIA_GIRO_MIN_CM))
            izquierda_abierta = ((estado.estado["sonar"]["izquierdo"] is None) or (estado.estado["sonar"]["izquierdo"] >= config.DISTANCIA_GIRO_MIN_CM))

        except Exception as e:

            estado.estado["sonar"]["ok"] = False
            estado.estado["sonar"]["error"] = str(e)

        await uasyncio.sleep_ms(50)


async def actualizar_encoder():
    while True:
        try:
            delta = encoder.actualizar()
            estado.estado["encoder"]["delta"] = delta
            if abs(delta) <= 2:
                estado.estado["encoder"]["movimiento"] = False
            else:
                estado.estado["encoder"]["movimiento"] = True

            try:
                pasos_por_vuelta = encoder.PASOS_POR_VUELTA
            except Exception:
                pasos_por_vuelta = 4096
            distancia_cm = (delta * config.DISTANCIA_POR_VUELTA_CM) / pasos_por_vuelta
            estado.estado["encoder"]["distancia_cm"] = distancia_cm
            estado.estado["encoder"]["timestamp"] = time.ticks_ms()
            estado.estado["encoder"]["actualizaciones"] += 1
        except Exception as e:
            # no bloquear por error de encoder
            estado.estado["encoder"]["delta"] = 0
        await uasyncio.sleep_ms(1000)


async def actualizar_servo():

    while True:

        try:
            if heading_centrado and utilidades.servo_objetivo_desde_sonar():
                estado.servo_estado["modo_correccion"] = "sonar"
            else:
                if not heading_centrado:
                    estado.servo_estado["sonar_disponible"] = False
                    estado.servo_estado["sonar_motivo"] = "heading_fuera_rango"
                utilidades.servo_objetivo_desde_heading()
                estado.servo_estado["modo_correccion"] = "heading"

            actual = estado.servo_estado["actual"]
            objetivo = estado.servo_estado["objetivo"]
            delta = objetivo - actual

            if abs(delta) >= estado.servo_estado["paso"]:
                # mover sin espera para no bloquear el bucle
                servo.mover(objetivo, espera=False)
                estado.servo_estado["actual"] = objetivo
            else:
                servo.mover(actual, espera=False)
                estado.servo_estado["actual"] = actual

            estado.servo_estado["timestamp"] = time.ticks_ms()
            estado.servo_estado["actualizaciones"] += 1
            estado.servo_estado["ok"] = True
            estado.servo_estado["error"] = None

        except Exception as e:

            estado.servo_estado["ok"] = False
            estado.servo_estado["error"] = str(e)

        await uasyncio.sleep_ms(10)


async def leer_camara():
    modo_color_activo = False

    while True:
        try:
            if not modo_color_activo:
                estado.camara_estado["ok"] = camara.is_present()
                if not estado.camara_estado["ok"]:
                    raise Exception("WonderCam no encontrada en I2C")

                try:
                    estado.camara_estado["firmware"] = camara.get_firmware_version()
                except Exception:
                    estado.camara_estado["firmware"] = None

                if not camara.iniciar_modo_color():
                    raise Exception("No se pudo activar reconocimiento de color")

                estado.camara_estado["funcion"] = camara.FUNC_COLOR
                modo_color_activo = True

            detecciones = camara.get_color_detections()
            estado.camara_estado["detecciones"] = detecciones
            estado.camara_estado["cantidad"] = len(detecciones)
            estado.camara_estado["detectado"] = len(detecciones) > 0
            estado.camara_estado["ids"] = [deteccion["id"] for deteccion in detecciones]
            estado.camara_estado["ok"] = True
            estado.camara_estado["error"] = None
            global bloque_rojo
            global bloque_verde
            bloque_rojo = ()


        except Exception as e:
            modo_color_activo = False
            estado.camara_estado["ok"] = False
            estado.camara_estado["error"] = str(e)
            estado.camara_estado["detectado"] = False
            estado.camara_estado["cantidad"] = 0
            estado.camara_estado["ids"] = []
            estado.camara_estado["detecciones"] = []
            await uasyncio.sleep_ms(1000)
            continue

        await uasyncio.sleep_ms(50)

async def debug():

    while True:

        detecciones = estado.camara_estado["detecciones"]
        camara_detalles = []
        
        for deteccion in detecciones:
            camara_detalles.append(
                "id:{} x:{} y:{} w:{} h:{}".format(
                    deteccion.get("id"),
                    deteccion.get("x"),
                    deteccion.get("y"),
                    deteccion.get("w"),
                    deteccion.get("h")
                )
            )

        camara_debug = "OK:{} DET:{} N:{} [{}]".format(
            estado.camara_estado["ok"],
            estado.camara_estado["detectado"],
            estado.camara_estado["cantidad"],
            " | ".join(camara_detalles)
        )

        print(
            "OK:{} "
            "HEAD:{:.1f} "
            "REF:{} "
            "ERR:{} "
            "F:{} "
            "I:{} "
            "D:{} "
            "UPD:{} "
            "MODO:{} "
            "S:{:.f}->{:.f} "
            "CAMARA:{} "
            "MN:{}"
            .format(
                estado.imu_estado["ok"],
                estado.imu_estado["heading"],
                estado.imu_estado["heading_ref"],
                estado.imu_estado["heading_error"],
                estado.estado["sonar"]["frontal"],
                estado.estado["sonar"]["izquierdo"],
                estado.estado["sonar"]["derecho"],
                estado.estado["sonar"]["actualizaciones"],
                estado.servo_estado["modo_correccion"],
                estado.servo_estado["actual"],
                estado.servo_estado["objetivo"],
                 estado.estado["sonar"]["tof"],
                estado.motor_estado["maniobra"]
            ))

        await uasyncio.sleep_ms(1000)

async def main():

    uasyncio.create_task(leer_imu())
    uasyncio.create_task(leer_sonares())
    uasyncio.create_task(actualizar_encoder())
    uasyncio.create_task(actualizar_servo())
    uasyncio.create_task(leer_camara())
    uasyncio.create_task(actualizar_motor())
    uasyncio.create_task(movimiento()) 
    uasyncio.create_task(debug())
    while True:
        


        estado.servo_estado["objetivo"] = config.SERVO_CENTRO
        if btn_a.value() == 0 and estado.estado["btn_a"]["memoria"] == 0:
            estado.imu_estado["heading_ref"] = estado.imu_estado["heading"]
            estado.estado["btn_a"]["memoria"] += 1
            estado.motor_estado["activo"] = True
            estado.motor_estado["maniobra"] = "avance"
            estado.motor_estado["activo"] = True
        elif btn_a.value() == 0 and estado.estado["btn_a"]["memoria"] == 1:
            estado.estado["btn_a"]["memoria"] = 0
            estado.motor_estado["activo"] = False
            estado.motor_estado["direccion"] = 0
            estado.imu_estado["heading_ref"] = None

        await uasyncio.sleep_ms(500)

uasyncio.run(main())
