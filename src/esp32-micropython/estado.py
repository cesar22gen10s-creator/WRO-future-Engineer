import config


def nueva_muestra(valor=None):
    return {
        "valor": valor,
        "valido": False,
        "fuera_rango": False,
        "capturado_ms": 0,
        "actualizado_ms": 0,
        "seq": 0,
        "actualizaciones": 0,
        "error": None,
        "errores_consecutivos": 0,
        "fuera_servicio": False,
    }


def nueva_muestra_imu():
    muestra = nueva_muestra()
    muestra["heading"] = None
    muestra["gz"] = None
    return muestra


def nueva_muestra_encoder():
    muestra = nueva_muestra()
    muestra["delta"] = 0
    muestra["pasos_acumulados"] = 0
    muestra["distancia_acumulada_cm"] = 0.0
    muestra["rpm"] = None
    muestra["movimiento"] = False
    return muestra


def nueva_muestra_ps4():
    muestra = nueva_muestra(None)
    muestra["cortes_uart"] = 0
    return muestra


def nueva_orden_motor():
    return {
        "rpm_objetivo": 0.0,
        "direccion": 0,
        "frenar": False,
        "emitida_ms": 0,
        "vigencia_ms": config.VIGENCIA_ORDEN_MS,
        "seq": 0,
        "motivo": "inicio",
    }


def nueva_orden_servo():
    return {
        "comando": 0.0,
        "emitida_ms": 0,
        "vigencia_ms": config.VIGENCIA_ORDEN_MS,
        "seq": 0,
        "motivo": "inicio",
    }


def nuevo_estado():
    return {
        "entradas": {
            "boton_start": nueva_muestra(False),
            "ps4": nueva_muestra_ps4(),
        },
        "sensores": {
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
            "imu": nueva_muestra_imu(),
            "encoder": nueva_muestra_encoder(),
            "camara": nueva_muestra(None),
        },
        "navegacion": {
            "modo": "automatico",
            "activo": False,
            "maniobra": "detenido",
            "sentido_pista": None,
            "sentido_giro": None,
            "sentido_giro_pendiente": None,
            "candidato_tof_giro": None,
            "sentido_giro_fluido_confirmado": None,
            "ultimo_frame_sonar_planificacion": None,
            "heading_ref": None,
            "heading_error": None,
            "estado_desde_ms": 0,
            "motivo_transicion": "inicio",
            "candidato_esquina": None,
            "confirmaciones_esquina": 0,
            "ultimo_frame_sonar_esquina": None,
            "confirmaciones_giro": 0,
            "ultimo_seq_imu_giro": 0,
            "confirmaciones_pasillo": 0,
            "ultimo_frame_sonar_pasillo": None,
            "pasillo_sonar_previo": False,
            "ultimo_pasillo_sonar_ms": None,
            "ultimo_frame_sonar_previo": None,
            "frame_frontal_preparacion": None,
            "distancia_inicio_retroceso_cm": None,
            "asimetria_tof": None,
            "esquinas": 0,
            "vueltas": 0,
            "fallo": None,
            "ultimo_movimiento_ms": 0,
            "activado_ms": 0,
        },
        "ordenes": {
            "motor": nueva_orden_motor(),
            "servo": nueva_orden_servo(),
        },
        "actuadores": {
            "motor": {
                "rpm_objetivo": 0.0,
                "rpm_medida": None,
                "pwm_aplicado": 0,
                "direccion": 0,
                "fase": "detenido",
                "saturado": False,
                "aplicada_ms": 0,
                "orden_seq": 0,
                "ok": False,
                "error": None,
            },
            "servo": {
                "comando": 0.0,
                "angulo": config.SERVO_CENTRO,
                "aplicada_ms": 0,
                "orden_seq": 0,
                "ok": False,
                "error": None,
            },
        },
    }


def publicar_muestra(muestra, valor, ahora_ms, fuera_rango=False):
    muestra["valor"] = valor
    muestra["valido"] = True
    muestra["fuera_rango"] = bool(fuera_rango)
    muestra["capturado_ms"] = ahora_ms
    muestra["actualizado_ms"] = ahora_ms
    muestra["seq"] += 1
    muestra["actualizaciones"] += 1
    muestra["error"] = None
    muestra["errores_consecutivos"] = 0
    muestra["fuera_servicio"] = False


def publicar_error(muestra, error, ahora_ms, fuera_servicio=False):
    """Invalida solo la fuente que fallo sin refrescar su ultima captura."""
    muestra["valido"] = False
    muestra["actualizado_ms"] = ahora_ms
    muestra["actualizaciones"] += 1
    muestra["error"] = str(error)
    muestra["errores_consecutivos"] += 1
    muestra["fuera_servicio"] = bool(fuera_servicio)


def publicar_imu(muestra, heading, gz, ahora_ms):
    publicar_muestra(muestra, heading, ahora_ms)
    muestra["heading"] = heading
    muestra["gz"] = gz


def publicar_encoder(
    muestra,
    delta,
    pasos_acumulados,
    distancia_acumulada_cm,
    rpm,
    movimiento,
    ahora_ms,
):
    publicar_muestra(muestra, delta, ahora_ms)
    muestra["delta"] = delta
    muestra["pasos_acumulados"] = pasos_acumulados
    muestra["distancia_acumulada_cm"] = distancia_acumulada_cm
    muestra["rpm"] = rpm
    muestra["movimiento"] = bool(movimiento)


def emitir_orden_motor(
    orden,
    rpm_objetivo,
    direccion,
    ahora_ms,
    motivo,
    frenar=False,
):
    orden["rpm_objetivo"] = float(rpm_objetivo)
    orden["direccion"] = int(direccion)
    orden["frenar"] = bool(frenar)
    orden["emitida_ms"] = ahora_ms
    orden["vigencia_ms"] = config.VIGENCIA_ORDEN_MS
    orden["seq"] += 1
    orden["motivo"] = motivo


def emitir_orden_servo(orden, comando, ahora_ms, motivo):
    orden["comando"] = float(comando)
    orden["emitida_ms"] = ahora_ms
    orden["vigencia_ms"] = config.VIGENCIA_ORDEN_MS
    orden["seq"] += 1
    orden["motivo"] = motivo


# Instancia utilizada en la placa. Las pruebas crean estados aislados.
estado = nuevo_estado()
