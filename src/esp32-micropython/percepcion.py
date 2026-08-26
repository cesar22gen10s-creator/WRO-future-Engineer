import config
import utilidades


def muestra_fresca(muestra, ahora_ms, edad_max_ms):
    if not isinstance(muestra, dict):
        return False
    if not muestra.get("valido") or muestra.get("fuera_servicio"):
        return False
    if muestra.get("seq", 0) <= 0:
        return False
    capturado_ms = muestra.get("capturado_ms")
    if not utilidades.numero_finito(capturado_ms):
        return False
    edad = utilidades.diferencia_ms(ahora_ms, capturado_ms)
    return 0 <= edad <= edad_max_ms


def valor_fresco(muestra, ahora_ms, edad_max_ms):
    if not muestra_fresca(muestra, ahora_ms, edad_max_ms):
        return None
    valor = muestra.get("valor")
    return valor if utilidades.numero_finito(valor) else None


def _indica_cerca(muestra, valor, umbral):
    return (valor is not None and not muestra.get("fuera_rango", False) and valor <= umbral)


def _indica_libre(muestra, valor, umbral):
    if valor is None:
        return None
    return bool(muestra.get("fuera_rango", False) or valor >= umbral)


def _cumple_distancia_minima(muestra, valor, minimo_cm):
    if valor is None:
        return None
    return bool(muestra.get("fuera_rango", False) or valor >= minimo_cm)


def _cumple_distancia_maxima(muestra, valor, maximo_cm):
    if valor is None:
        return None
    return bool(
        not muestra.get("fuera_rango", False)
        and valor < maximo_cm
    )


def observar_frente(sonar_frontal, tof_frontal, ahora_ms):
    sonar = valor_fresco(sonar_frontal, ahora_ms, config.EDAD_MAX_SONAR_MS)
    tof = valor_fresco(tof_frontal, ahora_ms, config.EDAD_MAX_TOF_MS)

    fuentes = []
    if sonar is not None:
        fuentes.append("sonar")
    if tof is not None:
        fuentes.append("tof")

    aproximacion = (
        _indica_cerca(
            sonar_frontal,
            sonar,
            config.SONAR_FRONTAL_ENTRAR_APROX_CM,
        )
        or _indica_cerca(
            tof_frontal,
            tof,
            config.TOF_FRONTAL_ENTRAR_APROX_CM,
        )
    )
    critico = (
        _indica_cerca(
            sonar_frontal,
            sonar,
            config.SONAR_FRONTAL_CRITICO_CM,
        )
        or _indica_cerca(
            tof_frontal,
            tof,
            config.TOF_FRONTAL_CRITICO_CM,
        )
    )

    informes_libre = []

    sonar_libre = _indica_libre(sonar_frontal, sonar, config.SONAR_FRONTAL_LIBRE_CM)
    tof_libre = _indica_libre(tof_frontal, tof, config.TOF_FRONTAL_LIBRE_CM)

    if sonar_libre is not None:
        informes_libre.append(sonar_libre)
    if tof_libre is not None:
        informes_libre.append(tof_libre)
    libre = bool(informes_libre) and all(informes_libre)

    informes_espacio_giro = []
    for informe in (
        _cumple_distancia_minima(
            sonar_frontal,
            sonar,
            config.DISTANCIA_FRONTAL_MIN_GIRO_CM,
        ),
        _cumple_distancia_minima(
            tof_frontal,
            tof,
            config.DISTANCIA_FRONTAL_MIN_GIRO_CM,
        ),
    ):
        if informe is not None:
            informes_espacio_giro.append(informe)

    informes_cerca_para_giro = []
    for informe in (
        _cumple_distancia_maxima(
            sonar_frontal,
            sonar,
            config.DISTANCIA_FRONTAL_INICIO_GIRO_FLUIDO_CM,
        ),
        _cumple_distancia_maxima(
            tof_frontal,
            tof,
            config.DISTANCIA_FRONTAL_INICIO_GIRO_FLUIDO_CM,
        ),
    ):
        if informe is not None:
            informes_cerca_para_giro.append(informe)

    informes_salir = []
    if sonar is not None:
        informes_salir.append(
            sonar_frontal.get("fuera_rango", False)
            or sonar >= config.SONAR_FRONTAL_SALIR_APROX_CM
        )
    if tof is not None:
        informes_salir.append(
            tof_frontal.get("fuera_rango", False)
            or tof >= config.TOF_FRONTAL_SALIR_APROX_CM
        )

    return {
        "sonar_cm": sonar,
        "tof_cm": tof,
        "fuentes": tuple(fuentes),
        "disponible": bool(fuentes),
        "aproximacion": bool(aproximacion),
        "critico": bool(critico),
        "libre": libre,
        "salir_aproximacion": bool(informes_salir) and all(informes_salir),
        "espacio_giro": (
            bool(informes_espacio_giro) and all(informes_espacio_giro)
        ),
        "ventana_giro_fluido": (
            not critico
            and bool(informes_cerca_para_giro)
            and all(informes_cerca_para_giro)
        ),
        "frame": (
            sonar_frontal.get("seq", 0) if sonar is not None else 0,
            tof_frontal.get("seq", 0) if tof is not None else 0,
        ),
    }


