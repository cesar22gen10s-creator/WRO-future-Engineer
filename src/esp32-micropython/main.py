import uasyncio  # type: ignore
import ble_debug

# Reserva BLE antes de construir el resto del hardware.
ble_debug.preparar()

import actuadores
import config
import estado
import hardware
import navegacion
import ps4_uart
import sensores
import utilidades

sistema = estado.estado

def _dato(muestra):
    valor = muestra.get("valor")
    if utilidades.numero_finito(valor):
        valor = "{:.1f}".format(valor)
    elif valor is None:
        valor = "-"
    salud = "OK" if muestra.get("valido") else "X"
    return "{}:{}#{}".format(salud, valor, muestra.get("seq", 0))


def _modo_motor(motor):
    if motor.get("freno"):
        return "FRENO"
    if motor.get("direccion") == 1 and motor.get("velocidad", 0) > 0:
        return "AVANCE"
    if motor.get("direccion") == -1 and motor.get("velocidad", 0) > 0:
        return "RETROCESO"
    return "DETENIDO"


def _linea_debug():
    nav = sistema["navegacion"]
    sonar = sistema["sonar"]
    tof = sistema["tof"]
    imu = sistema["imu"]
    encoder = sistema["encoder"]
    motor = sistema["motor"]
    servo = sistema["servo"]
    camara = sistema["camara"]
    detecciones = camara.get("valor")
    cantidad_camara = len(detecciones) if isinstance(detecciones, list) else 0
    return (
        "MODO:{} MN:{} ACT:{} "
        "H:{}/REF:{}/ERR:{}#{} {} "
        "S[F:{} I:{} D:{}] T[F:{} I:{} D:{}] "
        "ENC:{:.1f}#{} "
        "MODO_MOTOR:{} M[PWM:{} DIR:{} OK:{}] SV[CMD:{:.2f} OK:{}] "
        "GIRO[C:{} P:{} SENT:{}] E:{} V:{} "
        "CAM:{}:{}#{} TR:{}"
    ).format(
        nav["modo"],
        nav["maniobra"],
        nav["activo"],
        imu["heading"],
        nav["heading_ref"],
        nav["heading_error"],
        imu["seq"],
        "V" if imu["valido"] else "X",
        _dato(sonar["frontal"]),
        _dato(sonar["izquierdo"]),
        _dato(sonar["derecho"]),
        _dato(tof["frontal"]),
        _dato(tof["izquierdo"]),
        _dato(tof["derecho"]),
        encoder["distancia"],
        encoder["seq"],
        _modo_motor(motor),
        motor["velocidad"],
        motor["direccion"],
        motor["ok"],
        servo["comando"],
        servo["ok"],
        nav["candidato_giro"],
        nav["giro_pendiente"],
        nav["sentido_pista"],
        nav["esquinas"],
        nav["vueltas"],
        "V" if camara["valido"] else "X",
        cantidad_camara,
        camara["seq"],
        nav["motivo_transicion"],
    )

async def debug():
    while True:
        linea = _linea_debug()
        print(linea)
        ble_debug.publicar(linea)
        await uasyncio.sleep_ms(config.PERIODO_DEBUG_MS)

def _cambiar_modo_si_corresponde(cuadrado_anterior):
    muestra = sistema["entradas"]["ps4"]
    paquete = muestra.get("valor") if muestra.get("valido") else None
    cuadrado = bool(isinstance(paquete, dict) and paquete.get("conectado") and ps4_uart.boton_activo(paquete, ps4_uart.LectorPS4UART.BTN_CUADRADO))
    if cuadrado and not cuadrado_anterior:
        nav = sistema["navegacion"]
        nuevo = "manual" if nav["modo"] == "automatico" else "automatico"
        navegacion.desactivar("cambio_modo_" + nuevo)
        nav["modo"] = nuevo
    return cuadrado

async def ejecutar_control():
    cuadrado_anterior = False
    while True:
        cuadrado_anterior = _cambiar_modo_si_corresponde(
            cuadrado_anterior
        )
        nav = sistema["navegacion"]
        if nav["modo"] == "manual":
            navegacion.procesar_boton_start()
            if nav["activo"]:
                ps4_uart.actualizar_manual(sistema)
            else:
                sistema["motor"]["velocidad"] = 0
                sistema["motor"]["direccion"] = 0
                sistema["motor"]["freno"] = False
                sistema["servo"]["comando"] = 0.0
        else:
            navegacion.actualizar()
        navegacion.aplicar_proteccion_frontal()
        await uasyncio.sleep_ms(config.PERIODO_NAVEGACION_MS)

def _crear_tareas(corrutinas):
    for corrutina in corrutinas:
        uasyncio.create_task(corrutina)

async def ejecutar():
    ble_debug.iniciar()
    errores_tof = hardware.inicializar_tofs()
    if errores_tof:
        print("ToF no iniciados:", errores_tof)
    _crear_tareas((
        sensores.leer_imu(),
        sensores.leer_sonares(),
        sensores.leer_tofs(),
        sensores.leer_encoder(),
        sensores.leer_boton_start(),
        sensores.leer_ps4(),
        sensores.leer_camara(),
        actuadores.ejecutar_motor(),
        actuadores.ejecutar_servo(),
        ejecutar_control(),
    ))
    await debug()

try:
    uasyncio.run(ejecutar())
finally:
    actuadores.detener_seguro()
