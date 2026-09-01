import config


def nueva_muestra(valor=None):
    return {
        "valor": valor,
        "valido": False,
        "seq": 0,
    }


def publicar_lectura(muestra, valor):
    muestra["valor"] = valor
    muestra["valido"] = True
    muestra["seq"] += 1


def marcar_invalida(muestra):
    muestra["valido"] = False


estado = {
    "navegacion": {
        "activo": False,
        "modo": "automatico",
        "maniobra": "detenido",
        "heading_ref": None,
        "heading_error": None,
        "sentido_pista": None,
        "sentido_giro": None,
        "giro_pendiente": None,
        "candidato_giro": None,
        "confirmaciones_giro_lateral": 0,
        "ultimo_seq_izquierdo": 0,
        "ultimo_seq_derecho": 0,
        "confirmaciones_fin_giro": 0,
        "ultimo_seq_imu_giro": 0,
        "esquinas": 0,
        "vueltas": 0,
        "seq_frontal_preparacion": None,
        "ultimo_seq": {},
        "ciclos_sin_actualizar": {},
        "ciclos_maniobra": 0,
        "boton_start_anterior": False,
        "frente_critico_enclavado": False,
        "fallo": None,
        "motivo_transicion": "inicio",
    },
    "motor": {
        "velocidad": 0,
        "direccion": 0,
        "freno": False,
        "ok": True,
        "error": None,
    },
    "servo": {
        "comando": 0.0,
        "ok": True,
        "error": None,
    },
    "imu": {
        "heading": None,
        "gz": None,
        "valido": False,
        "seq": 0,
    },
    "sonar": {
        "frontal": nueva_muestra(),
        "izquierdo": nueva_muestra(),
        "derecho": nueva_muestra(),
    },
    "tof": {
        "frontal": nueva_muestra(),
        "izquierdo": nueva_muestra(),
        "derecho": nueva_muestra(),
    },
    "encoder": {
        "delta": 0,
        "pasos": 0,
        "distancia": 0.0,
        "movimiento": False,
        "valido": False,
        "seq": 0,
    },
    "entradas": {
        "boton_start": nueva_muestra(False),
        "ps4": nueva_muestra(),
    },
    "camara": nueva_muestra([]),
}
