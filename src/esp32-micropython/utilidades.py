import math
import time

import config

def ahora_ms():
    return time.ticks_ms()

def numero_finito(valor):
    if not isinstance(valor, (int, float)):
        return False
    try:
        return math.isfinite(valor)
    except (AttributeError, OverflowError, TypeError):
        return valor == valor and abs(valor) != float("inf")


def format1(valor):
    return "{:.1f}".format(valor) if numero_finito(valor) else str(valor)


def diferencia_ms(ahora_ms, antes_ms):
    try:
        return time.ticks_diff(ahora_ms, antes_ms)
    except AttributeError:
        return ahora_ms - antes_ms


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


def comando_stick(valor, minimo=-511, maximo=512, zona_muerta=10):
    if not numero_finito(valor):
        return 0.0
    valor = limitar(int(valor), minimo, maximo)
    if abs(valor) <= zona_muerta:
        return 0.0
    if valor < 0:
        return valor / abs(minimo)
    return valor / maximo


def control_heading(error, kp):
    if not numero_finito(error):
        return 0.0
    escala = config.ERROR_HEADING_MAX
    if escala <= 0:
        return 0.0
    comando = -config.SIGNO_HEADING_DERECHA * kp * error / escala
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
    """Convierte la asimetria de los ToF en correccion de pasillo.

    Una lectura mayor a la izquierda produce correccion hacia la izquierda
    (comando negativo); el signo del montaje se calibra en config.
    """
    if not numero_finito(asimetria):
        return 0.0
    if abs(asimetria) <= config.ZONA_MUERTA_ASIMETRIA_TOF:
        return 0.0
    return limitar(
        config.SIGNO_CORRECCION_TOF
        * config.KP_CORRECCION_TOF
        * asimetria,
        -1.0,
        1.0,
    )


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
        angulo = config.SERVO_CENTRO + (-comando) * (config.SERVO_IZQUIERDA - config.SERVO_CENTRO)
    else:
        angulo = config.SERVO_CENTRO + comando * (config.SERVO_DERECHA - config.SERVO_CENTRO)
    minimo = min(config.SERVO_DERECHA, config.SERVO_IZQUIERDA)
    maximo = max(config.SERVO_DERECHA, config.SERVO_IZQUIERDA)
    return limitar(angulo, minimo, maximo)


def avanzar_hacia(actual, objetivo, paso):
    if not numero_finito(actual) or not numero_finito(objetivo):
        return config.SERVO_CENTRO
    if paso <= 0 or abs(objetivo - actual) <= paso:
        return objetivo
    return actual + paso if objetivo > actual else actual - paso


def orden_vigente(orden, ahora_ms):
    try:
        emitida = orden["emitida_ms"]
        vigencia = orden["vigencia_ms"]
        seq = orden["seq"]
    except (KeyError, TypeError):
        return False
    if not numero_finito(emitida) or not numero_finito(vigencia):
        return False
    if not isinstance(seq, int) or seq <= 0 or vigencia < 0:
        return False
    edad = diferencia_ms(ahora_ms, emitida)
    return 0 <= edad <= vigencia
