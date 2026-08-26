"""Salida de diagnostico BLE no bloqueante mediante Nordic UART Service.

Los mensajes son best effort: se conserva solo el mas reciente para que una
conexion BLE lenta nunca acumule trabajo ni retrase el control del vehiculo.
"""

import gc
import uasyncio  # type: ignore

try:
    import bluetooth  # type: ignore
except ImportError:
    bluetooth = None

try:
    from micropython import const # type: ignore
except ImportError:
    def const(valor):
        return valor


_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)

_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)

_NOMBRE = "AUAA"
_UUID_SERVICIO = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
_UUID_RX = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
_UUID_TX = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

_INTERVALO_PUBLICIDAD_US = 500000

# Compatible con el MTU ATT minimo. Un bloque se descarta si la pila BLE no
# puede aceptarlo; nunca se reintenta ni se bloquea esperando espacio.
_TAMANO_BLOQUE = 20
_PAUSA_ENTRE_BLOQUES_MS = 5
_PAUSA_SIN_TRABAJO_MS = 500
_MAX_MENSAJE_BYTES = 1200


def _campo_publicidad(tipo, datos):
    return bytes((len(datos) + 1, tipo)) + datos


def _crear_publicidad(nombre, uuid_servicio):
    nombre = nombre.encode("utf-8")
    payload = bytearray(b"\x02\x01\x06")
    payload += _campo_publicidad(0x09, nombre)
    payload += _campo_publicidad(0x07, bytes(uuid_servicio))
    if len(payload) > 31:
        raise ValueError("publicidad BLE demasiado larga")
    return payload


class _SalidaBLE:
    def __init__(self):
        self._ble = None
        self._handle_tx = None
        self._conexiones = set()
        self._pendiente = None
        self._habilitada = False
        self._actualizar = True
        self._ultimo_error = None

    def _registrar_error(self, etapa, error):
        self._ultimo_error = "{}: {!r}".format(etapa, error)

    def diagnostico(self):
        if self._ultimo_error is not None:
            return self._ultimo_error
        if self._habilitada:
            return "BLE activo; conexiones={}".format(len(self._conexiones))
        return "BLE inactivo"

    def iniciar(self):
        if self._habilitada:
            return True
        if bluetooth is None:
            self._ultimo_error = "modulo bluetooth no disponible en el firmware"
            return False

        etapa = "crear_configuracion"
        try:
            # NimBLE necesita memoria interna contigua. Prepararlo antes que el
            # resto del vehiculo y recoger basura reduce la fragmentacion.
            gc.collect()
            uuid_servicio = bluetooth.UUID(_UUID_SERVICIO)
            caracteristica_tx = (
                bluetooth.UUID(_UUID_TX),
                _FLAG_READ | _FLAG_NOTIFY,
            )
            caracteristica_rx = (
                bluetooth.UUID(_UUID_RX),
                _FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE,
            )
            servicio = (
                uuid_servicio,
                (caracteristica_tx, caracteristica_rx),
            )

            etapa = "crear_radio"
            self._ble = bluetooth.BLE()

            # BLE() es un singleton. Tras una recarga suave puede conservar el
            # estado anterior; apagarlo primero libera NimBLE y el controlador.
            etapa = "reiniciar_radio"
            if self._ble.active():
                self._ble.active(False)

            etapa = "activar_radio"
            self._ble.active(True)
            if not self._ble.active():
                raise RuntimeError("la radio BLE no se activo")

            # La API exige detener la publicidad antes de registrar servicios.
            # Tambien limpia un anuncio conservado tras una recarga suave.
            etapa = "detener_publicidad_anterior"
            self._ble.gap_advertise(None)

            etapa = "configurar_nombre"
            self._ble.config(gap_name=_NOMBRE)

            etapa = "instalar_irq"
            self._ble.irq(self._irq)

            etapa = "registrar_servicio"
            handles = self._ble.gatts_register_services((servicio,))
            self._handle_tx, _ = handles[0]
            self._publicidad = _crear_publicidad(_NOMBRE, uuid_servicio)
            self._habilitada = True

            etapa = "publicidad"
            if not self._anunciar():
                self._habilitada = False
                return False
            self._ultimo_error = None
            return True
        except Exception as error:
            self._registrar_error(etapa, error)
            self._habilitada = False
            self._handle_tx = None
            self._conexiones.clear()
            if self._ble is not None:
                try:
                    self._ble.active(False)
                except Exception:
                    pass
            self._ble = None
            return False

    def _irq(self, evento, datos):
        try:
            if evento == _IRQ_CENTRAL_CONNECT:
                conexion, _, _ = datos
                self._conexiones.add(conexion)
            elif evento == _IRQ_CENTRAL_DISCONNECT:
                conexion, _, _ = datos
                self._conexiones.discard(conexion)
                self._anunciar()
        except Exception:
            pass

    def _anunciar(self):
        if not self._habilitada or self._ble is None:
            return False
        try:
            self._ble.gap_advertise(
                _INTERVALO_PUBLICIDAD_US,
                adv_data=self._publicidad,
                connectable=True,
            )
            return True
        except Exception as error:
            self._registrar_error("publicidad", error)
            return False

    def publicar(self, texto):
        if not self._actualizar or not self._habilitada or not self._conexiones:
            return
        try:
            datos = (str(texto) + "\r\n\r\n\r\n").encode("utf-8")
            self._pendiente = datos[:_MAX_MENSAJE_BYTES]
        except Exception:
            pass

    def alternar_actualizacion(self):
        self._actualizar = not self._actualizar
        if not self._actualizar:
            self._pendiente = None
        return self._actualizar

    def actualizacion_activa(self):
        return self._actualizar

    async def ejecutar(self):
        while True:
            try:
                if (
                    not self._habilitada
                    or not self._conexiones
                    or self._pendiente is None
                ):
                    await uasyncio.sleep_ms(_PAUSA_SIN_TRABAJO_MS)
                    continue

                datos = self._pendiente
                self._pendiente = None

                for inicio in range(0, len(datos), _TAMANO_BLOQUE):
                    bloque = datos[inicio:inicio + _TAMANO_BLOQUE]
                    for conexion in tuple(self._conexiones):
                        try:
                            self._ble.gatts_notify(
                                conexion,
                                self._handle_tx,
                                bloque,
                            )
                        except Exception:
                            pass
                    await uasyncio.sleep_ms(_PAUSA_ENTRE_BLOQUES_MS)
            except Exception:
                await uasyncio.sleep_ms(_PAUSA_SIN_TRABAJO_MS)


_salida = _SalidaBLE()
_tarea_iniciada = False


def preparar():
    """Reserva y anuncia BLE antes de cargar el resto del vehiculo."""
    if _salida.iniciar():
        return True
    print("BLE DEBUG NO INICIADO:", _salida.diagnostico())
    return False


def iniciar():
    """Inicia solo la tarea cooperativa que transmite los mensajes."""
    global _tarea_iniciada
    if _tarea_iniciada:
        return True
    if not preparar():
        return False
    try:
        uasyncio.create_task(_salida.ejecutar())
        _tarea_iniciada = True
        print("BLE DEBUG:", _salida.diagnostico(), "nombre=", _NOMBRE)
        return True
    except Exception as error:
        _salida._registrar_error("tarea", error)
        print("BLE DEBUG NO INICIADO:", _salida.diagnostico())
        return False


def publicar(texto):
    _salida.publicar(texto)


def alternar_actualizacion():
    return _salida.alternar_actualizacion()


def actualizacion_activa():
    return _salida.actualizacion_activa()


def diagnostico():
    return _salida.diagnostico()
