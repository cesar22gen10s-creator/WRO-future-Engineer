class LectorPS4UART:
    # Mascaras de flechas.
    DPAD_ARRIBA = 1
    DPAD_ABAJO = 2
    DPAD_DERECHA = 4
    DPAD_IZQUIERDA = 8

    # Mascaras de botones.
    BTN_X = 1
    BTN_CIRCULO = 2
    BTN_CUADRADO = 4
    BTN_TRIANGULO = 8
    BTN_L1 = 16
    BTN_R1 = 32
    BTN_L2 = 64
    BTN_R2 = 128

    def __init__(self, uart):
        self.uart = uart
        self.buffer = b""

    def _parsear(self, linea_bytes):
        try:
            partes = linea_bytes.decode("utf-8").strip().split(",")

            if len(partes) != 8 or partes[0] != "P":
                return None

            return {
                "conectado": bool(int(partes[1])),
                "stick": int(partes[2]),
                "flechas": int(partes[3]),
                "botones": int(partes[4]),
                "auxiliar": int(partes[5]),
                "gatillo_izq": int(partes[6]),
                "gatillo_der": int(partes[7]),
            }
        except Exception:
            return None

    def leer(self):
        """Lee la UART y devuelve el paquete completo mas reciente o None."""
        while self.uart.any():
            datos = self.uart.read()
            if not datos:
                break
            self.buffer += datos

        ultimo = None

        while b"\n" in self.buffer:
            linea, self.buffer = self.buffer.split(b"\n", 1)
            estado = self._parsear(linea)
            if estado is not None:
                ultimo = estado

        return ultimo
