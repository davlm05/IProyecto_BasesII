
import json
import unittest

from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from tests.test_seguridad_api import consultar, obtener_token
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier


API_URL = "http://localhost:8000"

PACIENTE_1 = "11111111-0040-0000-0000-000000000001"
PACIENTE_2 = "11111111-0040-0000-0000-000000000002"
PROFESIONAL = "11111111-0020-0000-0000-000000000001"
SERVICIO = "11111111-0030-0000-0000-000000000001"


def enviar_post(ruta, token, datos):
    solicitud = Request(
        API_URL + ruta,
        data=json.dumps(datos).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(solicitud, timeout=15) as respuesta:
            return respuesta.status, json.load(respuesta)
    except HTTPError as error:
        return error.code, json.load(error)


def fecha_laborable_futura():
    hora_cr = timezone(timedelta(hours=-6))
    fecha = datetime.now(hora_cr).date() + timedelta(days=14)

    while fecha.weekday() >= 5:
        fecha += timedelta(days=1)

    return fecha


class TestCitasAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token = obtener_token("santaLuciaReception")
        cls.fecha = fecha_laborable_futura()

    def setUp(self):
        self.citas_creadas = []

    def tearDown(self):
        # Liberar las reservas de prueba que sigan vigentes.
        for cita_id in self.citas_creadas:
            estado, _ = enviar_post(
                f"/appointments/{cita_id}/cancel",
                self.token,
                {"cancellationReason": "Limpieza de prueba automatizada"},
            )
            self.assertIn(estado, (200, 409))

    def consultar_espacios(self):
        parametros = urlencode({
            "professionalID": PROFESIONAL,
            "serviceID": SERVICIO,
            "targetDate": self.fecha.isoformat(),
        })

        estado, datos = consultar(
            f"/availability/professional?{parametros}",
            self.token,
        )

        self.assertEqual(estado, 200, datos)
        return datos["availableSlots"]

    def reservar(self, paciente, inicio):
        return enviar_post(
            "/appointments",
            self.token,
            {
                "patientID": paciente,
                "professionalID": PROFESIONAL,
                "serviceID": SERVICIO,
                "startAt": inicio,
            },
        )

    def test_reservar_y_cancelar_cita(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios, "No hay espacios disponibles")

        inicio = espacios[0]["startAt"]

        estado, cita = self.reservar(PACIENTE_1, inicio)

        self.assertEqual(estado, 201, cita)
        self.assertEqual(cita["appointmentStatusPK"], "reserved")
        self.assertEqual(cita["durationMinutes"], 30)

        cita_id = cita["appointmentID"]
        self.citas_creadas.append(cita_id)

        estado, cancelada = enviar_post(
            f"/appointments/{cita_id}/cancel",
            self.token,
            {"cancellationReason": "Cancelacion de prueba"},
        )

        self.assertEqual(estado, 200, cancelada)
        self.assertEqual(
            cancelada["appointmentStatusPK"],
            "cancelled",
        )

        # I7: el espacio debe quedar libre inmediatamente.
        espacios_despues = self.consultar_espacios()

        inicios_disponibles = {
            espacio["startAt"] for espacio in espacios_despues
        }

        self.assertIn(inicio, inicios_disponibles)

    def test_dos_citas_no_ocupan_el_mismo_espacio(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios, "No hay espacios disponibles")

        inicio = espacios[0]["startAt"]

        estado, primera = self.reservar(PACIENTE_1, inicio)

        self.assertEqual(estado, 201, primera)
        self.citas_creadas.append(primera["appointmentID"])

        # Otro paciente intenta reservar al mismo profesional
        # exactamente a la misma hora.
        estado, segunda = self.reservar(PACIENTE_2, inicio)

        self.assertEqual(estado, 409, segunda)
        self.assertEqual(segunda["errorCode"], "slotTaken")

    def test_no_cancelar_dos_veces(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios, "No hay espacios disponibles")

        estado, cita = self.reservar(
            PACIENTE_1,
            espacios[0]["startAt"],
        )

        self.assertEqual(estado, 201, cita)
        cita_id = cita["appointmentID"]
        self.citas_creadas.append(cita_id)

        ruta = f"/appointments/{cita_id}/cancel"
        motivo = {"cancellationReason": "Prueba de estados"}

        estado, _ = enviar_post(ruta, self.token, motivo)
        self.assertEqual(estado, 200)

        estado, respuesta = enviar_post(ruta, self.token, motivo)

        self.assertEqual(estado, 409, respuesta)
        self.assertEqual(
            respuesta["errorCode"],
            "appointmentNotReserved",
        )
        
    def test_reprogramar_cita(self):
        espacios = self.consultar_espacios()
        self.assertGreaterEqual(len(espacios), 2)

        inicio_original = espacios[0]["startAt"]
        inicio_nuevo = espacios[1]["startAt"]

        # Crear la cita original.
        estado, cita = self.reservar(
            PACIENTE_1,
            inicio_original,
        )

        self.assertEqual(estado, 201, cita)
        cita_id = cita["appointmentID"]
        self.citas_creadas.append(cita_id)

        # Reprogramar a otro espacio disponible.
        estado, resultado = enviar_post(
            f"/appointments/{cita_id}/reschedule",
            self.token,
            {"startAt": inicio_nuevo},
        )

        self.assertEqual(estado, 200, resultado)

        original = resultado["originalAppointment"]
        nueva = resultado["newAppointment"]

        self.citas_creadas.append(nueva["appointmentID"])

        # Verificar los estados y la relación.
        self.assertEqual(
            original["appointmentStatusPK"],
            "rescheduled",
        )
        self.assertEqual(
            nueva["appointmentStatusPK"],
            "reserved",
        )
        self.assertEqual(
            original["rescheduledToAppointmentID"],
            nueva["appointmentID"],
        )

        # I7: el horario anterior queda libre.
        # El nuevo horario queda ocupado.
        disponibles = {
            espacio["startAt"]
            for espacio in self.consultar_espacios()
        }

        self.assertIn(inicio_original, disponibles)
        self.assertNotIn(inicio_nuevo, disponibles)

        # RF13: una cita reprogramada no puede
        # reprogramarse nuevamente.
        estado, respuesta = enviar_post(
            f"/appointments/{cita_id}/reschedule",
            self.token,
            {"startAt": inicio_original},
        )

        self.assertEqual(estado, 409, respuesta)
        self.assertEqual(
            respuesta["errorCode"],
            "appointmentNotReserved",
        )

    def test_no_registrar_desENLACE_antes_de_la_cita(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios)

        estado, cita = self.reservar(
            PACIENTE_1,
            espacios[0]["startAt"],
        )

        self.assertEqual(estado, 201, cita)

        cita_id = cita["appointmentID"]
        self.citas_creadas.append(cita_id)

        # No se puede marcar como atendida
        # una cita que todavía no ha comenzado.
        estado, respuesta = enviar_post(
            f"/appointments/{cita_id}/outcome",
            self.token,
            {"appointmentStatusPK": "attended"},
        )

        self.assertEqual(estado, 422, respuesta)
        self.assertEqual(
            respuesta["errorCode"],
            "outcomeBeforeStart",
        )
    
    def test_concurrencia_dos_usuarios_mismo_espacio(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios, "No hay espacios disponibles")

        inicio = espacios[0]["startAt"]

        # Dos usuarios distintos de la misma clinica.
        token_recepcion = self.token
        token_admin = obtener_token("santaLuciaAdmin")

        # La barrera sincroniza los dos intentos.
        barrera = Barrier(3)

        def intentar_reserva(paciente, token):
            barrera.wait(timeout=10)

            estado, respuesta = enviar_post(
                "/appointments",
                token,
                {
                    "patientID": paciente,
                    "professionalID": PROFESIONAL,
                    "serviceID": SERVICIO,
                    "startAt": inicio,
                },
            )

            # Registrar la cita aceptada para limpiarla
            # incluso si alguna comprobacion falla.
            if estado == 201:
                self.citas_creadas.append(
                    respuesta["appointmentID"]
                )

            return estado, respuesta

        # Ejecutamos las dos solicitudes en paralelo.
        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            futuro_1 = ejecutor.submit(
                intentar_reserva,
                PACIENTE_1,
                token_recepcion,
            )

            futuro_2 = ejecutor.submit(
                intentar_reserva,
                PACIENTE_2,
                token_admin,
            )

            # Liberar ambas solicitudes al mismo tiempo.
            barrera.wait(timeout=10)

            resultados = [
                futuro_1.result(timeout=30),
                futuro_2.result(timeout=30),
            ]

        codigos = sorted(
            estado for estado, respuesta in resultados
        )

        # Exactamente una reserva exitosa y un conflicto.
        self.assertEqual(codigos, [201, 409], resultados)

        self.assertEqual(len(self.citas_creadas), 1)

        # El conflicto debe tener una explicacion valida.
        for estado, respuesta in resultados:
            if estado == 409:
                self.assertIn(
                    respuesta["errorCode"],
                    ("slotTaken", "serializationConflict"),
                )

        # Comprobar que la cita ganadora existe
        # realmente en PostgreSQL a traves de la API.
        cita_id = self.citas_creadas[0]

        estado, cita = consultar(
            f"/appointments/{cita_id}",
            self.token,
        )

        self.assertEqual(estado, 200)
        self.assertEqual(
            cita["appointmentStatusPK"],
            "reserved",
        )

    def test_rechazar_cita_fuera_del_horario(self):
        # El profesional trabaja de 08:00 a 16:00.
        # Intentamos reservar a las 07:00.
        inicio = f"{self.fecha.isoformat()}T07:00:00-06:00"

        estado, respuesta = self.reservar(PACIENTE_1, inicio)

        self.assertEqual(estado, 422, respuesta)
        self.assertEqual(
            respuesta["errorCode"],
            "outsideWorkingHours",
        )

    def test_rechazar_profesional_no_habilitado(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios)

        # El profesional de medicina general intenta
        # atender un servicio de pediatria.
        estado, respuesta = enviar_post(
            "/appointments",
            self.token,
            {
                "patientID": PACIENTE_1,
                "professionalID": PROFESIONAL,
                "serviceID": (
                    "11111111-0030-0000-0000-000000000002"
                ),
                "startAt": espacios[0]["startAt"],
            },
        )

        self.assertEqual(estado, 422, respuesta)
        self.assertEqual(
            respuesta["errorCode"],
            "professionalNotEnabledForService",
        )

    def test_rechazar_paciente_de_otra_clinica(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios)

        # Este paciente pertenece a Monteverde,
        # pero el usuario trabaja en Santa Lucia.
        paciente_ajeno = (
            "22222222-0040-0000-0000-000000000001"
        )

        estado, respuesta = self.reservar(
            paciente_ajeno,
            espacios[0]["startAt"],
        )

        self.assertEqual(estado, 422, respuesta)
        self.assertEqual(
            respuesta["errorCode"],
            "relatedResourceNotFound",
        )

    def test_paciente_no_tiene_citas_solapadas(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios)

        inicio = espacios[0]["startAt"]

        # Primera cita: medicina general, 30 minutos.
        estado, primera = self.reservar(PACIENTE_1, inicio)

        self.assertEqual(estado, 201, primera)
        self.citas_creadas.append(primera["appointmentID"])

        # Segunda cita: mismo paciente y misma hora,
        # pero otro profesional y otro servicio.
        estado, segunda = enviar_post(
            "/appointments",
            self.token,
            {
                "patientID": PACIENTE_1,
                "professionalID": (
                    "11111111-0020-0000-0000-000000000002"
                ),
                "serviceID": (
                    "11111111-0030-0000-0000-000000000002"
                ),
                "startAt": inicio,
            },
        )

        # Si existe un defecto, limpiar tambien
        # la segunda cita antes de reportar el fallo.
        if estado == 201:
            self.citas_creadas.append(segunda["appointmentID"])

        self.assertEqual(estado, 409, segunda)
        self.assertEqual(
            segunda["errorCode"],
            "slotTaken",
        )

    def test_bloqueo_de_agenda_impide_reserva(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios)

        espacio = espacios[0]
        token_admin = obtener_token("santaLuciaAdmin")

        # Crear un bloqueo temporal en un espacio libre.
        estado, bloqueo = enviar_post(
            "/scheduleBlocks",
            token_admin,
            {
                "professionalID": PROFESIONAL,
                "startAt": espacio["startAt"],
                "endAt": espacio["endAt"],
                "reason": "Prueba automatizada I3",
            },
        )

        self.assertEqual(estado, 201, bloqueo)
        bloqueo_id = bloqueo["scheduleBlockID"]

        try:
            # Intentar reservar dentro del bloqueo.
            estado, respuesta = self.reservar(
                PACIENTE_1,
                espacio["startAt"],
            )

            if estado == 201:
                self.citas_creadas.append(
                    respuesta["appointmentID"]
                )

            self.assertEqual(estado, 422, respuesta)
            self.assertEqual(
                respuesta["errorCode"],
                "scheduleBlocked",
            )

        finally:
            # Eliminar el bloqueo aunque falle la prueba.
            solicitud = Request(
                API_URL + f"/scheduleBlocks/{bloqueo_id}",
                headers={
                    "Authorization": f"Bearer {token_admin}"
                },
                method="DELETE",
            )

            with urlopen(solicitud, timeout=15) as respuesta:
                self.assertEqual(respuesta.status, 204)

    def test_duracion_cita_corresponde_al_servicio(self):
        espacios = self.consultar_espacios()
        self.assertTrue(espacios)

        estado, cita = self.reservar(
            PACIENTE_1,
            espacios[0]["startAt"],
        )

        self.assertEqual(estado, 201, cita)
        self.citas_creadas.append(cita["appointmentID"])

        # El servicio de medicina general dura 30 minutos.
        self.assertEqual(cita["durationMinutes"], 30)

        inicio = datetime.fromisoformat(cita["startAt"])
        fin = datetime.fromisoformat(cita["endAt"])

        self.assertEqual(
            fin - inicio,
            timedelta(minutes=30),
        )

    def test_disponibilidad_antes_y_despues_de_reserva(self):
        # 1. Consultar disponibilidad inicial.
        espacios = self.consultar_espacios()
        self.assertTrue(espacios)

        inicio = espacios[0]["startAt"]

        # 2. Reservar el espacio.
        estado, cita = self.reservar(PACIENTE_1, inicio)

        self.assertEqual(estado, 201, cita)

        cita_id = cita["appointmentID"]
        self.citas_creadas.append(cita_id)

        # 3. El espacio reservado ya no debe aparecer.
        espacios_ocupados = {
            espacio["startAt"]
            for espacio in self.consultar_espacios()
        }

        self.assertNotIn(
            inicio,
            espacios_ocupados,
            "La disponibilidad muestra un espacio ya reservado.",
        )

        # 4. Cancelar la cita.
        estado, respuesta = enviar_post(
            f"/appointments/{cita_id}/cancel",
            self.token,
            {
                "cancellationReason":
                    "Prueba de actualizacion de disponibilidad"
            },
        )

        self.assertEqual(estado, 200, respuesta)

        # 5. El espacio debe aparecer nuevamente.
        espacios_liberados = {
            espacio["startAt"]
            for espacio in self.consultar_espacios()
        }

        self.assertIn(
            inicio,
            espacios_liberados,
            "La disponibilidad no refleja la cancelacion.",
        )




if __name__ == "__main__":
    unittest.main()
