
import os
import unittest
from pathlib import Path

import psycopg


CLINICA = "11111111-0001-0000-0000-000000000001"


def leer_env():
    archivo = Path(__file__).resolve().parents[1] / ".env"
    variables = {}

    for linea in archivo.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()

        if not linea or linea.startswith("#") or "=" not in linea:
            continue

        clave, valor = linea.split("=", 1)
        variables[clave] = valor.strip().strip("\"'")

    return variables


@unittest.skipUnless(
    os.environ.get("RUN_AUDIT_DB_TESTS") == "1",
    "Pruebas reservadas para la base de datos local de desarrollo",
)
class TestIntegridadAuditoria(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        variables = leer_env()

        cls.conexion = {
            "host": "127.0.0.1",
            "port": int(variables["POSTGRES_HOST_PORT"]),
            "dbname": variables["POSTGRES_DB"],
            "user": variables["POSTGRES_USER"],
            "password": variables["POSTGRES_PASSWORD"],
            "connect_timeout": 10,
        }

        with psycopg.connect(**cls.conexion) as conn:
            fila = conn.execute(
                """
                SELECT "auditLogPK"
                FROM "auditLogs"
                WHERE "clinicID" = %s
                ORDER BY "sequenceNo"
                LIMIT 1
                """,
                (CLINICA,),
            ).fetchone()

            if fila is None:
                raise AssertionError(
                    "No hay registros de auditoria para probar."
                )

            cls.registro_id = fila[0]

    def test_no_permitir_modificar_auditoria(self):
        with psycopg.connect(**self.conexion) as conn:
            try:
                with self.assertRaises(psycopg.Error) as contexto:
                    conn.execute(
                        """
                        UPDATE "auditLogs"
                        SET "metadata" = "metadata"
                        WHERE "auditLogPK" = %s
                        """,
                        (self.registro_id,),
                    )

                self.assertEqual(
                    contexto.exception.sqlstate,
                    "MC006",
                )
            finally:
                conn.rollback()

    def test_detectar_alteracion_y_revertirla(self):
        with psycopg.connect(**self.conexion) as conn:

            try:
                # Evitar esperar indefinidamente por bloqueos.
                conn.execute(
                    "SET LOCAL lock_timeout = '5s'"
                )

                # Desactivar temporalmente el disparador
                # SOLO dentro de esta transaccion.
                conn.execute(
                    """
                    ALTER TABLE "auditLogs"
                    DISABLE TRIGGER "auditLogsBud10PreventMutation"
                    """
                )

                # Alterar un registro sin actualizar su hash.
                conn.execute(
                    """
                    UPDATE "auditLogs"
                    SET "metadata" =
                        COALESCE("metadata", '{}'::jsonb)
                        || jsonb_build_object(
                            '_testAlteracion',
                            gen_random_uuid()::text
                        )
                    WHERE "auditLogPK" = %s
                    """,
                    (self.registro_id,),
                )

                # Comprobar que el verificador detecta
                # que el contenido ya no coincide con el hash.
                filas = conn.execute(
                    """
                    SELECT "anomaly"
                    FROM "verifyAuditChain"(%s)
                    """,
                    (CLINICA,),
                ).fetchall()

                anomalias = [fila[0] for fila in filas]

                self.assertIn("tamperedRow", anomalias)

            finally:
                # Revertir la alteracion y reactivar
                # automaticamente el disparador.
                conn.rollback()

            # Verificar que la cadena regreso a
            # su estado valido original.
            filas = conn.execute(
                """
                SELECT "anomaly"
                FROM "verifyAuditChain"(%s)
                """,
                (CLINICA,),
            ).fetchall()

            self.assertEqual(filas, [])

            # Confirmar que el disparador esta activo.
            estado = conn.execute(
                """
                SELECT tgenabled
                FROM pg_trigger
                WHERE tgrelid = '"auditLogs"'::regclass
                  AND tgname = 'auditLogsBud10PreventMutation'
                """
            ).fetchone()

            self.assertIsNotNone(estado)
            self.assertEqual(estado[0], "O")


    def test_campos_inmutables_de_cita(self):
        cambios = [
            (
                "duracion",
                '"durationMinutes" = "durationMinutes" + 5',
                "MC011",
            ),
            (
                "fecha_inicio",
                '"startAt" = "startAt" + interval \'1 minute\'',
                "MC004",
            ),
        ]

        for nombre, asignacion, codigo_esperado in cambios:
            with self.subTest(campo=nombre):
                with psycopg.connect(**self.conexion) as conn:
                    fila = conn.execute(
                        """
                        SELECT "appointmentID"
                        FROM "appointments"
                        WHERE "clinicID" = %s
                        LIMIT 1
                        """,
                        (CLINICA,),
                    ).fetchone()

                    self.assertIsNotNone(
                        fila,
                        "No hay citas para realizar la prueba.",
                    )

                    try:
                        with self.assertRaises(
                            psycopg.Error
                        ) as error:
                            conn.execute(
                                f"""
                                UPDATE "appointments"
                                SET {asignacion}
                                WHERE "appointmentID" = %s
                                """,
                                (fila[0],),
                            )

                        self.assertEqual(
                            error.exception.sqlstate,
                            codigo_esperado,
                        )

                    finally:
                        conn.rollback()

if __name__ == "__main__":
    unittest.main()
