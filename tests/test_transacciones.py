
import unittest

from psycopg.errors import (
    DeadlockDetected,
    SerializationFailure,
)

from app.db.transaction import runWithSerializationRetry


class TestTransacciones(unittest.TestCase):

    def test_operacion_exitosa_sin_reintentos(self):
        intentos = 0

        def operacion():
            nonlocal intentos
            intentos += 1
            return "reserva exitosa"

        resultado = runWithSerializationRetry(3, operacion)

        self.assertEqual(resultado, "reserva exitosa")
        self.assertEqual(intentos, 1)

    def test_reintento_por_error_serializacion(self):
        intentos = 0

        def operacion():
            nonlocal intentos
            intentos += 1

            if intentos == 1:
                raise SerializationFailure(
                    "Conflicto de serializacion simulado"
                )

            return "reserva exitosa"

        resultado = runWithSerializationRetry(3, operacion)

        self.assertEqual(resultado, "reserva exitosa")
        self.assertEqual(intentos, 2)

    def test_reintento_por_deadlock(self):
        intentos = 0

        def operacion():
            nonlocal intentos
            intentos += 1

            if intentos == 1:
                raise DeadlockDetected(
                    "Deadlock simulado"
                )

            return "reserva exitosa"

        resultado = runWithSerializationRetry(3, operacion)

        self.assertEqual(resultado, "reserva exitosa")
        self.assertEqual(intentos, 2)

    def test_error_despues_de_agotar_reintentos(self):
        intentos = 0

        def operacion():
            nonlocal intentos
            intentos += 1
            raise SerializationFailure(
                "Conflicto persistente"
            )

        with self.assertRaises(SerializationFailure):
            runWithSerializationRetry(3, operacion)

        self.assertEqual(intentos, 3)


if __name__ == "__main__":
    unittest.main()


