import uasyncio  # type: ignore

import config
import estado
import hardware
import utilidades


def _orden_motor():
    motor = estado.estado["motor"]
    freno = bool(motor.get("freno", False))
    if freno:
        return 0, 0, True

    velocidad = motor.get("velocidad", 0)
    direccion = motor.get("direccion", 0)

    if not utilidades.numero_finito(velocidad):
        raise ValueError("PWM no finito")
    velocidad = int(utilidades.limitar(velocidad, 0, 1023))
    direccion = int(direccion)
    if direccion not in (-1, 0, 1):
        raise ValueError("direccion de motor invalida")
    if velocidad == 0 or direccion == 0:
        return 0, 0, False
    
    return velocidad, direccion, False


async def _aplicar_contrapulso(venia_avanzando):
    hardware.motor.detener()
    if not venia_avanzando:
        return
    await uasyncio.sleep_ms(config.PAUSA_NEUTRAL_FRENO_MS)
    hardware.motor.frenar(config.PWM_FRENO_CONTRAPULSO)
    await uasyncio.sleep_ms(config.DURACION_FRENO_CONTRAPULSO_MS)
    hardware.motor.detener()


async def ejecutar_motor():
    motor_estado = estado.estado["motor"]
    direccion_aplicada = 0
    freno_aplicado = False

    while True:
        try:
            velocidad, direccion, freno = _orden_motor()

            if freno:
                if not freno_aplicado:
                    await _aplicar_contrapulso(direccion_aplicada == 1)
                    freno_aplicado = True
                else:
                    hardware.motor.detener()
                direccion_aplicada = 0
                motor_estado["ok"] = True
                motor_estado["error"] = None
                await uasyncio.sleep_ms(config.PERIODO_ACTUADOR_MS)
                continue

            freno_aplicado = False

            if (direccion != 0 and direccion_aplicada not in (0, direccion)):
                hardware.motor.detener()
                direccion_aplicada = 0
                await uasyncio.sleep_ms(config.PERIODO_ACTUADOR_MS)
                continue

            if direccion == 0:
                hardware.motor.detener()
                direccion_aplicada = 0
            else:
                hardware.motor.mover_directo(velocidad, direccion)
                direccion_aplicada = direccion

            motor_estado["ok"] = True
            motor_estado["error"] = None
        except Exception as error:
            try:
                hardware.motor.detener()
            except Exception:
                pass
            direccion_aplicada = 0
            freno_aplicado = bool(motor_estado.get("freno", False))
            motor_estado["ok"] = False
            motor_estado["error"] = str(error)

        await uasyncio.sleep_ms(config.PERIODO_ACTUADOR_MS)


def _invertir_servo_en_retroceso():
    navegacion = estado.estado["navegacion"]
    motor = estado.estado["motor"]
    return bool(navegacion["modo"] != "manual" and motor["direccion"] == -1)


async def ejecutar_servo():
    servo_estado = estado.estado["servo"]
    angulo_actual = config.SERVO_CENTRO

    while True:
        try:
            objetivo = utilidades.comando_a_angulo_servo(servo_estado["comando"], en_retroceso=_invertir_servo_en_retroceso())
            angulo_actual = utilidades.avanzar_hacia(angulo_actual, objetivo, config.PASO_SERVO)
            hardware.servo.mover(angulo_actual, espera=False)
            servo_estado["ok"] = True
            servo_estado["error"] = None
        except Exception as error:
            angulo_actual = config.SERVO_CENTRO
            try:
                hardware.servo.mover(angulo_actual, espera=False)
            except Exception:
                pass
            servo_estado["ok"] = False
            servo_estado["error"] = str(error)

        await uasyncio.sleep_ms(config.PERIODO_ACTUADOR_MS)


def detener_seguro():
    estado.estado["motor"]["velocidad"] = 0
    estado.estado["motor"]["direccion"] = 0
    estado.estado["motor"]["freno"] = False
    estado.estado["servo"]["comando"] = 0.0
    try:
        hardware.motor.detener()
    except Exception:
        pass
    try:
        hardware.servo.mover(config.SERVO_CENTRO, espera=False)
    except Exception:
        pass