def _tof_lateral_util(muestra, valor):
    return bool(
        valor is not None
        and not muestra.get("fuera_rango", False)
        and config.TOF_MIN_VALIDO_CM
        <= valor
        <= config.TOF_LATERAL_RANGO_UTIL_CM
    )


def _tof_lateral_en_peligro(muestra, valor):
    return bool(
        valor is not None
        and not muestra.get("fuera_rango", False)
        and config.TOF_MIN_VALIDO_CM
        <= valor
        <= config.TOF_LATERAL_PELIGRO_CM
    )


def _es_apertura_proporcional(
    valor,
    muestra,
    opuesto,
    referencia_opuesta_valida,
    factor,
    delta_minima_cm,
):
    """Compara un lado abierto contra una referencia opuesta observable."""
    if valor is None or opuesto is None or not referencia_opuesta_valida:
        return False
    if muestra.get("fuera_rango", False):
        return True
    return bool(
        valor - opuesto >= delta_minima_cm
        and valor >= opuesto * factor
    )


def observar_tofs_laterales(tof_izquierdo, tof_derecho, ahora_ms):
    ti = valor_fresco(tof_izquierdo, ahora_ms, config.EDAD_MAX_TOF_MS)
    td = valor_fresco(tof_derecho, ahora_ms, config.EDAD_MAX_TOF_MS)
    frame = None
    coherente = False
    if ti is not None and td is not None:
        desfase = abs(
            utilidades.diferencia_ms(
                tof_izquierdo.get("capturado_ms", 0),
                tof_derecho.get("capturado_ms", 0),
            )
        )

        coherente = desfase <= config.DESFASE_MAX_TOF_MS

    if coherente:
        frame = (tof_izquierdo.get("seq", 0), tof_derecho.get("seq", 0))

    asimetria = None
    if coherente and ti + td > 0:
        asimetria = (ti - td) / (ti + td)

    util_izquierdo = _tof_lateral_util(tof_izquierdo, ti)
    util_derecho = _tof_lateral_util(tof_derecho, td)
    pasillo_observable = coherente and util_izquierdo and util_derecho
    abierto_izquierdo = coherente and _es_apertura_proporcional(
        ti,
        tof_izquierdo,
        td,
        util_derecho,
        config.FACTOR_APERTURA_TOF,
        config.DELTA_APERTURA_TOF_CM,
    )
    abierto_derecho = coherente and _es_apertura_proporcional(
        td,
        tof_derecho,
        ti,
        util_izquierdo,
        config.FACTOR_APERTURA_TOF,
        config.DELTA_APERTURA_TOF_CM,
    )
    pistas = []
    candidato = None
    if abierto_izquierdo and not abierto_derecho:
        candidato = "izquierda"
    elif abierto_derecho and not abierto_izquierdo:
        candidato = "derecha"
    if abierto_izquierdo:
        pistas.append("izquierda")
    if abierto_derecho:
        pistas.append("derecha")

    comando_centrado = (
        utilidades.control_correccion_tof(asimetria)
        if pasillo_observable
        else 0.0
    )

    peligro_izquierdo = _tof_lateral_en_peligro(tof_izquierdo, ti)
    peligro_derecho = _tof_lateral_en_peligro(tof_derecho, td)
    peligro_ambos = peligro_izquierdo and peligro_derecho
    magnitud_evasion = min(1.0, abs(config.COMANDO_EVASION_TOF))

    # Se conserva la polaridad comprobada fisicamente: un obstaculo a la
    # izquierda usa comando negativo y uno a la derecha comando positivo.
    comando_proteccion = 0.0
    if peligro_ambos:
        motivo = "tof_peligro_ambos"
    elif peligro_izquierdo:
        comando_proteccion = -magnitud_evasion
        motivo = "tof_peligro_izquierdo"
    elif peligro_derecho:
        comando_proteccion = magnitud_evasion
        motivo = "tof_peligro_derecho"
    elif not coherente:
        motivo = "tof_incoherentes"
    elif not pasillo_observable:
        motivo = "tof_sin_par_util"
    elif comando_centrado == 0.0:
        motivo = "tof_centrados"
    else:
        motivo = "correccion_tof"

    return {
        "izquierdo_cm": ti,
        "derecho_cm": td,
        "frame": frame,
        "coherente": coherente,
        "asimetria": asimetria,
        "pasillo_observable": bool(pasillo_observable),
        "abierto_izquierdo": bool(abierto_izquierdo),
        "abierto_derecho": bool(abierto_derecho),
        "pistas": tuple(pistas),
        "pista": candidato,
        "candidato": candidato,
        "peligro_izquierdo": bool(peligro_izquierdo),
        "peligro_derecho": bool(peligro_derecho),
        "peligro_ambos": bool(peligro_ambos),
        "comando_proteccion": comando_proteccion,
        "comando_correccion": comando_centrado,
        "motivo_control": motivo,
    }


