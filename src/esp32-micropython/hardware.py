"""Construccion de hardware y gestion acotada de los ToF."""

import time

from machine import I2C, Pin, UART  # type: ignore

import VL53L0X
import config
from componentes import BMI160, Encoder_AS5600, MotorPuenteH, Servo, SonarBit, WonderCam
from ps4_uart import LectorPS4UART


motor = MotorPuenteH(
    config.PIN_PUENTEH_ENA,
    config.PIN_PUENTEH_IN1,
    config.PIN_PUENTEH_IN2,
)
servo = Servo(config.PIN_SERVO, angulo_inicial=config.SERVO_CENTRO)
servo.mover(config.SERVO_CENTRO, espera=False)

uart_ps4 = UART(
    config.UART_PS4_ID,
    baudrate=config.UART_PS4_BAUDRATE,
    tx=config.PIN_UART_PS4_TX,
    rx=config.PIN_UART_PS4_RX,
)
lector_ps4 = LectorPS4UART(uart_ps4)

sonar_frontal = SonarBit(
    config.PIN_SONAR_FRONTAL_TRIGGER,
    config.PIN_SONAR_FRONTAL_ECHO,
    config.SONAR_MAX_CM,
)
sonar_izquierdo = SonarBit(
    config.PIN_SONAR_IZQUIERDO_TRIGGER,
    config.PIN_SONAR_IZQUIERDO_ECHO,
    config.SONAR_MAX_CM,
)
sonar_derecho = SonarBit(
    config.PIN_SONAR_DERECHO_TRIGGER,
    config.PIN_SONAR_DERECHO_ECHO,
    config.SONAR_MAX_CM,
)

btn_a = Pin(config.PIN_BTN_A, Pin.IN, Pin.PULL_UP)
i2c = I2C(
    0,
    scl=Pin(config.PIN_SCL),
    sda=Pin(config.PIN_SDA),
    freq=400000,
)

_xshut = {
    "frontal": Pin(config.PIN_XSHUT_FRONTAL, Pin.OUT),
    "izquierdo": Pin(config.PIN_XSHUT_IZQUIERDO, Pin.OUT),
    "derecho": Pin(config.PIN_XSHUT_DERECHO, Pin.OUT),
}
for _pin_xshut in _xshut.values():
    _pin_xshut.value(0)
time.sleep_ms(5)
_direcciones_tof = {
    "frontal": config.TOF_DIRECCION_FRONTAL,
    "izquierdo": config.TOF_DIRECCION_IZQUIERDO,
    "derecho": config.TOF_DIRECCION_DERECHO,
}
tofs = {
    "frontal": None,
    "izquierdo": None,
    "derecho": None,
}


def _apagar_tof(nombre):
    sensor = tofs.get(nombre)
    if sensor is not None:
        try:
            sensor.stop()
        except Exception:
            pass
    _xshut[nombre].value(0)
    tofs[nombre] = None


def _crear_tof(nombre):
    pin = _xshut[nombre]
    direccion = _direcciones_tof[nombre]
    pin.value(1)
    time.sleep_ms(12)
    sensor = VL53L0X.VL53L0X(i2c, address=0x29)
    sensor.set_address(direccion)
    if direccion not in i2c.scan():
        raise OSError("ToF {} no responde en 0x{:02X}".format(nombre, direccion))
    sensor.start()
    tofs[nombre] = sensor
    return sensor


def reinicializar_tof(
    nombre,
    intentos=config.TOF_MAX_INTENTOS_INICIALIZACION,
):
    """Reconstruye un ToF con intentos limitados y deja los demas activos."""
    if nombre not in tofs:
        raise ValueError("ToF desconocido: " + str(nombre))
    ultimo_error = None
    _apagar_tof(nombre)
    time.sleep_ms(5)
    for _ in range(max(1, int(intentos))):
        try:                          
            return _crear_tof(nombre), None
        except Exception as exc:
            ultimo_error = exc
            _apagar_tof(nombre)
            time.sleep_ms(15)
    return None, str(ultimo_error or "sin respuesta")


def inicializar_tofs(
    intentos=config.TOF_MAX_INTENTOS_INICIALIZACION,
):
    """Inicializa secuencialmente; un ausente no bloquea a los otros."""
    for nombre in tofs:
        _apagar_tof(nombre)
    time.sleep_ms(15)
    errores = {}
    for nombre in ("frontal", "izquierdo", "derecho"):
        sensor, error = reinicializar_tof(nombre, intentos)
        if sensor is None:
            errores[nombre] = error
    return errores


def obtener_tof(nombre):
    return tofs.get(nombre)


def poner_tof_fuera_servicio(nombre):
    if nombre not in tofs:
        raise ValueError("ToF desconocido: " + str(nombre))
    _apagar_tof(nombre)


encoder = Encoder_AS5600(i2c)
imu = BMI160(i2c)
camara = WonderCam(i2c)
