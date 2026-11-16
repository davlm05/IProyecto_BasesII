
import json
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = "http://localhost:8000"
TOKEN_URL = (
    "http://localhost:8080/realms/MediCitas/"
    "protocol/openid-connect/token"
)


def leer_password_pruebas():
    archivo = Path(__file__).resolve().parents[1] / ".env"

    for linea in archivo.read_text(encoding="utf-8").splitlines():
        if linea.startswith("MEDICITAS_TEST_USER_PASSWORD="):
            return linea.split("=", 1)[1].strip().strip("\"'")

    raise RuntimeError(
        "No se encontro MEDICITAS_TEST_USER_PASSWORD en .env"
    )


def obtener_token(usuario):
    datos = urlencode({
        "client_id": "medicitasApi",
        "grant_type": "password",
        "username": usuario,
        "password": leer_password_pruebas(),
    }).encode("utf-8")

    solicitud = Request(
        TOKEN_URL,
        data=datos,
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        },
        method="POST",
    )

    with urlopen(solicitud, timeout=15) as respuesta:
        return json.load(respuesta)["access_token"]


def consultar(ruta, token=None):
    encabezados = {}

    if token is not None:
        encabezados["Authorization"] = f"Bearer {token}"

    solicitud = Request(
        API_URL + ruta,
        headers=encabezados,
    )

    try:
        with urlopen(solicitud, timeout=15) as respuesta:
            return respuesta.status, json.load(respuesta)
    except HTTPError as error:
        return error.code, json.load(error)


class TestSeguridadAPI(unittest.TestCase):

    def test_api_disponible(self):
        estado, datos = consultar("/health")

        self.assertEqual(estado, 200)
        self.assertEqual(datos["status"], "ok")

    def test_sin_token_retorna_401(self):
        estado, datos = consultar("/patients")

        self.assertEqual(estado, 401)
        self.assertEqual(datos["errorCode"], "missingToken")

    def test_token_invalido_retorna_401(self):
        estado, datos = consultar(
            "/patients",
            token="token_invalido",
        )

        self.assertEqual(estado, 401)
        self.assertEqual(datos["errorCode"], "invalidToken")

    def test_recepcion_no_puede_administrar_usuarios(self):
        token = obtener_token("santaLuciaReception")

        estado, datos = consultar("/users", token)

        self.assertEqual(estado, 403)
        self.assertEqual(datos["errorCode"], "forbiddenRole")

    def test_recepcion_consulta_su_clinica(self):
        token = obtener_token("santaLuciaReception")

        estado, datos = consultar("/clinics/current", token)

        self.assertEqual(estado, 200)
        self.assertEqual(
            datos["clinicID"],
            "11111111-0001-0000-0000-000000000001",
        )


if __name__ == "__main__":
    unittest.main()
