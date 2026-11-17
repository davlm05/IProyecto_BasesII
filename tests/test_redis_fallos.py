
import unittest
from contextlib import nullcontext
from datetime import date
from unittest.mock import Mock, patch

from redis.exceptions import ConnectionError

from app.services.availabilityService import getProfessionalAvailability


class TestRedisFallos(unittest.TestCase):

    def test_disponibilidad_funciona_si_redis_falla(self):
        # Simular un cliente Redis desconectado.
        cliente = Mock()
        cliente.get.side_effect = ConnectionError(
            "Redis no disponible"
        )
        cliente.setex.side_effect = ConnectionError(
            "Redis no disponible"
        )

        redis_registry = Mock()
        redis_registry.getClient.return_value = cliente

        contexto = Mock()
        contexto.clinicID = "11111111-0001-0000-0000-000000000001"

        profesional = "11111111-0020-0000-0000-000000000001"
        servicio = "11111111-0030-0000-0000-000000000001"

        # Simular respuestas correctas de PostgreSQL.
        with (
            patch(
                "app.services.availabilityService.openTenantTransaction",
                return_value=nullcontext(object()),
            ),
            patch(
                "app.services.availabilityService."
                "availabilityRepository.findServiceDurationMinutes",
                return_value=30,
            ),
            patch(
                "app.services.availabilityService."
                "professionalRepository.findProfessionalByID",
                return_value={"fullName": "Profesional de prueba"},
            ),
            patch(
                "app.services.availabilityService."
                "calculateProfessionalAvailability",
                return_value=[],
            ),
        ):
            resultado = getProfessionalAvailability(
                pools=Mock(),
                redisRegistry=redis_registry,
                requestContext=contexto,
                professionalID=profesional,
                serviceID=servicio,
                targetDate=date(2030, 1, 7),
            )

        # La consulta debe funcionar aunque Redis esté desconectado.
        self.assertEqual(resultado["professionalID"], profesional)
        self.assertEqual(resultado["durationMinutes"], 30)
        self.assertEqual(resultado["availableSlots"], [])
