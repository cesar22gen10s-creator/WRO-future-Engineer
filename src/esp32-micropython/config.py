# Pines
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

PIN_XSHUT_FRONTAL = 13
PIN_XSHUT_IZQUIERDO = 32
PIN_XSHUT_DERECHO = 14

UART_PS4_ID = 2
UART_PS4_BAUDRATE = 115200
PIN_UART_PS4_RX = 16
PIN_UART_PS4_TX = 17


# Servo y motor
SERVO_CENTRO = 70
SERVO_DERECHA = 30
SERVO_IZQUIERDA = 110
PASO_SERVO = 8

# Semantica del comando: -1 gira a la izquierda y +1 a la derecha.
# Cambiar solo esta bandera si el varillaje fisico invierte esa relacion.
INVERTIR_COMANDO_SERVO = False
INVERTIR_SERVO_EN_RETROCESO = True

# Consignas iniciales conservadoras para una rueda de 25 cm por vuelta.
# Equivalen aproximadamente a 25, 18.8, 13.3, 15.8, 20.8 y 11.7 cm/s.
# Deben calibrarse en pista: primero con la rueda elevada y luego con carga.
RPM_AVANCE = 700
RPM_APROXIMACION = 300
RPM_GIRO = 500
RPM_RETROCESO = 400
RPM_MANUAL_MAX = 700

# Control incremental de velocidad y frenado activo. El puente H conserva como
# limite fisico los 1024 niveles de PWM (valores de 0 a 1023).
# KI_RPM define cuanto cambia el PWM por segundo por cada RPM de error.
KI_RPM = 6.0
RPM_TOLERANCIA_CONTROL = 100
RPM_EXCESO_PARA_FRENAR = 200
RPM_TOLERANCIA = RPM_TOLERANCIA_CONTROL
RPM_PARADO = 10
PWM_FRENO = 250

# Cadencias cooperativas (milisegundos)
PERIODO_NAVEGACION_MS = 20
PERIODO_IMU_MS = 5
PERIODO_SONAR_MS = 30
SEPARACION_SONARES_MS = 8
PERIODO_TOF_POLL_MS = 8
PERIODO_ENCODER_MS = 10
PERIODO_ACTUADOR_MS = 10
PERIODO_ENTRADAS_MS = 20
PERIODO_DEBUG_MS = 1000

# Frescura por fuente
EDAD_MAX_IMU_MS = 300
EDAD_MAX_SONAR_MS = 300
EDAD_MAX_TOF_MS = 300
EDAD_MAX_ENCODER_MS = 200
# Caduca por ausencia de tramas UART validas, aunque los botones no cambien.
TIMEOUT_SIN_UART_PS4_MS = 300
DESFASE_MAX_TOF_MS = 60
DESFASE_MAX_SONAR_MS = 100
VENTANA_TRANSICION_SONAR_GIRO_MS = 1200

# Sonares perpendiculares: delimitan el pasillo y detectan sus aperturas.
SONAR_MAX_CM = 260
DISTANCIA_MIN_VALIDA_CM = 5
SONAR_PASILLO_MAX_CM = 130
SONAR_LADO_ABIERTO_CM = 130
# Una apertura sonar exige proporcion y diferencia absoluta. Esto permite
# reconocer pistas de distinto ancho sin confundir pequenas desalineaciones.
FACTOR_APERTURA_SONAR = 1.7
DELTA_APERTURA_SONAR_CM = 30

# Frontal: cada fuente conserva su propia magnitud. Estos umbrales producen
# conclusiones booleanas; nunca se promedian sonar y ToF.
SONAR_FRONTAL_ENTRAR_APROX_CM = 50
SONAR_FRONTAL_SALIR_APROX_CM = 70
SONAR_FRONTAL_CRITICO_CM = 20
SONAR_FRONTAL_LIBRE_CM = 70

TOF_FRONTAL_ENTRAR_APROX_CM = 70
TOF_FRONTAL_SALIR_APROX_CM = 80
TOF_FRONTAL_CRITICO_CM = 25
TOF_FRONTAL_LIBRE_CM = 80

# El giro se prepara detenido y solo comienza con este espacio frontal.
DISTANCIA_FRONTAL_MIN_GIRO_CM = 40
DISTANCIA_FRONTAL_INICIO_GIRO_FLUIDO_CM = 60


TOF_MIN_VALIDO_CM = 2
TOF_LATERAL_RANGO_UTIL_CM = 45
TOF_LATERAL_PELIGRO_CM = 25
COMANDO_EVASION_TOF = 0.8
# Los ToF diagonales solo anticipan una posible apertura durante aproximacion;
# el sonar decide el sentido final antes de iniciar el giro.
FACTOR_APERTURA_TOF = 1.5
DELTA_APERTURA_TOF_CM = 10
TOF_FRONTAL_RANGO_UTIL_CM = 200
ZONA_MUERTA_ASIMETRIA_TOF = 0.03
KP_CORRECCION_TOF = 3
# Con el montaje nominal, TI > TD exige corregir a la izquierda (-1).
SIGNO_CORRECCION_TOF = 1
MUESTRAS_CONFIRMAR_ESQUINA = 3
MUESTRAS_CONFIRMAR_PASILLO = 3

# Heading y control
ERROR_HEADING_MAX = 28.0
KP_HEADING_RECTA = 0.75
KP_HEADING_APROX = 0.9
KP_HEADING_GIRO = 1.35
COMANDO_GIRO_MIN = 0.45
ERROR_GIRO_PERMITIDO = 9.0
MUESTRAS_CONFIRMAR_GIRO = 3
# Si el signo medido por el IMU esta invertido respecto al montaje, cambiar
# esta constante entre +1 y -1. El objetivo y el control usan el mismo signo.
SIGNO_HEADING_DERECHA = -1

# Histeresis de proteccion.
MIN_SALIDA_MS = 350
PAUSA_PREPARACION_GIRO_MS = 120
MAX_RETROCESO_GIRO_CM = 35

# Encoder
DISTANCIA_POR_VUELTA_RUEDA_CM = 25.0
# El montaje nominal cuenta negativo al avanzar. Cambiar solo este signo si la
# telemetria de avance resulta negativa; no invertir el calculo en otros modulos.
SIGNO_RPM_ENCODER = -1
DELTA_ENCODER_MOVIMIENTO_MIN = 2

# ToF: direcciones unicas y recuperacion acotada
TOF_DIRECCION_FRONTAL = 0x2A
TOF_DIRECCION_IZQUIERDO = 0x2B
TOF_DIRECCION_DERECHO = 0x2C
TOF_MAX_INTENTOS_INICIALIZACION = 2
TOF_TIMEOUT_MUESTRA_MS = 500
TOF_ERRORES_ANTES_REINICIO = 3
TOF_BACKOFF_REINICIO_MS = 3000

# Las ordenes caducan si navegacion deja de ejecutarse. Esto no decide la FSM;
# solo hace que los actuadores vuelvan a una condicion segura.
VIGENCIA_ORDEN_MS = 150

# Open Challenge: cero significa recorrido indefinido para puesta a punto.
VUELTAS_OBJETIVO_OPEN = 0

# Camara (deshabilitada en Open; se conserva para una fase posterior)
X_MIN = 0
X_MAX = 320
Y_MIN = 0
Y_MAX = 240
W_MIN = 24
W_MAX = 70
H_MIN = 24
H_MAX = 80
IDS_CAMARA_X_MIN = (1, 2)
IDS_CAMARA_X_MAX = (3,)
KP_CAMARA = 1.8
