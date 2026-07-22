#estado.py
import config
estado = {
    "btn_a":{
        "memoria": 0
    },
    "motor":{
        "activo": False,
        "velocidad": config.VELOCIDAD_AVANCE,
        "direccion": 0,
        "maniobra": "avance"
    },
    "imu": {
        "ok": False,
        "error": None,
        "heading": 0.0,
        "gz": 0.0,
        "heading_ref": 0,
        "heading_error": None,
        "timestamp": 0,
        "actualizaciones": 0,
        "velocidad": 0.0,
    },

    "servo": {
        "ok": False,
        "error": None,
        "actual": config.SERVO_CENTRO,
        "objetivo": config.SERVO_CENTRO,
        "modo_correccion": "heading",
        "sonar_disponible": False,
        "sonar_motivo": "sin_datos",
        "paso": config.PASO_SERVO,
        "timestamp": 0,
        "actualizaciones": 0,
    },
    "sonar": {
        "ok": False,
        "error": None,
        "frontal": None,
        "izquierdo": None,
        "derecho": None,
        "tof": None,
        "timestamp": 0,
        "actualizaciones": 0,
    },

    "encoder": {
        "delta": 0,
        "distancia_cm": 0.0,
        "timestamp": 0,
        "movimiento": False,
        "actualizaciones": 0,
    },

    "camara": {
        "ok": False,
        "error": None,
        "firmware": None,
        "funcion": None,
        "detectado": False,
        "cantidad": 0,
        "ids": [],
        "detecciones": [],
    },
}


imu_estado = estado["imu"]
servo_estado = estado["servo"]
dist_frontal = estado["sonar"]["frontal"]
dist_izquierdo = estado["sonar"]["izquierdo"]
dist_derecho = estado["sonar"]["derecho"]
motor_estado = estado["motor"]
camara_estado = estado["camara"]
