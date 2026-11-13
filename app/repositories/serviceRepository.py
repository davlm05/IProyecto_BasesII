from psycopg import Connection

def insertService(
    connection: Connection,
    clinicID: str,
    name: str,
    description: str | None,
    durationMinutes: int,
    specialtyID: str,
) -> dict:
    cursor = connection.execute(
        """
        INSERT INTO "services"
               ("clinicID", "name", "description", "durationMinutes", "specialtyID")
        VALUES (%s, %s, %s, %s, %s)
        RETURNING "serviceID", "clinicID", "name", "description",
                  "durationMinutes", "specialtyID", "isActive", "createdAt"
        """,
        (clinicID, name, description, durationMinutes, specialtyID),
    )
    return cursor.fetchone()


def listServices(connection: Connection, onlyActive: bool) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT s."serviceID", s."clinicID", s."name", s."description",
               s."durationMinutes", s."specialtyID", sp."name" AS "specialtyName",
               s."isActive", s."createdAt"
          FROM "services" s
          JOIN "specialties" sp ON sp."specialtyID" = s."specialtyID"
         WHERE (%s = false OR s."isActive")
         ORDER BY s."name"
        """,
        (onlyActive,),
    )
    return cursor.fetchall()


def findServiceByID(connection: Connection, serviceID: str) -> dict | None:
    cursor = connection.execute(
        """
        SELECT "serviceID", "clinicID", "name", "description",
               "durationMinutes", "specialtyID", "isActive", "createdAt"
          FROM "services"
         WHERE "serviceID" = %s
        """,
        (serviceID,),
    )
    return cursor.fetchone()


def updateService(
    connection: Connection,
    serviceID: str,
    name: str,
    description: str | None,
    durationMinutes: int,
    isActive: bool,
) -> dict | None:
    cursor = connection.execute(
        """
        UPDATE "services"
           SET "name"            = %s,
               "description"     = %s,
               "durationMinutes" = %s,
               "isActive"        = %s
         WHERE "serviceID" = %s
        RETURNING "serviceID", "clinicID", "name", "description",
                  "durationMinutes", "specialtyID", "isActive", "createdAt"
        """,
        (name, description, durationMinutes, isActive, serviceID),
    )
    return cursor.fetchone()
