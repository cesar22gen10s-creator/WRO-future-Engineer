# main.py
from machine import Pin, I2C, UART  # type: ignore
import time
from componentes import Servo, SonarBit, MotorPuenteH, Encoder_AS5600, BMI160, TCS3200, WonderCam
from movimiento_vehiculo import MovimientoDelVehiculo, ConfigVehiculo
from ps4_uart import ControlUARTVehiculo

# ===========================VARIABLES========================
#DIRECCION
PULSO_MIN_US = 518 #servo
PULSO_MAX_US = 2510 #servo
FREQ_HZ      = 50
PIN_SERVO  = 27

#BOTON
PIN_BTN_A  = 32 #ROJO 

#ENCODER Y GYRO
PIN_SCL = 22 # I2C
PIN_SDA = 21 # I2C

#PS4
PIN_UART_RX2 = 16
PIN_UART_TX2 = 17

#MOTORES
PIN_PUENTEH_ENA = 15 #VOLTAJE
PIN_PUENTEH_IN1 = 4 #DIRECCION
PIN_PUENTEH_IN2 = 2 #DIRECCION

#SONAR
PIN_SONAR_FRONTAL_TRIGGER = 5 #sonar
PIN_SONAR_FRONTAL_ECHO = 18 #sonar
PIN_SONAR_TRACERO_TRIGGER = 12 #sonar
PIN_SONAR_TRACERO_ECHO = 14 #sonar
DISTANCIA_MAXIMA_SONAR = 400


# =======================MOTORES================================
servo = Servo(pin=PIN_SERVO, angulo_inicial=0)
servo_2 = Servo(pin = 2)
servo.calibrar(pulso_min=PULSO_MIN_US, pulso_max=PULSO_MAX_US)
motor = MotorPuenteH(pin_ena = PIN_PUENTEH_ENA, pin_in1=PIN_PUENTEH_IN1, pin_in2=PIN_PUENTEH_IN2)
# =====================BOTONES=================================
btn_a = Pin(PIN_BTN_A, Pin.IN, Pin.PULL_UP)


# ========================SENSORES=============================
i2c = I2C(0, scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=400000)
print(i2c.scan())
uart = UART(2, baudrate=115200, tx=PIN_UART_TX2, rx=PIN_UART_RX2)
sonar_frontal = SonarBit(trigger_pin= PIN_SONAR_FRONTAL_TRIGGER, echo_pin=PIN_SONAR_FRONTAL_ECHO, distancia_max_cm=DISTANCIA_MAXIMA_SONAR)
sonar_tracero = SonarBit(trigger_pin= PIN_SONAR_TRACERO_TRIGGER, echo_pin=PIN_SONAR_TRACERO_ECHO, distancia_max_cm=DISTANCIA_MAXIMA_SONAR)
#bmi = BMI160(i2c, addr=0x69)   # si no responde, prueba 0x68
#bmi.iniciar()
#bmi.calibrar_bias_gyro()
# =============================================================
cfg = ConfigVehiculo()
cfg.tamano_celda_cm = 5.0
cfg.velocidad_crucero = 1000
cfg.velocidad_giro = 800
cfg.tolerancia_angulo_deg = 4.0

vehiculo = MovimientoDelVehiculo(
    motor=motor,
    servo=servo,
    #imu=bmi,
    config=cfg
)
# =============================================================
vehiculo.reset_odometria()

control = ControlUARTVehiculo(
    uart=uart,
    vehiculo=vehiculo,
    velocidad_max=1020,
    zona_muerta_stick=25,
    zona_muerta_gatillo=15,
    paso_servo=5,
    paso_motor=40,
)



import time

ADDR = 0x41

i2c = I2C(
    0,
    scl=Pin(22),
    sda=Pin(21),
    freq=100000
)

print("SCAN:", i2c.scan())

def read_u8(reg):
    return i2c.readfrom_mem(
        ADDR,
        reg,
        1,
        addrsize=16
    )[0]

def read_u16(reg):

    data = i2c.readfrom_mem(
        ADDR,
        reg,
        2,
        addrsize=16
    )

    return data[0] | (data[1] << 8)

# =========================
# firmware
# =========================

fw = i2c.readfrom_mem(
    ADDR,
    0x0000,
    16,
    addrsize=16
)

print("FW:", fw)

#control ps4


while True:
    control.actualizar(debug=True)
    time.sleep_ms(20)