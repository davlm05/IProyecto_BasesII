
import unittest
from urllib.parse import urlencode
from tests.test_citas_api import enviar_post, PACIENTE_1
import redis
from app.cache.redisTransactions import TTL_SEGUNDOS, createKey
from tests.test_citas_api import (
    PROFESIONAL,
    SERVICIO,
    fecha_laborable_futura,
)
from tests.test_seguridad_api import consultar, obtener_token
from urllib.request import Request, urlopen
from urllib.error import HTTPError
SANTA_LUCIA_ID = "11111111-0001-0000-0000-000000000001"

class TestRedisDisponibilidad(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token_santa = obtener_token("santaLuciaReception")
        cls.token_monteverde = obtener_token("monteverdeReception")
        cls.fecha = fecha_laborable_futura()

        cls.redis = redis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True,
        )
        cls.redis.ping()

    def setUp(self):
        self.clave = createKey({
            "clinicID": SANTA_LUCIA_ID,
            "professionalID": PROFESIONAL,
            "serviceID": SERVICIO,
            "targetDate": self.fecha.isoformat(),
        })

        # Limpiar solo la clave de esta prueba.
        self.redis.delete(self.clave)

    def tearDown(self):
        self.redis.delete(self.clave)

    def consultar_disponibilidad(self, token):
        parametros = urlencode({
            "professionalID": PROFESIONAL,
            "serviceID": SERVICIO,
            "targetDate": self.fecha.isoformat(),
        })

        return consultar(
            f"/availability/professional?{parametros}",
            token,
        )

    def test_cache_se_guarda_y_tiene_ttl(self):
        self.assertFalse(self.redis.exists(self.clave))

        estado, primera = self.consultar_disponibilidad(
            self.token_santa
        )
        self.assertEqual(estado, 200, primera)

        # Redis debe contener el resultado.
        self.assertTrue(self.redis.exists(self.clave))

        ttl = self.redis.ttl(self.clave)
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, TTL_SEGUNDOS)

        # Una segunda consulta debe producir el mismo resultado.
        estado, segunda = self.consultar_disponibilidad(
            self.token_santa
        )
        self.assertEqual(estado, 200, segunda)
        self.assertEqual(primera, segunda)

    def test_cache_no_expone_datos_de_otra_clinica(self):
        # Santa Lucia llena la cache.
        estado, datos = self.consultar_disponibilidad(
            self.token_santa
        )
        self.assertEqual(estado, 200, datos)
        self.assertTrue(self.redis.exists(self.clave))

        # Monteverde intenta consultar esos mismos recursos.
        estado, respuesta = self.consultar_disponibilidad(
            self.token_monteverde
        )

        # No debe recibir informacion de Santa Lucia.
        self.assertEqual(estado, 404, respuesta)
    def test_cache_se_invalida_al_reservar_y_cancelar(self):
        # 1. Consultar disponibilidad para llenar Redis.
        estado, datos = self.consultar_disponibilidad(
            self.token_santa
        )

        self.assertEqual(estado, 200, datos)
        self.assertTrue(datos["availableSlots"])

        inicio = datos["availableSlots"][0]["startAt"]

        # Verificar que la disponibilidad está guardada.
        self.assertTrue(self.redis.exists(self.clave))

        cita_id = None

        try:
            # 2. Reservar el espacio.
            estado, cita = enviar_post(
                "/appointments",
                self.token_santa,
                {
                    "patientID": PACIENTE_1,
                    "professionalID": PROFESIONAL,
                    "serviceID": SERVICIO,
                    "startAt": inicio,
                },
            )

            self.assertEqual(estado, 201, cita)
            cita_id = cita["appointmentID"]

            # La reserva debe eliminar la caché anterior.
            self.assertFalse(
                self.redis.exists(self.clave),
                "Redis no se invalidó después de reservar.",
            )

            # 3. Consultar otra vez y llenar Redis nuevamente.
            estado, datos = self.consultar_disponibilidad(
                self.token_santa
            )

            self.assertEqual(estado, 200, datos)
            self.assertTrue(self.redis.exists(self.clave))

            espacios = {
                espacio["startAt"]
                for espacio in datos["availableSlots"]
            }

            self.assertNotIn(inicio, espacios)

            # 4. Cancelar la cita.
            estado, respuesta = enviar_post(
                f"/appointments/{cita_id}/cancel",
                self.token_santa,
                {
                    "cancellationReason": "Prueba Redis",
                },
            )

            self.assertEqual(estado, 200, respuesta)
            cita_id = None

            # La cancelación también debe eliminar la caché.
            self.assertFalse(
                self.redis.exists(self.clave),
                "Redis no se invalidó después de cancelar.",
            )

            # 5. Comprobar que el espacio vuelve a estar libre.
            estado, datos = self.consultar_disponibilidad(
                self.token_santa
            )

            self.assertEqual(estado, 200, datos)

            espacios = {
                espacio["startAt"]
                for espacio in datos["availableSlots"]
            }

            self.assertIn(inicio, espacios)

        finally:
            # Evitar dejar reservas activas si falla la prueba.
            if cita_id is not None:
                enviar_post(
                    f"/appointments/{cita_id}/cancel",
                    self.token_santa,
                    {
                        "cancellationReason": "Limpieza de prueba Redis",
                    },
                )

    def test_cache_se_invalida_al_reprogramar(self):
        # 1. Obtener dos horarios libres y llenar Redis.
        estado, datos = self.consultar_disponibilidad(
            self.token_santa
        )
        self.assertEqual(estado, 200, datos)
        self.assertGreaterEqual(len(datos["availableSlots"]), 2)

        inicio_original = datos["availableSlots"][0]["startAt"]
        inicio_nuevo = datos["availableSlots"][1]["startAt"]

        self.assertTrue(self.redis.exists(self.clave))

        citas_creadas = []

        try:
            # 2. Reservar el primer horario.
            estado, cita = enviar_post(
                "/appointments",
                self.token_santa,
                {
                    "patientID": PACIENTE_1,
                    "professionalID": PROFESIONAL,
                    "serviceID": SERVICIO,
                    "startAt": inicio_original,
                },
            )
            self.assertEqual(estado, 201, cita)
            citas_creadas.append(cita["appointmentID"])

            # Volver a llenar Redis con los horarios actualizados.
            estado, datos = self.consultar_disponibilidad(
                self.token_santa
            )
            self.assertEqual(estado, 200, datos)
            self.assertTrue(self.redis.exists(self.clave))

            # 3. Reprogramar la cita al segundo horario.
            estado, resultado = enviar_post(
                f"/appointments/{cita['appointmentID']}/reschedule",
                self.token_santa,
                {"startAt": inicio_nuevo},
            )
            self.assertEqual(estado, 200, resultado)

            citas_creadas.append(
                resultado["newAppointment"]["appointmentID"]
            )

            # Redis debe eliminar los horarios anteriores.
            self.assertFalse(
                self.redis.exists(self.clave),
                "Redis no se invalidó al reprogramar.",
            )

            # 4. Consultar los horarios actualizados.
            estado, datos = self.consultar_disponibilidad(
                self.token_santa
            )
            self.assertEqual(estado, 200, datos)

            disponibles = {
                espacio["startAt"]
                for espacio in datos["availableSlots"]
            }

            # El horario original está libre.
            self.assertIn(inicio_original, disponibles)

            # El nuevo horario está ocupado.
            self.assertNotIn(inicio_nuevo, disponibles)

        finally:
            # Limpiar ambas citas.
            # La original ya estará en estado "rescheduled".
            for cita_id in reversed(citas_creadas):
                enviar_post(
                    f"/appointments/{cita_id}/cancel",
                    self.token_santa,
                    {
                        "cancellationReason": "Limpieza de prueba Redis",
                    },
                )

    def test_cache_se_invalida_al_crear_y_eliminar_bloqueo(self):
        token_admin = obtener_token("santaLuciaAdmin")

        # Consultar disponibilidad y llenar Redis.
        estado, datos = self.consultar_disponibilidad(
            self.token_santa
        )
        self.assertEqual(estado, 200, datos)
        self.assertTrue(datos["availableSlots"])

        espacio = datos["availableSlots"][0]
        inicio = espacio["startAt"]

        self.assertTrue(self.redis.exists(self.clave))

        bloqueo_id = None

        def eliminar_bloqueo(identificador):
            solicitud = Request(
                f"http://localhost:8000/scheduleBlocks/{identificador}",
                headers={
                    "Authorization": f"Bearer {token_admin}"
                },
                method="DELETE",
            )

            try:
                with urlopen(solicitud, timeout=15) as respuesta:
                    return respuesta.status
            except HTTPError as error:
                return error.code

        try:
            # Crear un bloqueo sobre el espacio disponible.
            estado, bloqueo = enviar_post(
                "/scheduleBlocks",
                token_admin,
                {
                    "professionalID": PROFESIONAL,
                    "startAt": espacio["startAt"],
                    "endAt": espacio["endAt"],
                    "reason": "Prueba de invalidacion Redis",
                },
            )

            self.assertEqual(estado, 201, bloqueo)
            bloqueo_id = bloqueo["scheduleBlockID"]

            # La creacion del bloqueo debe invalidar Redis.
            self.assertFalse(
                self.redis.exists(self.clave),
                "Redis no se invalido al crear el bloqueo.",
            )

            # La disponibilidad ya no debe mostrar el espacio.
            estado, datos = self.consultar_disponibilidad(
                self.token_santa
            )
            self.assertEqual(estado, 200, datos)

            disponibles = {
                espacio["startAt"]
                for espacio in datos["availableSlots"]
            }

            self.assertNotIn(inicio, disponibles)

            # La consulta anterior vuelve a llenar Redis.
            self.assertTrue(self.redis.exists(self.clave))

            # Eliminar el bloqueo.
            estado = eliminar_bloqueo(bloqueo_id)
            self.assertEqual(estado, 204)
            bloqueo_id = None

            # Eliminar el bloqueo debe invalidar Redis otra vez.
            self.assertFalse(
                self.redis.exists(self.clave),
                "Redis no se invalido al eliminar el bloqueo.",
            )

            # El espacio vuelve a estar disponible.
            estado, datos = self.consultar_disponibilidad(
                self.token_santa
            )
            self.assertEqual(estado, 200, datos)

            disponibles = {
                espacio["startAt"]
                for espacio in datos["availableSlots"]
            }

            self.assertIn(inicio, disponibles)

        finally:
            # Eliminar el bloqueo si la prueba falla antes.
            if bloqueo_id is not None:
                eliminar_bloqueo(bloqueo_id)

    def test_cache_se_invalida_al_modificar_horario_semanal(self):
        token_admin = obtener_token("santaLuciaAdmin")

        # 1. Consultar disponibilidad inicial.
        estado, datos = self.consultar_disponibilidad(
            self.token_santa
        )
        self.assertEqual(estado, 200, datos)

        originales = {
            espacio["startAt"]
            for espacio in datos["availableSlots"]
        }

        self.assertTrue(self.redis.exists(self.clave))

        horario_id = None

        def eliminar_horario(identificador):
            solicitud = Request(
                f"http://localhost:8000/workingHours/{identificador}",
                headers={
                    "Authorization": f"Bearer {token_admin}"
                },
                method="DELETE",
            )

            try:
                with urlopen(solicitud, timeout=15) as respuesta:
                    return respuesta.status
            except HTTPError as error:
                return error.code

        try:
            # 2. Crear un horario temporal fuera del horario habitual.
            estado, horario = enviar_post(
                f"/professionals/{PROFESIONAL}/workingHours",
                token_admin,
                {
                    "weekday": self.fecha.isoweekday(),
                    "startTimeLocal": "18:00:00",
                    "endTimeLocal": "18:30:00",
                },
            )

            self.assertEqual(estado, 201, horario)
            horario_id = horario["workingHourID"]

            # La creacion debe invalidar la cache.
            self.assertFalse(
                self.redis.exists(self.clave),
                "Redis no se invalido al crear el horario.",
            )

            # 3. Comprobar que aparecen nuevos espacios.
            estado, datos = self.consultar_disponibilidad(
                self.token_santa
            )
            self.assertEqual(estado, 200, datos)

            actualizados = {
                espacio["startAt"]
                for espacio in datos["availableSlots"]
            }

            self.assertTrue(
                actualizados - originales,
                "El horario nuevo no aparece en disponibilidad.",
            )

            self.assertTrue(self.redis.exists(self.clave))

            # 4. Eliminar el horario temporal.
            estado = eliminar_horario(horario_id)
            self.assertEqual(estado, 204)
            horario_id = None

            # La eliminacion debe invalidar Redis.
            self.assertFalse(
                self.redis.exists(self.clave),
                "Redis no se invalido al eliminar el horario.",
            )

            # 5. La disponibilidad debe regresar a su estado inicial.
            estado, datos = self.consultar_disponibilidad(
                self.token_santa
            )
            self.assertEqual(estado, 200, datos)

            restaurados = {
                espacio["startAt"]
                for espacio in datos["availableSlots"]
            }

            self.assertEqual(originales, restaurados)

        finally:
            # Limpiar el horario temporal si falla la prueba.
            if horario_id is not None:
                eliminar_horario(horario_id)


if __name__ == "__main__":
    unittest.main()
