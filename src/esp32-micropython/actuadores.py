import uasyncio  # type: ignore

import config
import hardware
import percepcion
import utilidades


class ControladorRPM:
    PWM_MAX = 1023

    def __init__(self, ki, tolerancia_rpm, rpm_parado, pwm_freno):
        self.ki = float(ki)
        self.tolerancia_rpm = float(tolerancia_rpm)
        self.exceso_freno_rpm = float(config.RPM_EXCESO_PARA_FRENAR)
        self.rpm_parado = float(rpm_parado)
        self.pwm_freno = int(utilidades.limitar(pwm_freno, 0, self.PWM_MAX))
        self.reiniciar()

    def _reiniciar_pi(self):
        self._pwm_actual = 0.0
        self._ultimo_control_ms = None
        self._direccion_pi = 0

    def reiniciar(self):
        self._reiniciar_pi()
        self._fase = "detenido"
        self._consigna_freno = None
        self._signo_freno = 0
        self._rpm_fin_freno = 0.0
        self._seq_entrada_neutral = None

    @staticmethod
    def _signo(valor):
        return 1 if valor > 0 else -1

    def _datos_freno(self, rpm_objetivo, direccion, rpm_medida):
        velocidad = abs(rpm_medida)

        if velocidad <= self.rpm_parado:
            return False, 0.0
        
        direccion_movimiento = self._signo(rpm_medida)
        if rpm_objetivo <= 0 or direccion != direccion_movimiento:
            return True, 0.0
        
        return (velocidad > rpm_objetivo + self.exceso_freno_rpm, rpm_objetivo)

    def _freno_terminado(self, rpm_medida):
        if abs(rpm_medida) <= self.rpm_parado:
            return True
        if self._signo_freno * rpm_medida <= 0:
            return True
        return (self._rpm_fin_freno > 0 and abs(rpm_medida) <= self._rpm_fin_freno + self.tolerancia_rpm)

    def _paso_pwm(self, error, dt_ms):
        return self.ki * error * dt_ms / 1000.0

    def _calcular_pi(self, rpm_objetivo, rpm_medida, ahora_ms):

        velocidad = abs(rpm_medida)
        error = rpm_objetivo - velocidad

        if self._ultimo_control_ms is None:
            dt_ms = config.PERIODO_ACTUADOR_MS
        else:
            dt_ms = utilidades.diferencia_ms(ahora_ms, self._ultimo_control_ms)

        if 0 < dt_ms <= config.EDAD_MAX_ENCODER_MS:
            self._pwm_actual += self._paso_pwm(error, dt_ms)
        self._ultimo_control_ms = ahora_ms

        self._pwm_actual = utilidades.limitar(
            self._pwm_actual,
            0,
            self.PWM_MAX,
        )
        return int(self._pwm_actual), self._pwm_actual >= self.PWM_MAX

    def actualizar(self, rpm_objetivo, direccion, frenar, rpm_medida, encoder_seq, capturado_ms, ahora_ms):
        if (not utilidades.numero_finito(rpm_objetivo) or rpm_objetivo < 0 or not utilidades.numero_finito(rpm_medida) or not isinstance(encoder_seq, int) or encoder_seq <= 0 or not utilidades.numero_finito(capturado_ms)):
            raise ValueError("orden RPM o muestra de encoder invalida")
        direccion = int(direccion)
        if rpm_objetivo > 0 and direccion not in (-1, 1):
            raise ValueError("direccion invalida para una orden RPM")

        rpm_objetivo = float(rpm_objetivo)
        frenar = bool(frenar)

        firma = (rpm_objetivo, direccion, frenar)

        if self._fase == "neutral_cambio_sentido":
            if encoder_seq == self._seq_entrada_neutral:
                return 0, 0, self._fase, False
            self._seq_entrada_neutral = None
            self._fase = "detenido"

        if (self._fase in ("neutral_antes_freno", "frenando", "esperando_parada") and firma != self._consigna_freno
        ):
            self._reiniciar_pi()
            self._fase = "neutral_despues_freno"
            return 0, 0, self._fase, False

        if self._fase == "neutral_despues_freno":
            self._fase = "detenido"
            self._consigna_freno = None

        if self._fase == "neutral_antes_freno":
            if encoder_seq == self._seq_entrada_neutral:
                return 0, 0, self._fase, False
            self._seq_entrada_neutral = None
            necesita_freno, rpm_fin = self._datos_freno(
                rpm_objetivo,
                direccion,
                rpm_medida,
            )
            if not necesita_freno:
                self._fase = "neutral_despues_freno"
                return 0, 0, self._fase, False
            self._signo_freno = self._signo(rpm_medida)
            self._rpm_fin_freno = rpm_fin
            self._fase = "frenando"
            return self.pwm_freno, -self._signo_freno, self._fase, False

        if self._fase == "frenando":
            if self._freno_terminado(rpm_medida):
                self._fase = "neutral_despues_freno"
                return 0, 0, self._fase, False
            return self.pwm_freno, -self._signo_freno, self._fase, False

        if self._fase == "esperando_parada":
            if self._freno_terminado(rpm_medida):
                self._fase = "neutral_despues_freno"
            return 0, 0, self._fase, False

        if (
            rpm_objetivo > 0
            and self._direccion_pi not in (0, direccion)
        ):
            self._reiniciar_pi()
            self._fase = "neutral_cambio_sentido"
            self._seq_entrada_neutral = encoder_seq
            return 0, 0, self._fase, False

        necesita_freno, rpm_fin = self._datos_freno(
            rpm_objetivo,
            direccion,
            rpm_medida,
        )
        cambio_sentido = (
            abs(rpm_medida) > self.rpm_parado
            and rpm_objetivo > 0
            and direccion != self._signo(rpm_medida)
        )
        if necesita_freno:
            self._reiniciar_pi()
            self._consigna_freno = firma
            self._signo_freno = self._signo(rpm_medida)
            self._rpm_fin_freno = rpm_fin
            
            if frenar or rpm_fin > 0:
                self._fase = "neutral_antes_freno"
                self._seq_entrada_neutral = encoder_seq
            else:
                self._fase = "esperando_parada"
            return 0, 0, self._fase, False

        if rpm_objetivo == 0:
            self.reiniciar()
            return 0, 0, self._fase, False

        if direccion != self._direccion_pi:
            self._reiniciar_pi()
            self._direccion_pi = direccion
        pwm, saturado = self._calcular_pi(
            rpm_objetivo,
            rpm_medida,
            ahora_ms,
        )
        self._fase = "marcha"
        return pwm, direccion, self._fase, saturado