def observar_sonares_laterales(sonar_izquierdo, sonar_derecho, ahora_ms):
    izquierdo = valor_fresco(
        sonar_izquierdo,
        ahora_ms,
        config.EDAD_MAX_SONAR_MS,
    )
    derecho = valor_fresco(
        sonar_derecho,
        ahora_ms,
        config.EDAD_MAX_SONAR_MS,
    )
    coherente = False
    if izquierdo is not None and derecho is not None:
        desfase = abs(
            utilidades.diferencia_ms(
                sonar_izquierdo.get("capturado_ms", 0),
                sonar_derecho.get("capturado_ms", 0),
            )
        )
        coherente = desfase <= config.DESFASE_MAX_SONAR_MS
    pared_izquierda = (
        izquierdo is not None
        and not sonar_izquierdo.get("fuera_rango", False)
        and config.DISTANCIA_MIN_VALIDA_CM
        <= izquierdo
        <= config.SONAR_PASILLO_MAX_CM
    )
    pared_derecha = (
        derecho is not None
        and not sonar_derecho.get("fuera_rango", False)
        and config.DISTANCIA_MIN_VALIDA_CM
        <= derecho
        <= config.SONAR_PASILLO_MAX_CM
    )
    abierto_izquierdo = coherente and _es_apertura_proporcional(
        izquierdo,
        sonar_izquierdo,
        derecho,
        pared_derecha,
        config.FACTOR_APERTURA_SONAR,
        config.DELTA_APERTURA_SONAR_CM,
    )
    abierto_derecho = coherente and _es_apertura_proporcional(
        derecho,
        sonar_derecho,
        izquierdo,
        pared_izquierda,
        config.FACTOR_APERTURA_SONAR,
        config.DELTA_APERTURA_SONAR_CM,
    )

    candidato = None
    if abierto_derecho and not abierto_izquierdo:
        candidato = "derecha"
    elif abierto_izquierdo and not abierto_derecho:
        candidato = "izquierda"
    pasillo_normal = (
        coherente
        and pared_izquierda
        and pared_derecha
        and candidato is None
    )
    frame = None
    if coherente:
        frame = (
            sonar_izquierdo.get("seq", 0),
            sonar_derecho.get("seq", 0),
        )
    return {
        "izquierdo_cm": izquierdo,
        "derecho_cm": derecho,
        "pared_izquierda": bool(pared_izquierda),
        "pared_derecha": bool(pared_derecha),
        "abierto_izquierdo": bool(abierto_izquierdo),
        "abierto_derecho": bool(abierto_derecho),
        "candidato": candidato,
        "pasillo_normal": bool(pasillo_normal),
        "frame": frame,
        "coherente": coherente,
    }
