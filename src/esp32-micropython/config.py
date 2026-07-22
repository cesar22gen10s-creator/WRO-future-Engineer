# ============================================================
# PINES
# ============================================================

PIN_SERVO = 27
PIN_BTN_A = 33

PIN_SCL = 22
PIN_SDA = 21

PIN_PUENTEH_ENA = 15
PIN_PUENTEH_IN1 = 4
PIN_PUENTEH_IN2 = 2

PIN_SONAR_FRONTAL_TRIGGER = 5
PIN_SONAR_FRONTAL_ECHO = 18

PIN_SONAR_IZQUIERDO_TRIGGER = 26
PIN_SONAR_IZQUIERDO_ECHO = 25

PIN_SONAR_DERECHO_TRIGGER = 23
PIN_SONAR_DERECHO_ECHO = 19


# ============================================================
# SERVO / MOTOR
# ============================================================

SERVO_CENTRO = 70
SERVO_DERECHA = 30
SERVO_IZQUIERDA = 110

VELOCIDAD_AVANCE = 800 
VELOCIDAD_RETROCESO = 600
VELOCIDAD_APROXIMACION = 600

PASO_SERVO = 2
INVERTIR_SERVO = True


# ============================================================
# SONARES
# ============================================================

SONAR_MAX_CM = 260
DISTANCIA_MIN_VALIDA = 2
DISTANCIA_MIN_PARED = 15
DISTANCIA_PARED_OBJETIVO_CM = 25
DISTANCIA_FRONTAL_FRENADO_CM = 55
DISTANCIA_FRONTAL_FIN_FRENADO_CM = 30
INVERTIR_SONAR = True


# ============================================================
# GIRO POR IMU
# ============================================================

ERROR_GIRO_PERMITIDO = 10
KP_HEADING = 1
KP_PASILLO = 1.5
ERROR_HEADING_MAX = 28.0
INVERTIR_HEADING = False

FRONTAL_MIN_ANTES_GIRO_CM = 30
DISTANCIA_POR_VUELTA_CM = 25


# ============================================================
# CONTROL PROPORCIONAL POR CAMARA
# ============================================================

X_MIN = 0
X_MAX = 320
Y_MIN = 0
Y_MAX = 240
W_MIN = 24
W_MAX = 70
H_MIN = 24
H_MAX = 80
IDS_CAMARA_X_MIN = (1, 2) #ROJO
IDS_CAMARA_X_MAX = (3) #VERDE
KP_CAMARA = 1.8
INVERTIR_CAMARA = True


# ============================================================
# NAVEGACION
# ============================================================

DISTANCIA_GIRO_MIN_CM = 50
PASILLO_CM = 80

#nuevo: parametros para maniobra de esquiva de obstaculos de colores
HEADING_ESQUIVA = 20
DISTANCIA_FRONTAL_ESQUIVA_CM = 15
DISTANCIA_ESQUIVA_LARGO_CM = 25
