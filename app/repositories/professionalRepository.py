from psycopg import Connection

def insertProfessional(
    connection: Connection,
    clinicID: str,
    userID: str,
    specialtyID: str,
    fullName: str,
    licenseCode: str | None,
) -> dict:
    cursor = connection.execute(
        """
        INSERT INTO "professionals"
               ("clinicID", "userID", "specialtyID", "fullName", "licenseCode")
        VALUES (%s, %s, %s, %s, %s)
        RETURNING "professionalID", "clinicID", "userID", "specialtyID",
                  "fullName", "licenseCode", "isActive", "createdAt"
        """,
        (clinicID, userID, specialtyID, fullName, licenseCode),
    )
    return cursor.fetchone()


def listProfessionals(connection: Connection, onlyActive: bool) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT p."professionalID", p."clinicID", p."userID", p."specialtyID",
               sp."name" AS "specialtyName", p."fullName", p."licenseCode",
               p."isActive", p."createdAt"
          FROM "professionals" p
          JOIN "specialties" sp ON sp."specialtyID" = p."specialtyID"
         WHERE (%s = false OR p."isActive")
         ORDER BY p."fullName"
        """,
        (onlyActive,),
    )
    return cursor.fetchall()


def findProfessionalByID(connection: Connection, professionalID: str) -> dict | None:
    cursor = connection.execute(
        """
        SELECT "professionalID", "clinicID", "userID", "specialtyID",
               "fullName", "licenseCode", "isActive", "createdAt"
          FROM "professionals"
         WHERE "professionalID" = %s
        """,
        (professionalID,),
    )
    return cursor.fetchone()


def setProfessionalActiveState(
    connection: Connection, professionalID: str, isActive: bool
) -> dict | None:
    cursor = connection.execute(
        """
        UPDATE "professionals"
           SET "isActive" = %s
         WHERE "professionalID" = %s
        RETURNING "professionalID", "clinicID", "userID", "specialtyID",
                  "fullName", "licenseCode", "isActive", "createdAt"
        """,
        (isActive, professionalID),
    )
    return cursor.fetchone()


def deleteProfessionalServices(connection: Connection, professionalID: str) -> None:
    connection.execute(
        """
        DELETE FROM "professionalServices"
         WHERE "professionalID" = %s
        """,
        (professionalID,),
    )


def insertProfessionalService(
    connection: Connection, clinicID: str, professionalID: str, serviceID: str
) -> None:
    connection.execute(
        """
        INSERT INTO "professionalServices"
               ("clinicID", "professionalID", "serviceID", "specialtyID")
        SELECT %s, %s, %s, p."specialtyID"
          FROM "professionals" p
         WHERE p."clinicID"       = %s
           AND p."professionalID" = %s
        """,
        (clinicID, professionalID, serviceID, clinicID, professionalID),
    )


def listProfessionalServices(connection: Connection, professionalID: str) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT ps."serviceID", s."name", s."durationMinutes", s."isActive"
          FROM "professionalServices" ps
          JOIN "services" s ON s."clinicID"  = ps."clinicID"
                           AND s."serviceID" = ps."serviceID"
         WHERE ps."professionalID" = %s
         ORDER BY s."name"
        """,
        (professionalID,),
    )
    return cursor.fetchall()


def listProfessionalsOfferingService(
    connection: Connection, serviceID: str
) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT p."professionalID", p."fullName", p."specialtyID"
          FROM "professionalServices" ps
          JOIN "professionals" p ON p."clinicID"       = ps."clinicID"
                                AND p."professionalID" = ps."professionalID"
         WHERE ps."serviceID" = %s
           AND p."isActive"
         ORDER BY p."fullName"
        """,
        (serviceID,),
    )
    return cursor.fetchall()
