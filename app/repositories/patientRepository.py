from datetime import date
from psycopg import Connection

PATIENT_COLUMNS = """
    "patientID", "clinicID", "nationalID", "firstName", "lastName",
    "birthDate", "phone", "email", "isActive", "createdAt", "updatedAt"
"""


def insertPatient(
    connection: Connection,
    clinicID: str,
    nationalID: str,
    firstName: str,
    lastName: str,
    birthDate: date,
    phone: str | None,
    email: str | None,
) -> dict:
    cursor = connection.execute(
        f"""
        INSERT INTO "patients"
               ("clinicID", "nationalID", "firstName", "lastName",
                "birthDate", "phone", "email")
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING {PATIENT_COLUMNS}
        """,
        (clinicID, nationalID, firstName, lastName, birthDate, phone, email),
    )
    return cursor.fetchone()


def listPatients(connection: Connection, searchText: str | None) -> list[dict]:
    cursor = connection.execute(
        f"""
        SELECT {PATIENT_COLUMNS}
          FROM "patients"
         WHERE "isActive"
           AND (%s::text IS NULL
                OR lower("lastName")  LIKE lower(%s) || '%%'
                OR lower("firstName") LIKE lower(%s) || '%%')
         ORDER BY lower("lastName"), lower("firstName")
         LIMIT 200
        """,
        (searchText, searchText, searchText),
    )
    return cursor.fetchall()


def findPatientByID(connection: Connection, patientID: str) -> dict | None:
    cursor = connection.execute(
        f"""
        SELECT {PATIENT_COLUMNS}
          FROM "patients"
         WHERE "patientID" = %s
        """,
        (patientID,),
    )
    return cursor.fetchone()


def updatePatient(
    connection: Connection,
    patientID: str,
    firstName: str,
    lastName: str,
    birthDate: date,
    phone: str | None,
    email: str | None,
) -> dict | None:
    cursor = connection.execute(
        f"""
        UPDATE "patients"
           SET "firstName" = %s,
               "lastName"  = %s,
               "birthDate" = %s,
               "phone"     = %s,
               "email"     = %s
         WHERE "patientID" = %s
        RETURNING {PATIENT_COLUMNS}
        """,
        (firstName, lastName, birthDate, phone, email, patientID),
    )
    return cursor.fetchone()
