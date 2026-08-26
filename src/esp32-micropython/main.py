import time
import uasyncio  # type: ignore

import ble_debug

# BLE reserva memoria interna antes de cargar el resto del vehiculo. La tarea
# de transmision se crea mas tarde, cuando el event loop ya esta ejecutandose.
ble_debug.preparar()

import actuadores
import config
import estado
import hardware
import sensores
import utilidades
from navegacion import NavegadorOpen


sistema = estado.estado
navegador = NavegadorOpen()


async def ejecutar_navegacion():
    while True:
        try:
            navegador.actualizar(sistema, time.ticks_ms())
        except Exception as exc:
            navegador.forzar_fallo(sistema, time.ticks_ms(), "excepcion_navegacion: " + str(exc))
        await uasyncio.sleep_ms(config.PERIODO_NAVEGACION_MS)


def _dato_debug(nombre, muestra, ahora_ms):
    valor = utilidades.format1(muestra.get("valor"))
    if muestra.get("seq", 0) > 0:
        edad = utilidades.diferencia_ms(ahora_ms, muestra.get("capturado_ms", 0))
    else:
        edad = "-"
    salud = "ok" if muestra.get("valido") else "X"
    if muestra.get("fuera_servicio"):
        salud = "OOS"
    if not muestra.get("valido") and muestra.get("error"):
        salud += ":" + str(muestra["error"])[:18]
    return "{}:{} {}ms #{} {}".format(nombre, valor, edad, muestra.get("seq", 0), salud)


async def debug():
    while True:
        ahora = time.ticks_ms()
        sensores_estado = sistema["sensores"]
        sonar = sensores_estado["sonar"]
        tof = sensores_estado["tof"]
        imu = sensores_estado["imu"]
        nav = sistema["navegacion"]
        orden_motor = sistema["ordenes"]["motor"]
        motor = sistema["actuadores"]["motor"]
        servo = sistema["ordenes"]["servo"]
        linea = (
            "{} | {} | {} | {} | {} | {} | "
            "H:{} REF:{} ERR:{} | MODO:{} MN:{} SENT:{} | "
            "RPM_OBJ:{} RPM_MED:{} PWM:{} DIR:{} FASE:{} "
            "FRENO_ORD:{} SAT:{} ACT_OK:{} ACT_ERR:{} SERVO:{} | "
            "TR:{} | A:{} E:{} V:{}"
            .format(
                _dato_debug("SF", sonar["frontal"], ahora),
                _dato_debug("TF", tof["frontal"], ahora),
                _dato_debug("SI", sonar["izquierdo"], ahora),
                _dato_debug("TI", tof["izquierdo"], ahora),
                _dato_debug("TD", tof["derecho"], ahora),
                _dato_debug("SD", sonar["derecho"], ahora),
                utilidades.format1(imu.get("heading")),
                utilidades.format1(nav.get("heading_ref")),
                utilidades.format1(nav.get("heading_error")),
                nav["modo"],
                nav["maniobra"],
                nav["sentido_pista"],
                utilidades.format1(motor.get("rpm_objetivo")),
                utilidades.format1(motor.get("rpm_medida")),
                motor.get("pwm_aplicado", 0),
                motor.get("direccion", 0),
                motor.get("fase", "-"),
                orden_motor.get("frenar", False),
                motor.get("saturado", False),
                motor.get("ok", False),
                str(motor.get("error") or "-")[:24],
                utilidades.format1(servo["comando"]),
                nav["motivo_transicion"],
                utilidades.format1(nav["asimetria_tof"]),
                nav["esquinas"],
                nav["vueltas"],
            )
        )
        print(linea, end = "\r\n\r\n")
        ble_debug.publicar(linea)
        await uasyncio.sleep_ms(config.PERIODO_DEBUG_MS)


async def main():
    errores_tof = hardware.inicializar_tofs()
    sensores.registrar_estado_inicial_tofs(sistema, errores_tof)
    ble_debug.iniciar()

    # Los sensores se crean siempre; la camara queda fuera del Open Challenge.
    uasyncio.create_task(sensores.leer_imu(sistema))
    uasyncio.create_task(sensores.leer_sonares(sistema))
    uasyncio.create_task(sensores.leer_tofs(sistema))
    uasyncio.create_task(sensores.leer_encoder(sistema))
    uasyncio.create_task(sensores.leer_boton_start(sistema))
    uasyncio.create_task(sensores.leer_control_ps4(sistema))
    
    uasyncio.create_task(ejecutar_navegacion())
    uasyncio.create_task(actuadores.ejecutar_motor(sistema))
    uasyncio.create_task(actuadores.ejecutar_servo(sistema))
    uasyncio.create_task(debug())

    while True:
        await uasyncio.sleep_ms(1000)


if __name__ == "__main__":
    try:
        uasyncio.run(main())
    finally:
        actuadores.detener_seguro(sistema)
