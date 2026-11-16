
import unittest

from urllib.parse import urlencode

from tests.test_seguridad_api import consultar, obtener_token


SANTA_LUCIA_ID = "11111111-0001-0000-0000-000000000001"
MONTEVERDE_ID = "22222222-0001-0000-0000-000000000001"

PACIENTE_SANTA_LUCIA = "11111111-0040-0000-0000-000000000001"
PACIENTE_MONTEVERDE = "22222222-0040-0000-0000-000000000001"

USUARIO_RECEPCION = "11111111-0010-0000-0000-000000000002"


class TestAuditoriaAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.admin_sl = obtener_token("santaLuciaAdmin")
        cls.admin_mv = obtener_token("monteverdeAdmin")
        cls.recepcion_sl = obtener_token("santaLuciaReception")
        cls.recepcion_mv = obtener_token("monteverdeReception")

    def test_lectura_de_paciente_genera_auditoria(self):
        # Consultar información de contacto de un paciente.
        estado, paciente = consultar(
            f"/patients/{PACIENTE_SANTA_LUCIA}",
            self.recepcion_sl,
        )

        self.assertEqual(estado, 200, paciente)

        # Consultar los registros asociados a ese paciente.
        parametros = urlencode({
            "patientID": PACIENTE_SANTA_LUCIA
        })

        estado, registros = consultar(
            f"/auditLogs?{parametros}",
            self.admin_sl,
        )

        self.assertEqual(estado, 200, registros)

        coincidencias = [
            registro for registro in registros
            if (
                registro["auditActionPK"] == "readPatientContact"
                and registro["userID"] == USUARIO_RECEPCION
                and registro["patientID"] == PACIENTE_SANTA_LUCIA
            )
        ]

        self.assertTrue(
            coincidencias,
            "No se encontro el registro de lectura del paciente.",
        )

        # Cada registro debe tener una huella SHA-256.
        for registro in coincidencias:
            self.assertRegex(
                registro["rowHashHex"],
                r"^[0-9a-f]{64}$",
            )

    def test_recepcion_no_puede_ver_auditoria(self):
        for ruta in ("/auditLogs", "/auditLogs/verification"):
            with self.subTest(ruta=ruta):
                estado, respuesta = consultar(
                    ruta,
                    self.recepcion_sl,
                )

                self.assertEqual(estado, 403, respuesta)
                self.assertEqual(
                    respuesta["errorCode"],
                    "forbiddenRole",
                )

    def test_auditoria_aislada_entre_clinicas(self):
        # Generar una lectura auditable en cada clinica.
        estado, _ = consultar(
            f"/patients/{PACIENTE_SANTA_LUCIA}",
            self.recepcion_sl,
        )
        self.assertEqual(estado, 200)

        estado, _ = consultar(
            f"/patients/{PACIENTE_MONTEVERDE}",
            self.recepcion_mv,
        )
        self.assertEqual(estado, 200)

        estado_sl, registros_sl = consultar(
            "/auditLogs",
            self.admin_sl,
        )

        estado_mv, registros_mv = consultar(
            "/auditLogs",
            self.admin_mv,
        )

        self.assertEqual(estado_sl, 200, registros_sl)
        self.assertEqual(estado_mv, 200, registros_mv)

        self.assertTrue(registros_sl)
        self.assertTrue(registros_mv)

        for registro in registros_sl:
            self.assertEqual(
                registro["clinicID"],
                SANTA_LUCIA_ID,
            )

        for registro in registros_mv:
            self.assertEqual(
                registro["clinicID"],
                MONTEVERDE_ID,
            )

    def test_verificar_integridad_cadena(self):
        for clinica_id, token in (
            (SANTA_LUCIA_ID, self.admin_sl),
            (MONTEVERDE_ID, self.admin_mv),
        ):
            with self.subTest(clinica=clinica_id):
                estado, resultado = consultar(
                    "/auditLogs/verification",
                    token,
                )

                self.assertEqual(estado, 200, resultado)
                self.assertEqual(
                    resultado["clinicID"],
                    clinica_id,
                )
                self.assertTrue(
                    resultado["isIntact"],
                    resultado["anomalies"],
                )
                self.assertEqual(
                    resultado["anomalies"],
                    [],
                )


if __name__ == "__main__":
    unittest.main()
