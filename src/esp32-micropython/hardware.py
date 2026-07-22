# ============================================================
# HARDWARE
# ============================================================

from machine import Pin, I2C  # type: ignore
import VL53L0X
from componentes import MotorPuenteH, Encoder_AS5600, Servo, SonarBit, BMI160, FlyingFlash, WonderCam
from config import (
    PIN_BTN_A,
    PIN_PUENTEH_ENA,
    PIN_PUENTEH_IN1,
    PIN_PUENTEH_IN2,
    PIN_SCL,
    PIN_SDA,
    PIN_SERVO,
    PIN_SONAR_DERECHO_ECHO,
    PIN_SONAR_DERECHO_TRIGGER,
    PIN_SONAR_FRONTAL_ECHO,
    PIN_SONAR_FRONTAL_TRIGGER,
    PIN_SONAR_IZQUIERDO_ECHO,
    PIN_SONAR_IZQUIERDO_TRIGGER,
    SERVO_CENTRO,
    SONAR_MAX_CM,
)


motor = MotorPuenteH(PIN_PUENTEH_ENA, PIN_PUENTEH_IN1, PIN_PUENTEH_IN2)

servo = Servo(
    pin=PIN_SERVO,
    angulo_inicial=SERVO_CENTRO,
)

sonar_frontal = SonarBit(
    trigger_pin=PIN_SONAR_FRONTAL_TRIGGER,
    echo_pin=PIN_SONAR_FRONTAL_ECHO,
    distancia_max_cm=SONAR_MAX_CM,
)

sonar_izquierdo = SonarBit(
    trigger_pin=PIN_SONAR_IZQUIERDO_TRIGGER,
    echo_pin=PIN_SONAR_IZQUIERDO_ECHO,
    distancia_max_cm=SONAR_MAX_CM,
)

sonar_derecho = SonarBit(
    trigger_pin=PIN_SONAR_DERECHO_TRIGGER,
    echo_pin=PIN_SONAR_DERECHO_ECHO,
    distancia_max_cm=SONAR_MAX_CM,
)
flying_flash = FlyingFlash(pin=32)


btn_a = Pin(PIN_BTN_A, Pin.IN, Pin.PULL_UP)

i2c = I2C(0,scl=Pin(PIN_SCL),sda=Pin(PIN_SDA),freq=400000)



encoder = Encoder_AS5600(i2c)
imu = BMI160(i2c)
camara = WonderCam(i2c)
ToF = VL53L0X.VL53L0X(i2c)
print("I2C:", i2c.scan())