def _rpm_encoder_fresca(encoder, ahora_ms):
    if not percepcion.muestra_fresca(
        encoder,
        ahora_ms,
        config.EDAD_MAX_ENCODER_MS,
    ):
        return None
    rpm = encoder.get("rpm")
    return rpm if utilidades.numero_finito(rpm) else None


def _aplicar_motor(pwm, direccion):
    if pwm > 0 and direccion in (-1, 1):
        hardware.motor.mover_directo(pwm, direccion)
        return direccion
    else:
        hardware.motor.detener()
        return 0


def _publicar_motor(
    aplicado,
    rpm_objetivo,
    rpm_medida,
    pwm,
    direccion,
    fase,
    saturado,
    ahora_ms,
    orden_seq,
    error=None,
):
    aplicado["rpm_objetivo"] = float(rpm_objetivo)
    aplicado["rpm_medida"] = rpm_medida
    aplicado["pwm_aplicado"] = int(pwm)
    aplicado["direccion"] = int(direccion)
    aplicado["fase"] = fase
    aplicado["saturado"] = bool(saturado)
    aplicado["aplicada_ms"] = ahora_ms
    aplicado["orden_seq"] = orden_seq
    aplicado["ok"] = error is None
    aplicado["error"] = None if error is None else str(error)


async def ejecutar_motor(sistema):
    orden = sistema["ordenes"]["motor"]
    aplicado = sistema["actuadores"]["motor"]
    encoder = sistema["sensores"]["encoder"]
    controlador = ControladorRPM(
        config.KI_RPM,
        config.RPM_TOLERANCIA,
        config.RPM_PARADO,
        config.PWM_FRENO,
    )
    while True:
        ahora = utilidades.ahora_ms()
        rpm_medida = _rpm_encoder_fresca(encoder, ahora)
        try:
            if not utilidades.orden_vigente(orden, ahora):
                controlador.reiniciar()
                _aplicar_motor(0, 0)
                _publicar_motor(
                    aplicado,
                    0.0,
                    rpm_medida,
                    0,
                    0,
                    "detenido",
                    False,
                    ahora,
                    orden.get("seq", 0),
                )
            else:
                rpm_objetivo = orden["rpm_objetivo"]
                direccion = orden["direccion"]
                frenar = bool(orden.get("frenar", False))
                if rpm_objetivo == 0 and not frenar:
                    controlador.reiniciar()
                    pwm, direccion_aplicada, fase, saturado = (
                        0,
                        0,
                        "detenido",
                        False,
                    )
                else:
                    if rpm_medida is None:
                        raise ValueError("encoder viejo o invalido")
                    pwm, direccion_aplicada, fase, saturado = (
                        controlador.actualizar(
                            rpm_objetivo,
                            direccion,
                            frenar,
                            rpm_medida,
                            encoder["seq"],
                            encoder["capturado_ms"],
                            ahora,
                        )
                    )
                direccion_aplicada = _aplicar_motor(
                    pwm,
                    direccion_aplicada,
                )
                _publicar_motor(
                    aplicado,
                    rpm_objetivo,
                    rpm_medida,
                    pwm,
                    direccion_aplicada,
                    fase,
                    saturado,
                    ahora,
                    orden.get("seq", 0),
                )
        except Exception as exc:
            controlador.reiniciar()
            try:
                hardware.motor.detener()
            except Exception:
                pass
            _publicar_motor(
                aplicado,
                0.0,
                None,
                0,
                0,
                "detenido",
                False,
                ahora,
                orden.get("seq", 0),
                exc,
            )
        await uasyncio.sleep_ms(config.PERIODO_ACTUADOR_MS)


