import config
import estado

historial_tof = []

MAX_MUESTRAS = 5

def normalizar_angulo(a):

    while a > 180:
        a -= 360

    while a <= -180:
        a += 360

    return a

def limitar(x, minimo, maximo):
    if x < minimo:
        return minimo
    if x > maximo:
        return maximo
    return x

def comando_a_servo(comando):
    comando = limitar(comando, -1.0, 1.0)
    if not config.INVERTIR_SERVO:
        comando = -comando
    if estado.motor_estado["direccion"] == -1:
        comando = -comando
    rango = abs(config.SERVO_IZQUIERDA - config.SERVO_CENTRO)
    angulo = config.SERVO_CENTRO + comando * rango
    return limitar(angulo, config.SERVO_DERECHA, config.SERVO_IZQUIERDA)

def fijar_servo_objetivo(angulo):
    estado.servo_estado["objetivo"] = limitar(angulo, config.SERVO_DERECHA, config.SERVO_IZQUIERDA)

def servo_objetivo_desde_heading():
    error = estado.imu_estado["heading_error"]
    if error is None:
        fijar_servo_objetivo(config.SERVO_CENTRO)
        return True
    if config.INVERTIR_HEADING:
        error = -error
    comando = config.KP_HEADING * error / config.ERROR_HEADING_MAX
    fijar_servo_objetivo(comando_a_servo(comando))
    return True

def servo_objetivo_desde_sonar():
    izquierdo = estado.estado["sonar"]["izquierdo"]
    derecho = estado.estado["sonar"]["derecho"]

    izquierdo_valido = izquierdo is not None and izquierdo >= config.DISTANCIA_MIN_VALIDA
    derecho_valido = derecho is not None and derecho >= config.DISTANCIA_MIN_VALIDA

    if not izquierdo_valido and not derecho_valido:
        estado.servo_estado["sonar_disponible"] = False
        estado.servo_estado["sonar_motivo"] = "sin_laterales"
        return False

    if izquierdo_valido and derecho_valido:
        error = izquierdo - derecho
        suma = izquierdo + derecho
        if suma <= 0:
            estado.servo_estado["sonar_disponible"] = False
            estado.servo_estado["sonar_motivo"] = "suma_invalida"
            return False

        comando = config.KP_PASILLO * error / suma
        estado.servo_estado["sonar_motivo"] = "pasillo"
    elif izquierdo_valido:
        error = izquierdo - config.DISTANCIA_PARED_OBJETIVO_CM
        comando = config.KP_PARED * error / config.DISTANCIA_PARED_OBJETIVO_CM
        estado.servo_estado["sonar_motivo"] = "pared_izquierda"
    else:
        error = config.DISTANCIA_PARED_OBJETIVO_CM - derecho
        comando = config.KP_PARED * error / config.DISTANCIA_PARED_OBJETIVO_CM
        estado.servo_estado["sonar_motivo"] = "pared_derecha"

    if config.INVERTIR_SONAR:
        comando = -comando

    fijar_servo_objetivo(comando_a_servo(comando))
    estado.servo_estado["sonar_disponible"] = True
    return True

def servo_objetivo_desde_camara():
    detecciones = estado.estado["camara"]["detecciones"]

    # La camara solo participa cuando hay una deteccion real de color.
    if not estado.estado["camara"]["ok"] or not estado.estado["camara"]["detectado"]:
        return False

    objetivo = None
    objetivo_x = None

    # Cada id puede apuntar al borde izquierdo o derecho de la imagen.
    # Esto permite que varios colores/objetos compartan el mismo objetivo visual.
    for deteccion in detecciones:
        deteccion_id = deteccion.get("id")

        if deteccion_id in config.IDS_CAMARA_X_MIN:
            objetivo = deteccion
            objetivo_x = config.X_MIN
            break

        if deteccion_id in config.IDS_CAMARA_X_MAX:
            objetivo = deteccion
            objetivo_x = config.X_MAX
            break

    if objetivo is None:
        return False

    x = objetivo.get("x")
    y = objetivo.get("y")
    w = objetivo.get("w")
    h = objetivo.get("h")

    # Si faltan datos, la lectura no es util para mandar el servo.
    if x is None or y is None or w is None or h is None:
        return False

    # Filtros de zona y tamano: evitan que ruido o detecciones parciales
    # generen direccion sobre el servo.
    if not (
        config.X_MIN <= x <= config.X_MAX and
        config.Y_MIN <= y <= config.Y_MAX and
        config.W_MIN <= w <= config.W_MAX and
        config.H_MIN <= h <= config.H_MAX
    ):
        return False

    izquierdo = estado.estado["sonar"]["izquierdo"]
    derecho = estado.estado["sonar"]["derecho"]
    centro_x = (config.X_MIN + config.X_MAX) / 2

    # La camara no debe empujar hacia una pared que ya esta demasiado cerca.
    # En ese caso se devuelve False para que la tarea caiga a sonar/heading.
    if x < centro_x and izquierdo is not None and izquierdo <= config.DISTANCIA_MIN_PARED:
        return False

    if x > centro_x and derecho is not None and derecho <= config.DISTANCIA_MIN_PARED:
        return False

    ancho_util = config.X_MAX - config.X_MIN
    if ancho_util <= 0:
        return False

    # El error se mide contra el objetivo visual asignado al id detectado:
    # ids en IDS_CAMARA_X_MIN buscan X_MIN, ids en IDS_CAMARA_X_MAX buscan X_MAX.
    error = x - objetivo_x
    comando = config.KP_CAMARA * error / ancho_util

    if config.INVERTIR_CAMARA:
        comando = -comando

    fijar_servo_objetivo(comando_a_servo(comando))
    return True
