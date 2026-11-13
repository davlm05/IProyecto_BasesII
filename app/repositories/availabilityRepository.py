from datetime import date
from psycopg import Connection

def findServiceDurationMinutes(
    connection: Connection, serviceID: str
) -> int | None:
    cursor = connection.execute(
        """
        SELECT "durationMinutes"
          FROM "services"
         WHERE "serviceID" = %s
           AND "isActive"
        """,
        (serviceID,),
    )
    row = cursor.fetchone()
    return row["durationMinutes"] if row else None


def listWorkingIntervalsForDate(
    connection: Connection, professionalID: str, targetDate: date
) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT ((%s::date + wh."startTimeLocal") AT TIME ZONE c."timeZone") AS "startAt",
               ((%s::date + wh."endTimeLocal")   AT TIME ZONE c."timeZone") AS "endAt"
          FROM "workingHours" wh
          JOIN "clinics" c ON c."clinicID" = wh."clinicID"
         WHERE wh."professionalID" = %s
           AND wh."weekday"        = EXTRACT(ISODOW FROM %s::date)::smallint
         ORDER BY wh."startTimeLocal"
        """,
        (targetDate, targetDate, professionalID, targetDate),
    )
    return cursor.fetchall()


def listBusyIntervals(
    connection: Connection,
    professionalID: str,
    fromInstant,
    toInstant,
) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT a."startAt", a."endAt", 'appointment' AS "busySource"
          FROM "appointments" a
         WHERE a."professionalID" = %s
           AND a."appointmentStatusPK" NOT IN ('cancelled', 'rescheduled')
           AND tstzrange(a."startAt", a."endAt", '[)')
            && tstzrange(%s, %s, '[)')
        UNION ALL
        SELECT sb."startAt", sb."endAt", 'scheduleBlock' AS "busySource"
          FROM "scheduleBlocks" sb
         WHERE sb."professionalID" = %s
           AND tstzrange(sb."startAt", sb."endAt", '[)')
            && tstzrange(%s, %s, '[)')
         ORDER BY "startAt"
        """,
        (professionalID, fromInstant, toInstant, professionalID, fromInstant, toInstant),
    )
    return cursor.fetchall()


def findClinicTimeZone(connection: Connection, clinicID: str) -> str | None:
    cursor = connection.execute(
        """
        SELECT "timeZone"
          FROM "clinics"
         WHERE "clinicID" = %s
        """,
        (clinicID,),
    )
    row = cursor.fetchone()
    return row["timeZone"] if row else None
