from psycopg import Connection

def insertClinic(
    connection: Connection, code: str, name: str, timeZone: str
) -> dict:
    cursor = connection.execute(
        """
        INSERT INTO "clinics" ("code", "name", "timeZone")
        VALUES (%s, %s, %s)
        RETURNING "clinicID", "code", "name", "timeZone", "isActive", "createdAt"
        """,
        (code, name, timeZone),
    )
    return cursor.fetchone()


def listClinics(connection: Connection) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT "clinicID", "code", "name", "timeZone", "isActive", "createdAt"
          FROM "clinics"
         ORDER BY "name"
        """
    )
    return cursor.fetchall()


def findClinicByID(connection: Connection, clinicID: str) -> dict | None:
    cursor = connection.execute(
        """
        SELECT "clinicID", "code", "name", "timeZone", "isActive", "createdAt"
          FROM "clinics"
         WHERE "clinicID" = %s
        """,
        (clinicID,),
    )
    return cursor.fetchone()
