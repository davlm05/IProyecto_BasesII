from psycopg import Connection

def insertUser(
    connection: Connection,
    clinicID: str | None,
    identityProviderSubject: str,
    rolePK: str,
) -> dict:
    cursor = connection.execute(
        """
        INSERT INTO "users" ("clinicID", "identityProviderSubject", "rolePK")
        VALUES (%s, %s, %s)
        RETURNING "userID", "clinicID", "identityProviderSubject", "rolePK",
                  "isActive", "createdAt"
        """,
        (clinicID, identityProviderSubject, rolePK),
    )
    return cursor.fetchone()


def listUsers(connection: Connection) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT "userID", "clinicID", "identityProviderSubject", "rolePK",
               "isActive", "deactivatedAt", "createdAt"
          FROM "users"
         ORDER BY "rolePK", "createdAt"
        """
    )
    return cursor.fetchall()


def findUserByID(connection: Connection, userID: str) -> dict | None:
    cursor = connection.execute(
        """
        SELECT "userID", "clinicID", "identityProviderSubject", "rolePK",
               "isActive", "deactivatedAt", "createdAt"
          FROM "users"
         WHERE "userID" = %s
        """,
        (userID,),
    )
    return cursor.fetchone()


def updateUserRole(connection: Connection, userID: str, rolePK: str) -> dict | None:
    cursor = connection.execute(
        """
        UPDATE "users"
           SET "rolePK" = %s
         WHERE "userID" = %s
        RETURNING "userID", "clinicID", "identityProviderSubject", "rolePK",
                  "isActive", "deactivatedAt", "createdAt"
        """,
        (rolePK, userID),
    )
    return cursor.fetchone()


def setUserActiveState(
    connection: Connection, userID: str, isActive: bool
) -> dict | None:
    cursor = connection.execute(
        """
        UPDATE "users"
           SET "isActive"      = %s,
               "deactivatedAt" = CASE WHEN %s THEN NULL ELSE now() END
         WHERE "userID" = %s
        RETURNING "userID", "clinicID", "identityProviderSubject", "rolePK",
                  "isActive", "deactivatedAt", "createdAt"
        """,
        (isActive, isActive, userID),
    )
    return cursor.fetchone()
