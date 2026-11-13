from psycopg import Connection

def insertClinicalNote(
    connection: Connection,
    clinicID: str,
    appointmentID: str,
    professionalID: str,
    content: str,
) -> dict:
    cursor = connection.execute(
        """
        INSERT INTO "clinicalNotes"
               ("clinicID", "appointmentID", "professionalID", "content")
        VALUES (%s, %s, %s, %s)
        RETURNING "clinicalNoteID", "clinicID", "appointmentID",
                  "professionalID", "content", "createdAt", "updatedAt"
        """,
        (clinicID, appointmentID, professionalID, content),
    )
    return cursor.fetchone()


def findClinicalNoteByAppointment(
    connection: Connection, appointmentID: str
) -> dict | None:
    cursor = connection.execute(
        """
        SELECT "clinicalNoteID", "clinicID", "appointmentID",
               "professionalID", "content", "createdAt", "updatedAt"
          FROM "clinicalNotes"
         WHERE "appointmentID" = %s
        """,
        (appointmentID,),
    )
    return cursor.fetchone()


def updateClinicalNote(
    connection: Connection, appointmentID: str, content: str
) -> dict | None:
    cursor = connection.execute(
        """
        UPDATE "clinicalNotes"
           SET "content" = %s
         WHERE "appointmentID" = %s
        RETURNING "clinicalNoteID", "clinicID", "appointmentID",
                  "professionalID", "content", "createdAt", "updatedAt"
        """,
        (content, appointmentID),
    )
    return cursor.fetchone()
