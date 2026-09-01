import math

import config


def numero_finito(valor):
    if not isinstance(valor, (int, float)):
        return False
    try:
        return math.isfinite(valor)
    except (AttributeError, OverflowError, TypeError):
        return valor == valor and abs(valor) != float("inf")


def normalizar_angulo(angulo):
    if not numero_finito(angulo):
        raise ValueError("angulo no finito")
    resultado = (angulo + 180.0) % 360.0 - 180.0
    if resultado <= -180.0:
        resultado += 360.0
    return resultado


def error_angular(objetivo, actual):
    return normalizar_angulo(objetivo - actual)


def limitar(valor, minimo, maximo):
    if valor < minimo:
        return minimo
    if valor > maximo:
        return maximo
    return valor


def control_heading(error, kp):
    if not numero_finito(error) or config.ERROR_HEADING_MAX <= 0:
        return 0.0
    comando = (
        -config.SIGNO_HEADING_DERECHA
        * kp
        * error
        / config.ERROR_HEADING_MAX
    )
    return limitar(comando, -1.0, 1.0)


def control_giro(error):
    if not numero_finito(error):
        return 0.0
    if abs(error) <= config.ERROR_GIRO_PERMITIDO:
        return 0.0
    comando = control_heading(error, config.KP_HEADING_GIRO)
    if 0 < abs(comando) < config.COMANDO_GIRO_MIN:
        comando = config.COMANDO_GIRO_MIN if comando > 0 else -config.COMANDO_GIRO_MIN
    return limitar(comando, -1.0, 1.0)


def control_correccion_tof(asimetria):
    if not numero_finito(asimetria):
        return 0.0
    if abs(asimetria) <= config.ZONA_MUERTA_ASIMETRIA_TOF:
        return 0.0
    comando = (
        config.SIGNO_CORRECCION_TOF
        * config.KP_CORRECCION_TOF
        * asimetria
    )
    return limitar(comando, -1.0, 1.0)


def combinar_controles(heading, correccion):
    return limitar(heading + correccion, -1.0, 1.0)


def comando_a_angulo_servo(comando, en_retroceso=False):
    if not numero_finito(comando):
        comando = 0.0
    comando = limitar(comando, -1.0, 1.0)

    if config.INVERTIR_COMANDO_SERVO:
        comando = -comando
    if en_retroceso and config.INVERTIR_SERVO_EN_RETROCESO:
        comando = -comando

    if comando < 0:
        recorrido = config.SERVO_IZQUIERDA - config.SERVO_CENTRO
        angulo = config.SERVO_CENTRO + (-comando) * recorrido
    else:
        recorrido = config.SERVO_DERECHA - config.SERVO_CENTRO
        angulo = config.SERVO_CENTRO + comando * recorrido

    minimo = min(config.SERVO_DERECHA, config.SERVO_IZQUIERDA)
    maximo = max(config.SERVO_DERECHA, config.SERVO_IZQUIERDA)
    return limitar(angulo, minimo, maximo)


def avanzar_hacia(actual, objetivo, paso):
    if not numero_finito(actual) or not numero_finito(objetivo):
        return config.SERVO_CENTRO
    if paso <= 0 or abs(objetivo - actual) <= paso:
        return objetivo
    return actual + paso if objetivo > actual else actual - paso


def actualizar_contador_seq(seq, ultimo_seq, ciclos_sin_actualizar):
    if isinstance(seq, int) and seq > 0 and seq != ultimo_seq:
        return seq, 0, True
    return ultimo_seq, ciclos_sin_actualizar + 1, False
