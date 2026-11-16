
import unittest

from tests.test_seguridad_api import consultar, obtener_token


SANTA_LUCIA_ID = "11111111-0001-0000-0000-000000000001"
MONTEVERDE_ID = "22222222-0001-0000-0000-000000000001"


class TestAislamientoClinicas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.token_santa_lucia = obtener_token(
            "santaLuciaReception"
        )
        cls.token_monteverde = obtener_token(
            "monteverdeReception"
        )

        estado_sl, cls.pacientes_sl = consultar(
            "/patients",
            cls.token_santa_lucia,
        )

        estado_mv, cls.pacientes_mv = consultar(
            "/patients",
            cls.token_monteverde,
        )

        if estado_sl != 200 or estado_mv != 200:
            raise AssertionError(
                "No fue posible consultar los pacientes."
            )

        if not cls.pacientes_sl or not cls.pacientes_mv:
            raise AssertionError(
                "Las dos clinicas necesitan pacientes de prueba."
            )

    def test_listado_solo_muestra_pacientes_propios(self):
        for paciente in self.pacientes_sl:
            self.assertEqual(
                paciente["clinicID"],
                SANTA_LUCIA_ID,
            )

        for paciente in self.pacientes_mv:
            self.assertEqual(
                paciente["clinicID"],
                MONTEVERDE_ID,
            )

    def test_acceso_directo_a_paciente_ajeno(self):
        paciente_monteverde = self.pacientes_mv[0]["patientID"]

        estado, datos = consultar(
            f"/patients/{paciente_monteverde}",
            self.token_santa_lucia,
        )

        self.assertEqual(estado, 404)
        self.assertEqual(
            datos["errorCode"],
            "resourceNotFound",
        )

        paciente_santa_lucia = self.pacientes_sl[0]["patientID"]

        estado, datos = consultar(
            f"/patients/{paciente_santa_lucia}",
            self.token_monteverde,
        )

        self.assertEqual(estado, 404)
        self.assertEqual(
            datos["errorCode"],
            "resourceNotFound",
        )

    def test_manipulacion_identificador_clinica(self):
        estado, pacientes = consultar(
            f"/patients?clinicID={MONTEVERDE_ID}",
            self.token_santa_lucia,
        )

        self.assertEqual(estado, 200)

        ids_normales = {
            paciente["patientID"]
            for paciente in self.pacientes_sl
        }

        ids_manipulados = {
            paciente["patientID"]
            for paciente in pacientes
        }

        self.assertEqual(ids_normales, ids_manipulados)

        for paciente in pacientes:
            self.assertEqual(
                paciente["clinicID"],
                SANTA_LUCIA_ID,
            )

    def test_historial_de_paciente_ajeno(self):
        paciente_monteverde = self.pacientes_mv[0]["patientID"]

        estado, datos = consultar(
            f"/patients/{paciente_monteverde}/appointments",
            self.token_santa_lucia,
        )

        self.assertEqual(estado, 404)
        self.assertEqual(
            datos["errorCode"],
            "resourceNotFound",
        )


if __name__ == "__main__":
    unittest.main()