async def ejecutar_servo(sistema):
    orden = sistema["ordenes"]["servo"]
    aplicado = sistema["actuadores"]["servo"]
    while True:
        ahora = utilidades.ahora_ms()
        try:
            comando = (
                orden["comando"]
                if utilidades.orden_vigente(orden, ahora)
                else 0.0
            )
            motor = sistema["actuadores"]["motor"]
            retroceso = (
                motor["direccion"] == -1
                and motor.get("fase") == "marcha"
            )
            objetivo = utilidades.comando_a_angulo_servo(
                comando,
                en_retroceso=retroceso,
            )
            actual = aplicado["angulo"]
            nuevo = utilidades.avanzar_hacia(
                actual,
                objetivo,
                config.PASO_SERVO,
            )
            hardware.servo.mover(nuevo, espera=False)
            aplicado["comando"] = comando
            aplicado["angulo"] = nuevo
            aplicado["aplicada_ms"] = ahora
            aplicado["orden_seq"] = orden.get("seq", 0)
            aplicado["ok"] = True
            aplicado["error"] = None
        except Exception as exc:
            try:
                hardware.servo.mover(config.SERVO_CENTRO, espera=False)
            except Exception:
                pass
            aplicado["comando"] = 0.0
            aplicado["angulo"] = config.SERVO_CENTRO
            aplicado["aplicada_ms"] = ahora
            aplicado["ok"] = False
            aplicado["error"] = str(exc)
        await uasyncio.sleep_ms(config.PERIODO_ACTUADOR_MS)


def detener_seguro(sistema=None):
    """Cierre sin await para excepciones del event loop o KeyboardInterrupt."""
    try:
        hardware.motor.detener()
    except Exception:
        pass
    try:
        hardware.servo.mover(config.SERVO_CENTRO, espera=False)
    except Exception:
        pass
    if sistema is not None:
        motor = sistema["actuadores"]["motor"]
        motor["rpm_objetivo"] = 0.0
        motor["rpm_medida"] = None
        motor["pwm_aplicado"] = 0
        motor["direccion"] = 0
        motor["fase"] = "detenido"
        motor["saturado"] = False
        sistema["actuadores"]["servo"]["comando"] = 0.0
        sistema["actuadores"]["servo"]["angulo"] = config.SERVO_CENTRO
