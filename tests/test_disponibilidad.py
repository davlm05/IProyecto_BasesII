
import unittest
from datetime import datetime, timezone

from app.services.availabilityService import (
    buildSlotsForWorkingInterval,
    overlapsAnyBusyInterval,
)


def hora(horas, minutos=0):
    return datetime(
        2030, 1, 15, horas, minutos, tzinfo=timezone.utc
    )


class TestDisponibilidad(unittest.TestCase):

    def test_horario_sin_ocupaciones(self):
        espacios = buildSlotsForWorkingInterval(
            intervalStart=hora(9),
            intervalEnd=hora(11),
            durationMinutes=30,
            busyIntervals=[],
            earliestAllowedStart=hora(8),
        )

        self.assertEqual(len(espacios), 4)

    def test_horario_con_citas_ocupadas(self):
        ocupaciones = [
            {
                "startAt": hora(9, 30),
                "endAt": hora(10, 30),
            }
        ]

        espacios = buildSlotsForWorkingInterval(
            intervalStart=hora(9),
            intervalEnd=hora(11),
            durationMinutes=30,
            busyIntervals=ocupaciones,
            earliestAllowedStart=hora(8),
        )

        self.assertEqual(len(espacios), 2)
        self.assertEqual(espacios[0]["startAt"], hora(9))
        self.assertEqual(
            espacios[1]["startAt"], hora(10, 30)
        )

    def test_intervalos_consecutivos_no_se_solapan(self):
        ocupaciones = [
            {
                "startAt": hora(9, 30),
                "endAt": hora(10),
            }
        ]

        resultado = overlapsAnyBusyInterval(
            hora(9),
            hora(9, 30),
            ocupaciones,
        )

        self.assertFalse(resultado)

    def test_no_ofrecer_espacios_anteriores(self):
        espacios = buildSlotsForWorkingInterval(
            intervalStart=hora(9),
            intervalEnd=hora(11),
            durationMinutes=30,
            busyIntervals=[],
            earliestAllowedStart=hora(10),
        )

        self.assertEqual(len(espacios), 2)
        self.assertEqual(espacios[0]["startAt"], hora(10))


if __name__ == "__main__":
    unittest.main()
