from datetime import date, datetime, time
from psycopg import Connection

def insertWorkingHour(
    connection: Connection,
    clinicID: str,
    professionalID: str,
    weekday: int,
    startTimeLocal: time,
    endTimeLocal: time,
) -> dict:
    
    cursor = connection.execute(
        """
        INSERT INTO "workingHours"
               ("clinicID", "professionalID", "weekday", "startTimeLocal", "endTimeLocal")
        VALUES (%s, %s, %s, %s, %s)
        RETURNING "workingHourID", "clinicID", "professionalID", "weekday",
                  "startTimeLocal", "endTimeLocal", "createdAt"
        """,
        (clinicID, professionalID, weekday, startTimeLocal, endTimeLocal),
    )
    return cursor.fetchone()


def listWorkingHours(connection: Connection, professionalID: str) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT "workingHourID", "clinicID", "professionalID", "weekday",
               "startTimeLocal", "endTimeLocal", "createdAt"
          FROM "workingHours"
         WHERE "professionalID" = %s
         ORDER BY "weekday", "startTimeLocal"
        """,
        (professionalID,),
    )
    return cursor.fetchall()


def deleteWorkingHour(connection: Connection, workingHourID: str) -> int:

    cursor = connection.execute(
        """
        DELETE FROM "workingHours"
         WHERE "workingHourID" = %s
        """,
        (workingHourID,),
    )
    return cursor.rowcount


# =============================================================================
# scheduleBlocks - RF6
# =============================================================================
def insertScheduleBlock(
    connection: Connection,
    clinicID: str,
    professionalID: str,
    startAt: datetime,
    endAt: datetime,
    reason: str,
    userID: str,
) -> dict:
    cursor = connection.execute(
        """
        INSERT INTO "scheduleBlocks"
               ("clinicID", "professionalID", "startAt", "endAt", "reason", "userID")
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING "scheduleBlockID", "clinicID", "professionalID",
                  "startAt", "endAt", "reason", "userID", "createdAt"
        """,
        (clinicID, professionalID, startAt, endAt, reason, userID),
    )
    return cursor.fetchone()


def listScheduleBlocks(
    connection: Connection,
    professionalID: str | None,
    fromDate: date,
    toDate: date,
) -> list[dict]:
    cursor = connection.execute(
        """
        WITH "clinicWindow" AS (
            SELECT ((%s::date)::timestamp     AT TIME ZONE c."timeZone") AS "fromInstant",
                   ((%s::date + 1)::timestamp AT TIME ZONE c."timeZone") AS "toInstant"
              FROM "clinics" c
             WHERE c."clinicID" = "currentClinicID"()
        )
        SELECT sb."scheduleBlockID", sb."clinicID", sb."professionalID",
               sb."startAt", sb."endAt", sb."reason", sb."userID", sb."createdAt"
          FROM "scheduleBlocks" sb
          CROSS JOIN "clinicWindow" w
         WHERE (%s::uuid IS NULL OR sb."professionalID" = %s::uuid)
           AND sb."startAt" < w."toInstant"
           AND sb."endAt"   > w."fromInstant"
         ORDER BY sb."startAt"
        """,
        (fromDate, toDate, professionalID, professionalID),
    )
    return cursor.fetchall()


def findScheduleBlockByID(
    connection: Connection, scheduleBlockID: str
) -> dict | None:
    cursor = connection.execute(
        """
        SELECT "scheduleBlockID", "clinicID", "professionalID",
               "startAt", "endAt", "reason", "userID", "createdAt"
          FROM "scheduleBlocks"
         WHERE "scheduleBlockID" = %s
        """,
        (scheduleBlockID,),
    )
    return cursor.fetchone()


def deleteScheduleBlock(connection: Connection, scheduleBlockID: str) -> int:
    cursor = connection.execute(
        """
        DELETE FROM "scheduleBlocks"
         WHERE "scheduleBlockID" = %s
        """,
        (scheduleBlockID,),
    )
    return cursor.rowcount


def listAppointmentsConflictingWithBlock(
    connection: Connection, scheduleBlockID: str
) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT a."appointmentID", a."patientID", a."professionalID",
               a."serviceID", a."startAt", a."endAt", a."appointmentStatusPK",
               pa."firstName", pa."lastName"
          FROM "scheduleBlocks" sb
          JOIN "appointments" a
                ON a."clinicID"       = sb."clinicID"
               AND a."professionalID" = sb."professionalID"
               AND a."appointmentStatusPK" NOT IN ('cancelled', 'rescheduled')
               AND tstzrange(a."startAt", a."endAt", '[)')
                && tstzrange(sb."startAt", sb."endAt", '[)')
          JOIN "patients" pa
                ON pa."clinicID"  = a."clinicID"
               AND pa."patientID" = a."patientID"
         WHERE sb."scheduleBlockID" = %s
         ORDER BY a."startAt"
        """,
        (scheduleBlockID,),
    )
    return cursor.fetchall()
