import ble_debug
import config
import estado as contratos
import percepcion
import utilidades
from ps4_uart import LectorPS4UART


MODO_AUTOMATICO = "automatico"
MODO_MANUAL = "manual"

DETENIDO = "detenido"
CRUCERO = "crucero"
APROXIMACION = "aproximacion"
PREPARACION_GIRO = "preparacion_giro"
RETROCESO_GIRO = "retroceso_giro"
GIRO = "giro"
SALIDA = "salida"
FALLO = "fallo"

SENTIDO_DERECHA = "derecha"
SENTIDO_IZQUIERDA = "izquierda"

_UMBRAL_GATILLO_MANUAL = 100
_VALOR_MAX_GATILLO = 1023


class NavegadorOpen:
    def __init__(self):
        self._boton_start_anterior = False
        self._boton_cuadrado_anterior = False
        self._boton_x_anterior = False
        self._manual_neutro_confirmado = False
        self._manual_seq_neutro_desde = 0
        self._manual_cortes_uart = 0

    def _desarmar_manual(self, sistema):
        self._manual_neutro_confirmado = False
        self._manual_seq_neutro_desde = sistema["entradas"]["ps4"].get(
            "seq",
            0,
        )
        self._manual_cortes_uart = sistema["entradas"]["ps4"].get(
            "cortes_uart",
            0,
        )

    def activar(self, sistema, ahora_ms):
        nav = sistema["navegacion"]
        self._desarmar_manual(sistema)
        nav["activo"] = True
        nav["fallo"] = None
        nav["sentido_pista"] = None
        nav["sentido_giro"] = None
        nav["sentido_giro_pendiente"] = None
        nav["candidato_tof_giro"] = None
        nav["sentido_giro_fluido_confirmado"] = None
        nav["ultimo_frame_sonar_planificacion"] = None
        nav["esquinas"] = 0
        nav["vueltas"] = 0
        nav["candidato_esquina"] = None
        nav["confirmaciones_esquina"] = 0
        nav["ultimo_frame_sonar_esquina"] = None
        nav["confirmaciones_giro"] = 0
        nav["ultimo_seq_imu_giro"] = 0
        nav["confirmaciones_pasillo"] = 0
        nav["ultimo_frame_sonar_pasillo"] = None
        nav["pasillo_sonar_previo"] = False
        nav["ultimo_pasillo_sonar_ms"] = None
        nav["ultimo_frame_sonar_previo"] = None
        nav["frame_frontal_preparacion"] = None
        nav["distancia_inicio_retroceso_cm"] = None
        nav["activado_ms"] = ahora_ms
        nav["ultimo_movimiento_ms"] = ahora_ms
        nav["heading_ref"] = None
        nav["heading_error"] = None
        self._cambiar_maniobra(nav, DETENIDO, ahora_ms, "activado")

    def desactivar(self, sistema, ahora_ms, motivo="detenido_por_usuario"):
        nav = sistema["navegacion"]
        self._desarmar_manual(sistema)
        nav["activo"] = False
        nav["heading_ref"] = None
        nav["heading_error"] = None
        nav["sentido_giro"] = None
        nav["sentido_giro_pendiente"] = None
        self._cambiar_maniobra(nav, DETENIDO, ahora_ms, motivo)
        self._emitir_parada(sistema, ahora_ms, motivo)

    def forzar_fallo(self, sistema, ahora_ms, motivo):
        self._fallar(sistema, ahora_ms, motivo)

    def actualizar(self, sistema, ahora_ms):
        nav = sistema["navegacion"]
        self._procesar_entradas(sistema, ahora_ms)

        if nav["maniobra"] == FALLO:
            motivo_fallo = nav["fallo"] or "fallo"
            self._emitir_fallo_seguro(
                sistema,
                ahora_ms,
                motivo_fallo,
            )
            return

        if nav["modo"] == MODO_MANUAL:
            self._actualizar_manual(sistema, ahora_ms)
            return
        
        if not nav["activo"]:
            self._cambiar_maniobra(nav, DETENIDO, ahora_ms, "automatico_inactivo")
            self._emitir_parada(sistema, ahora_ms, "automatico_inactivo")
            return

        sensores = sistema["sensores"]
        imu = sensores["imu"]
        if not percepcion.muestra_fresca(imu, ahora_ms,config.EDAD_MAX_IMU_MS) or not utilidades.numero_finito(imu.get("heading")):
            if nav["maniobra"] == DETENIDO:
                self._emitir_parada(sistema, ahora_ms, "esperando_imu")
                return
            self._fallar(sistema, ahora_ms, "imu_vieja_o_invalida")
            
            return

        heading = utilidades.normalizar_angulo(imu["heading"])

        frente = percepcion.observar_frente(sensores["sonar"]["frontal"], sensores["tof"]["frontal"], ahora_ms)
        laterales = percepcion.observar_sonares_laterales(
            sensores["sonar"]["izquierdo"],
            sensores["sonar"]["derecho"],
            ahora_ms,
        )
        tofs = percepcion.observar_tofs_laterales(
            sensores["tof"]["izquierdo"],
            sensores["tof"]["derecho"],
            ahora_ms,
        )
        nav["asimetria_tof"] = tofs["asimetria"]
        if nav["maniobra"] in (DETENIDO, CRUCERO, APROXIMACION):
            self._actualizar_candidato_tof_giro(nav, laterales, tofs)
        if (
            nav["maniobra"] in (DETENIDO, CRUCERO, APROXIMACION)
            and laterales["pasillo_normal"]
            and laterales["frame"] != nav["ultimo_frame_sonar_previo"]
        ):
            nav["pasillo_sonar_previo"] = True
            nav["ultimo_pasillo_sonar_ms"] = ahora_ms
            nav["ultimo_frame_sonar_previo"] = laterales["frame"]

        if nav["maniobra"] == DETENIDO:
            if not frente["disponible"]:
                self._emitir_parada(
                    sistema,
                    ahora_ms,
                    "esperando_sensor_frontal",
                )
                return
            nav["heading_ref"] = heading
            nav["activado_ms"] = ahora_ms
            nav["ultimo_movimiento_ms"] = ahora_ms
            self._cambiar_maniobra(
                nav,
                CRUCERO,
                ahora_ms,
                "sensores_listos",
            )

        if nav["heading_ref"] is None:
            nav["heading_ref"] = heading
        try:
            nav["heading_error"] = utilidades.error_angular(
                nav["heading_ref"],
                heading,
            )
        except ValueError:
            self._fallar(sistema, ahora_ms, "heading_no_finito")
            return

        # Algunas transiciones pueden encadenarse de forma segura en un mismo
        # paso (por ejemplo una distancia frontal que ya es critica).
        for _ in range(3):
            anterior = nav["maniobra"]
            self._actualizar_estado(
                sistema,
                ahora_ms,
                frente,
                laterales,
                tofs,
                imu,
            )
            if nav["maniobra"] == anterior or nav["maniobra"] in (GIRO, FALLO):
                break
            if nav["maniobra"] == SALIDA:
                # Validar SALIDA en el mismo tick en que termina GIRO.
                continue

        if nav["maniobra"] == FALLO:
            return

        orden = self._orden_para_estado(
            nav,
            frente,
            laterales,
            tofs,
        )
        (
            rpm_objetivo,
            direccion,
            comando,
            motivo,
            frenar,
        ) = self._aplicar_proteccion_tof(
            orden,
            tofs,
            nav["maniobra"] not in (
                PREPARACION_GIRO,
                RETROCESO_GIRO,
                GIRO,
            ),
        )
        contratos.emitir_orden_motor(
            sistema["ordenes"]["motor"],
            rpm_objetivo,
            direccion,
            ahora_ms,
            motivo,
            frenar=frenar,
        )
        contratos.emitir_orden_servo(
            sistema["ordenes"]["servo"],
            comando,
            ahora_ms,
            motivo,
        )

    def _procesar_entradas(self, sistema, ahora_ms):
        nav = sistema["navegacion"]
        boton = sistema["entradas"]["boton_start"]
        presionado = bool(boton.get("valor")) if boton.get("valido") else False
        if presionado and not self._boton_start_anterior:
            if nav["activo"]:
                self.desactivar(sistema, ahora_ms)
            else:
                self.activar(sistema, ahora_ms)
        self._boton_start_anterior = presionado

        ps4 = sistema["entradas"]["ps4"]
        paquete = self._paquete_ps4_fresco(ps4, ahora_ms)
        cuadrado = False
        boton_x = False
        if isinstance(paquete, dict) and paquete.get("conectado"):
            cuadrado = self._boton_ps4_activo(
                paquete,
                LectorPS4UART.BTN_CUADRADO,
            )
            boton_x = self._boton_ps4_activo(
                paquete,
                LectorPS4UART.BTN_X,
            )
        if cuadrado and not self._boton_cuadrado_anterior:
            nav["modo"] = (MODO_MANUAL if nav["modo"] == MODO_AUTOMATICO else MODO_AUTOMATICO)
            nav["activo"] = False
            nav["heading_ref"] = None
            self._desarmar_manual(sistema)
            self._cambiar_maniobra(nav, DETENIDO, ahora_ms,"cambio_modo_" + nav["modo"])
        self._boton_cuadrado_anterior = cuadrado
        if boton_x and not self._boton_x_anterior:
            activa = ble_debug.alternar_actualizacion()
        self._boton_x_anterior = boton_x

    def _actualizar_manual(self, sistema, ahora_ms):
        nav = sistema["navegacion"]
        ps4 = sistema["entradas"]["ps4"]

        if not nav["activo"]:
            self._desarmar_manual(sistema)
            self._emitir_parada(sistema, ahora_ms, "manual_inactivo")
            return

        if ps4.get("cortes_uart", 0) != self._manual_cortes_uart:
            self._desarmar_manual(sistema)
            self._emitir_parada(sistema, ahora_ms, "manual_reconexion_uart")
            return

        paquete = self._paquete_ps4_fresco(ps4, ahora_ms)
        if not isinstance(paquete, dict):
            self._desarmar_manual(sistema)
            self._emitir_parada(sistema, ahora_ms, "manual_sin_trama_uart")
            return

        if not paquete.get("conectado"):
            self._desarmar_manual(sistema)
            self._emitir_parada(sistema, ahora_ms, "ps4_desconectado")
            return

        if not self._manual_neutro_confirmado:
            if (
                ps4.get("seq", 0) > self._manual_seq_neutro_desde
                and self._entrada_manual_neutra(paquete)
            ):
                self._manual_neutro_confirmado = True
                nav["ultimo_movimiento_ms"] = ahora_ms
            self._emitir_parada(sistema, ahora_ms, "manual_esperando_neutro")
            return

        l1 = self._boton_ps4_activo(paquete, LectorPS4UART.BTN_L1)
        r1 = self._boton_ps4_activo(paquete, LectorPS4UART.BTN_R1)

        if r1 and l1:
            rpm_objetivo = config.RPM_APROXIMACION
            direccion = 1
            frenar = True
            motivo = "manual_r1_l1_aproximacion"
        elif r1:
            rpm_objetivo = config.RPM_AVANCE
            direccion = 1
            frenar = False
            motivo = "manual_r1_avance"
        elif l1:
            rpm_objetivo = 0.0
            direccion = 1
            frenar = True
            motivo = "manual_l1_freno_critico"
        else:
            rpm_objetivo, direccion = self._orden_manual_gatillos(paquete)
            frenar = False
            motivo = "manual_gatillos" if direccion else "manual_neutro"

        comando = utilidades.comando_stick(paquete.get("stick"))

        contratos.emitir_orden_motor(
            sistema["ordenes"]["motor"],
            rpm_objetivo,
            direccion,
            ahora_ms,
            motivo,
            frenar=frenar,
        )
        contratos.emitir_orden_servo(
            sistema["ordenes"]["servo"],
            comando,
            ahora_ms,
            motivo,
        )

    @staticmethod
    def _paquete_ps4_fresco(ps4, ahora_ms):
        if not percepcion.muestra_fresca(
            ps4,
            ahora_ms,
            config.TIMEOUT_SIN_UART_PS4_MS,
        ):
            return None
        return ps4.get("valor")

    @staticmethod
    def _boton_ps4_activo(paquete, mascara):
        try:
            return bool(int(paquete.get("botones", 0)) & mascara)
        except (AttributeError, TypeError, ValueError):
            return False

    @classmethod
    def _entrada_manual_neutra(cls, paquete):
        hombros = (
            cls._boton_ps4_activo(paquete, LectorPS4UART.BTN_L1)
            or cls._boton_ps4_activo(paquete, LectorPS4UART.BTN_R1)
        )
        return (
            not hombros
            and cls._valor_gatillo(paquete.get("gatillo_izq"))
            <= _UMBRAL_GATILLO_MANUAL
            and cls._valor_gatillo(paquete.get("gatillo_der"))
            <= _UMBRAL_GATILLO_MANUAL
        )

    @staticmethod
    def _valor_gatillo(valor):
        if not utilidades.numero_finito(valor):
            return 0
        return int(utilidades.limitar(valor, 0, _VALOR_MAX_GATILLO))

    @classmethod
    def _rpm_desde_gatillo(cls, valor):
        valor = cls._valor_gatillo(valor)
        if valor <= _UMBRAL_GATILLO_MANUAL:
            return 0.0
        return (
            float(valor)
            * config.RPM_MANUAL_MAX
            / _VALOR_MAX_GATILLO
        )

    @classmethod
    def _orden_manual_gatillos(cls, paquete):
        gatillo_izq = cls._valor_gatillo(paquete.get("gatillo_izq"))
        gatillo_der = cls._valor_gatillo(paquete.get("gatillo_der"))

        if (
            gatillo_der > gatillo_izq
            and gatillo_der > _UMBRAL_GATILLO_MANUAL
        ):
            return cls._rpm_desde_gatillo(gatillo_der), 1
        if (
            gatillo_izq > gatillo_der
            and gatillo_izq > _UMBRAL_GATILLO_MANUAL
        ):
            return cls._rpm_desde_gatillo(gatillo_izq), -1
        return 0.0, 0

    def _actualizar_estado(
        self,
        sistema,
        ahora_ms,
        frente,
        laterales,
        tofs,
        imu,
    ):
        nav = sistema["navegacion"]
        maniobra = nav["maniobra"]

        if maniobra != GIRO and not frente["disponible"]:
            self._fallar(sistema, ahora_ms, "frontal_viejo_o_invalido")
            return

        if maniobra == CRUCERO:
            if frente["aproximacion"] or not frente["libre"]:
                motivo = (
                    "frente_en_aproximacion"
                    if frente["aproximacion"]
                    else "frente_no_libre"
                )
                self._cambiar_maniobra(
                    nav,
                    APROXIMACION,
                    ahora_ms,
                    motivo,
                )
            return

        if maniobra == APROXIMACION:
            if frente["critico"]:
                self._descartar_anticipacion_tof(nav)
                if not self._vehiculo_detenido(sistema, ahora_ms):
                    self._reiniciar_confirmacion_sonar(nav)
                    return
                candidato = self._confirmar_giro_detenido(nav, laterales)
                if candidato is not None:
                    nav["sentido_pista"] = candidato
                    self._preparar_giro(nav, ahora_ms, candidato)
                return

            candidato = self._confirmar_giro_fluido(nav, laterales)
            if (
                candidato is not None
                and frente["ventana_giro_fluido"]
                and self._heading_centrado_para_giro(nav)
            ):
                nav["sentido_pista"] = candidato
                self._iniciar_giro(
                    nav,
                    ahora_ms,
                    candidato,
                    imu["heading"],
                )
                return

            if frente["salir_aproximacion"]:
                self._cambiar_maniobra(
                    nav,
                    CRUCERO,
                    ahora_ms,
                    "frente_liberado_con_histeresis",
                )
            return

        if maniobra == PREPARACION_GIRO:
            if (
                utilidades.diferencia_ms(ahora_ms, nav["estado_desde_ms"])
                < config.PAUSA_PREPARACION_GIRO_MS
            ):
                return
            if nav["frame_frontal_preparacion"] is None:
                # La linea base se toma despues de la pausa para que la
                # decision use una captura hecha con el vehiculo detenido.
                nav["frame_frontal_preparacion"] = frente["frame"]
                return
            if not self._frame_frontal_actualizado(
                frente["frame"],
                nav["frame_frontal_preparacion"],
            ):
                return
            sentido = nav["sentido_giro_pendiente"]
            if sentido not in (SENTIDO_DERECHA, SENTIDO_IZQUIERDA):
                self._fallar(sistema, ahora_ms, "giro_pendiente_invalido")
                return
            if frente["espacio_giro"]:
                self._iniciar_giro(nav, ahora_ms, sentido, imu["heading"])
            else:
                self._iniciar_retroceso_giro(sistema, ahora_ms)
            return

        if maniobra == RETROCESO_GIRO:
            distancia_retroceso = self._distancia_retroceso(
                sistema,
                ahora_ms,
            )
            if distancia_retroceso is None:
                self._fallar(
                    sistema,
                    ahora_ms,
                    "encoder_invalido_durante_retroceso",
                )
                return
            if frente["espacio_giro"]:
                if (
                    nav["sentido_giro"] in (
                        SENTIDO_DERECHA,
                        SENTIDO_IZQUIERDA,
                    )
                    and utilidades.numero_finito(nav.get("heading_ref"))
                ):
                    self._cambiar_maniobra(
                        nav,
                        GIRO,
                        ahora_ms,
                        "espacio_frontal_recuperado_giro",
                    )
                else:
                    self._entrar_preparacion_giro(
                        nav,
                        ahora_ms,
                        "espacio_frontal_recuperado",
                    )
            return

        if maniobra == GIRO:
            if frente["critico"]:
                if self._vehiculo_detenido(sistema, ahora_ms):
                    self._iniciar_retroceso_giro(sistema, ahora_ms)
                return
            self._confirmar_fin_giro(sistema, ahora_ms, imu)
            return

        if maniobra == SALIDA:
            if frente["critico"]:
                return
            if (
                utilidades.diferencia_ms(
                    ahora_ms,
                    nav["estado_desde_ms"],
                )
                < config.MIN_SALIDA_MS
                or not frente["libre"]
            ):
                nav["confirmaciones_pasillo"] = 0
                return
            self._confirmar_pasillo(nav, ahora_ms, laterales)

    @staticmethod
    def _reiniciar_confirmacion_sonar(nav):
        nav["candidato_esquina"] = None
        nav["confirmaciones_esquina"] = 0
        nav["ultimo_frame_sonar_esquina"] = None

    @staticmethod
    def _descartar_anticipacion_tof(nav):
        nav["candidato_tof_giro"] = None
        nav["sentido_giro_fluido_confirmado"] = None
        nav["ultimo_frame_sonar_planificacion"] = None

    @staticmethod
    def _frame_lateral_actualizado(frame, anterior):
        return bool(
            frame is not None
            and anterior is not None
            and frame[0] != anterior[0]
            and frame[1] != anterior[1]
        )

    @staticmethod
    def _actualizar_candidato_tof_giro(nav, laterales, tofs):
        """Almacena una pista ToF aunque el frente aun este lejano."""
        if nav["sentido_giro_fluido_confirmado"] in (
            SENTIDO_DERECHA,
            SENTIDO_IZQUIERDA,
        ):
            return

        candidato_tof = tofs.get("pista", tofs.get("candidato"))
        if candidato_tof not in (SENTIDO_DERECHA, SENTIDO_IZQUIERDA):
            return
        if nav["candidato_tof_giro"] == candidato_tof:
            return

        nav["candidato_tof_giro"] = candidato_tof
        nav["ultimo_frame_sonar_planificacion"] = laterales["frame"]

    def _confirmar_giro_fluido(self, nav, laterales):
        """Usa ToF como pista y decide el sentido final con sonar."""
        confirmado = nav["sentido_giro_fluido_confirmado"]
        if confirmado in (SENTIDO_DERECHA, SENTIDO_IZQUIERDA):
            return confirmado

        candidato_planificado = nav["candidato_tof_giro"]
        if candidato_planificado not in (
            SENTIDO_DERECHA,
            SENTIDO_IZQUIERDA,
        ):
            return None

        frame = laterales["frame"]
        anterior = nav["ultimo_frame_sonar_planificacion"]
        if anterior is None:
            nav["ultimo_frame_sonar_planificacion"] = frame
            return None
        if not self._frame_lateral_actualizado(frame, anterior):
            return None
        nav["ultimo_frame_sonar_planificacion"] = frame

        candidato_sonar = laterales["candidato"]
        if candidato_sonar is None:
            return None

        nav["sentido_giro_fluido_confirmado"] = candidato_sonar
        return candidato_sonar

    def _confirmar_giro_detenido(self, nav, laterales):
        """Cuenta solo pares sonar adquiridos despues de quedar detenido."""
        frame = laterales["frame"]
        ultimo = nav["ultimo_frame_sonar_esquina"]
        if frame is None:
            nav["candidato_esquina"] = None
            nav["confirmaciones_esquina"] = 0
            return None
        if ultimo is None:
            nav["ultimo_frame_sonar_esquina"] = frame
            return None
        if not self._frame_lateral_actualizado(frame, ultimo):
            return None
        nav["ultimo_frame_sonar_esquina"] = frame

        candidato = laterales["candidato"]
        if candidato is None:
            nav["candidato_esquina"] = None
            nav["confirmaciones_esquina"] = 0
            return None
        if candidato == nav["candidato_esquina"]:
            nav["confirmaciones_esquina"] += 1
        else:
            nav["candidato_esquina"] = candidato
            nav["confirmaciones_esquina"] = 1

        if nav["confirmaciones_esquina"] < config.MUESTRAS_CONFIRMAR_ESQUINA:
            return None
        return candidato

    @staticmethod
    def _vehiculo_detenido(sistema, ahora_ms):
        encoder = sistema["sensores"]["encoder"]
        rpm = encoder.get("rpm")
        return bool(
            percepcion.muestra_fresca(
                encoder,
                ahora_ms,
                config.EDAD_MAX_ENCODER_MS,
            )
            and utilidades.numero_finito(rpm)
            and abs(rpm) <= config.RPM_PARADO
        )

    @staticmethod
    def _heading_centrado_para_giro(nav):
        error = nav.get("heading_error")
        return bool(
            utilidades.numero_finito(error)
            and abs(error) <= config.ERROR_GIRO_PERMITIDO
        )

    def _preparar_giro(self, nav, ahora_ms, sentido):
        self._descartar_anticipacion_tof(nav)
        nav["sentido_giro_pendiente"] = sentido
        self._entrar_preparacion_giro(
            nav,
            ahora_ms,
            "esquina_sonar_" + sentido + "_confirmada",
        )

    def _entrar_preparacion_giro(self, nav, ahora_ms, motivo):
        self._cambiar_maniobra(nav, PREPARACION_GIRO, ahora_ms, motivo)
        nav["frame_frontal_preparacion"] = None

    def _iniciar_retroceso_giro(self, sistema, ahora_ms):
        nav = sistema["navegacion"]
        distancia_actual = self._distancia_encoder_fresca(
            sistema,
            ahora_ms,
        )
        if distancia_actual is None:
            self._fallar(
                sistema,
                ahora_ms,
                "encoder_no_disponible_para_retroceso",
            )
            return
        if not utilidades.numero_finito(
            nav.get("distancia_inicio_retroceso_cm")
        ):
            nav["distancia_inicio_retroceso_cm"] = distancia_actual
        self._cambiar_maniobra(
            nav,
            RETROCESO_GIRO,
            ahora_ms,
            "frente_menor_a_{}_cm".format(
                config.DISTANCIA_FRONTAL_MIN_GIRO_CM
            ),
        )

    @staticmethod
    def _distancia_encoder_fresca(sistema, ahora_ms):
        encoder = sistema["sensores"]["encoder"]
        if not percepcion.muestra_fresca(
            encoder,
            ahora_ms,
            config.EDAD_MAX_ENCODER_MS,
        ):
            return None
        distancia = encoder.get("distancia_acumulada_cm")
        return distancia if utilidades.numero_finito(distancia) else None

    def _distancia_retroceso(self, sistema, ahora_ms):
        nav = sistema["navegacion"]
        inicio = nav.get("distancia_inicio_retroceso_cm")
        actual = self._distancia_encoder_fresca(sistema, ahora_ms)
        if not utilidades.numero_finito(inicio) or actual is None:
            return None
        return abs(actual - inicio)

    def _iniciar_giro(self, nav, ahora_ms, sentido, heading_actual):
        signo = 1 if sentido == SENTIDO_DERECHA else -1
        delta = 90.0 * config.SIGNO_HEADING_DERECHA * signo
        heading_pasillo = nav.get("heading_ref")
        if not utilidades.numero_finito(heading_pasillo):
            heading_pasillo = heading_actual
        nav["heading_ref"] = utilidades.normalizar_angulo(
            heading_pasillo + delta
        )
        nav["heading_error"] = utilidades.error_angular(
            nav["heading_ref"],
            heading_actual,
        )
        nav["sentido_giro"] = sentido
        nav["sentido_giro_pendiente"] = None
        self._descartar_anticipacion_tof(nav)
        nav["confirmaciones_giro"] = 0
        nav["ultimo_seq_imu_giro"] = 0
        self._cambiar_maniobra(
            nav,
            GIRO,
            ahora_ms,
            "espacio_giro_confirmado_" + sentido,
        )

    def _confirmar_fin_giro(self, sistema, ahora_ms, imu):
        nav = sistema["navegacion"]
        seq = imu.get("seq", 0)
        if seq == nav["ultimo_seq_imu_giro"]:
            return
        nav["ultimo_seq_imu_giro"] = seq
        if abs(nav["heading_error"]) <= config.ERROR_GIRO_PERMITIDO:
            nav["confirmaciones_giro"] += 1
        else:
            nav["confirmaciones_giro"] = 0
        if nav["confirmaciones_giro"] < config.MUESTRAS_CONFIRMAR_GIRO:
            return
        nav["esquinas"] += 1
        nav["vueltas"] = nav["esquinas"] // 4
        nav["sentido_giro"] = None
        self._cambiar_maniobra(
            nav,
            CRUCERO,
            ahora_ms,
            "giro_completado",
        )

    def _confirmar_pasillo(self, nav, ahora_ms, laterales):
        frame = laterales["frame"]
        ultimo = nav["ultimo_frame_sonar_pasillo"]
        if frame is None or not laterales["pasillo_normal"]:
            nav["confirmaciones_pasillo"] = 0
            return
        if ultimo is not None and not (
            frame[0] != ultimo[0] and frame[1] != ultimo[1]
        ):
            return
        nav["ultimo_frame_sonar_pasillo"] = frame
        nav["confirmaciones_pasillo"] += 1
        if nav["confirmaciones_pasillo"] >= config.MUESTRAS_CONFIRMAR_PASILLO:
            nav["pasillo_sonar_previo"] = True
            nav["ultimo_pasillo_sonar_ms"] = ahora_ms
            nav["ultimo_frame_sonar_previo"] = frame
            self._cambiar_maniobra(
                nav,
                CRUCERO,
                ahora_ms,
                "pasillo_normal_confirmado",
            )

    def _orden_para_estado(self, nav, frente, laterales, tofs):
        error = nav["heading_error"]
        maniobra = nav["maniobra"]
        if frente["critico"] and maniobra in (
            CRUCERO,
            APROXIMACION,
            PREPARACION_GIRO,
            GIRO,
            SALIDA,
        ):
            return (
                0.0,
                1,
                0.0,
                "frente_critico_" + maniobra,
                True,
            )
        if maniobra == CRUCERO:
            comando, motivo_control = self._control_longitudinal(
                error,
                config.KP_HEADING_RECTA,
                tofs,
            )
            if not frente["libre"]:
                return (
                    config.RPM_APROXIMACION,
                    1,
                    comando,
                    "crucero_no_libre_" + motivo_control,
                    True,
                )
            return (
                config.RPM_AVANCE,
                1,
                comando,
                "crucero_" + motivo_control,
                False,
            )
        if maniobra == APROXIMACION:
            comando, motivo_control = self._control_longitudinal(
                error,
                config.KP_HEADING_APROX,
                tofs,
            )
            return (
                config.RPM_APROXIMACION,
                1,
                comando,
                "aproximacion_" + motivo_control,
                True,
            )
        if maniobra == PREPARACION_GIRO:
            return 0.0, 0, 0.0, "preparacion_giro_detenida", False
        if maniobra == RETROCESO_GIRO:
            return (
                config.RPM_RETROCESO,
                -1,
                0.0,
                "retroceso_hasta_espacio_giro",
                False,
            )
        if maniobra == GIRO:
            if abs(error) <= config.ERROR_GIRO_PERMITIDO:
                return 0.0, 0, 0.0, "giro_asentando_error", False
            return (
                config.RPM_GIRO,
                1,
                utilidades.control_giro(error),
                "giro_imu_" + str(nav["sentido_giro"]),
                False,
            )
        if maniobra == SALIDA:
            comando, motivo_control = self._control_longitudinal(
                error,
                config.KP_HEADING_APROX,
                tofs,
            )
            return (
                config.RPM_SALIDA,
                1,
                comando,
                "salida_" + motivo_control,
                False,
            )
        return 0.0, 0, 0.0, "estado_sin_movimiento", False

    @staticmethod
    def _aplicar_proteccion_tof(orden, tofs, habilitada=True):
        """Da prioridad a evitar una colision lateral mientras se avanza."""
        if not habilitada:
            return orden
        rpm_objetivo, direccion, comando, motivo, frenar = orden
        if rpm_objetivo <= 0 or direccion != 1:
            return orden

        if tofs["peligro_ambos"]:
            return (
                0.0,
                1,
                0.0,
                "proteccion_tof_peligro_ambos",
                True,
            )

        if tofs["peligro_izquierdo"] or tofs["peligro_derecho"]:
            return (
                rpm_objetivo,
                direccion,
                tofs["comando_proteccion"],
                "proteccion_" + tofs["motivo_control"],
                frenar,
            )

        return orden

    @staticmethod
    def _control_longitudinal(error, kp_heading, tofs):
        heading = utilidades.control_heading(error, kp_heading)
        if (utilidades.numero_finito(error) and abs(error) >= config.ERROR_GIRO_PERMITIDO):
            return heading, "solo_heading_error_alto"
        correccion = tofs["comando_correccion"]
        comando = utilidades.combinar_controles(heading, correccion)
        return comando, "heading_" + tofs["motivo_control"]

    def _fallar(self, sistema, ahora_ms, motivo):
        nav = sistema["navegacion"]
        nav["activo"] = False
        nav["fallo"] = motivo
        self._desarmar_manual(sistema)
        self._cambiar_maniobra(nav, FALLO, ahora_ms, motivo)
        self._emitir_fallo_seguro(sistema, ahora_ms, motivo)

    def _emitir_fallo_seguro(self, sistema, ahora_ms, motivo):
        encoder = sistema["sensores"]["encoder"]
        rpm = encoder.get("rpm")
        puede_frenar = (
            percepcion.muestra_fresca(
                encoder,
                ahora_ms,
                config.EDAD_MAX_ENCODER_MS,
            )
            and utilidades.numero_finito(rpm)
            and abs(rpm) > config.RPM_PARADO
        )
        if not puede_frenar:
            self._emitir_parada(sistema, ahora_ms, motivo)
            return
        contratos.emitir_orden_motor(
            sistema["ordenes"]["motor"],
            0.0,
            1,
            ahora_ms,
            motivo,
            frenar=True,
        )
        contratos.emitir_orden_servo(
            sistema["ordenes"]["servo"],
            0.0,
            ahora_ms,
            motivo,
        )

    def _emitir_parada(self, sistema, ahora_ms, motivo):
        contratos.emitir_orden_motor(
            sistema["ordenes"]["motor"],
            0,
            0,
            ahora_ms,
            motivo,
            frenar=False,
        )
        contratos.emitir_orden_servo(
            sistema["ordenes"]["servo"],
            0.0,
            ahora_ms,
            motivo,
        )

    @staticmethod
    def _frame_frontal_actualizado(actual, referencia):
        if not isinstance(actual, (tuple, list)) or len(actual) != 2:
            return False
        if not isinstance(referencia, (tuple, list)) or len(referencia) != 2:
            referencia = (0, 0)
        hay_fuente = False
        for indice in range(2):
            secuencia = actual[indice]
            secuencia_referencia = referencia[indice]
            fuente_requerida = (
                isinstance(secuencia_referencia, int)
                and secuencia_referencia > 0
            )
            if not isinstance(secuencia, int) or secuencia <= 0:
                if fuente_requerida:
                    return False
                continue
            hay_fuente = True
            if fuente_requerida and secuencia == secuencia_referencia:
                return False
        return hay_fuente

    @staticmethod
    def _cambiar_maniobra(nav, nueva, ahora_ms, motivo):
        if nav["maniobra"] == nueva:
            nav["motivo_transicion"] = motivo
            return
        nav["maniobra"] = nueva
        nav["estado_desde_ms"] = ahora_ms
        nav["motivo_transicion"] = motivo
        if nueva == APROXIMACION:
            nav["sentido_giro_pendiente"] = None
            nav["candidato_esquina"] = None
            nav["confirmaciones_esquina"] = 0
            nav["ultimo_frame_sonar_esquina"] = None
            nav["distancia_inicio_retroceso_cm"] = None
        elif nueva == GIRO:
            nav["distancia_inicio_retroceso_cm"] = None
        elif nueva == SALIDA:
            nav["confirmaciones_pasillo"] = 0
            nav["ultimo_frame_sonar_pasillo"] = None
            nav["pasillo_sonar_previo"] = False
            nav["ultimo_pasillo_sonar_ms"] = None
            nav["ultimo_frame_sonar_previo"] = None
            nav["frame_frontal_preparacion"] = None
            nav["distancia_inicio_retroceso_cm"] = None
        elif nueva in (DETENIDO, FALLO):
            nav["sentido_giro_pendiente"] = None
            nav["candidato_tof_giro"] = None
            nav["sentido_giro_fluido_confirmado"] = None
            nav["ultimo_frame_sonar_planificacion"] = None
