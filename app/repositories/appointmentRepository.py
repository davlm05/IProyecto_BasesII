from datetime import date, datetime
from psycopg import Connection

APPOINTMENT_COLUMNS = """
    "appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
    "startAt", "endAt", "durationMinutes", "appointmentStatusPK",
    "createdByUserID", "createdAt", "updatedAt",
    "cancelledAt", "cancelledByUserID", "cancellationReason",
    "outcomeRecordedAt", "outcomeRecordedByUserID",
    "rescheduledToAppointmentID"
"""

def insertAppointment(
    connection: Connection,
    clinicID: str,
    patientID: str,
    professionalID: str,
    serviceID: str,
    startAt: datetime,
    createdByUserID: str,
) -> dict:
    cursor = connection.execute(
        f"""
        INSERT INTO "appointments"
               ("clinicID", "patientID", "professionalID", "serviceID",
                "startAt", "durationMinutes", "endAt", "createdByUserID")
        VALUES (%s, %s, %s, %s, %s, 5, %s + interval '5 minutes', %s)
        RETURNING {APPOINTMENT_COLUMNS}
        """,
        (clinicID, patientID, professionalID, serviceID, startAt, startAt, createdByUserID),
    )
    return cursor.fetchone()


def findAppointmentByID(connection: Connection, appointmentID: str) -> dict | None:
    cursor = connection.execute(
        f"""
        SELECT {APPOINTMENT_COLUMNS}
          FROM "appointments"
         WHERE "appointmentID" = %s
        """,
        (appointmentID,),
    )
    return cursor.fetchone()


def markAppointmentAsRescheduled(
    connection: Connection,
    appointmentID: str,
    newAppointmentID: str,
) -> dict | None:
    cursor = connection.execute(
        f"""
        UPDATE "appointments"
           SET "appointmentStatusPK"        = 'rescheduled',
               "rescheduledToAppointmentID" = %s
         WHERE "appointmentID" = %s
        RETURNING {APPOINTMENT_COLUMNS}
        """,
        (newAppointmentID, appointmentID),
    )
    return cursor.fetchone()


def cancelAppointment(
    connection: Connection,
    appointmentID: str,
    cancelledByUserID: str,
    cancellationReason: str,
) -> dict | None:
    cursor = connection.execute(
        f"""
        UPDATE "appointments"
           SET "appointmentStatusPK" = 'cancelled',
               "cancelledAt"         = now(),
               "cancelledByUserID"   = %s,
               "cancellationReason"  = %s
         WHERE "appointmentID" = %s
        RETURNING {APPOINTMENT_COLUMNS}
        """,
        (cancelledByUserID, cancellationReason, appointmentID),
    )
    return cursor.fetchone()


def recordAppointmentOutcome(
    connection: Connection,
    appointmentID: str,
    appointmentStatusPK: str,
    outcomeRecordedByUserID: str,
) -> dict | None:

    cursor = connection.execute(
        f"""
        UPDATE "appointments"
           SET "appointmentStatusPK"     = %s,
               "outcomeRecordedAt"       = now(),
               "outcomeRecordedByUserID" = %s
         WHERE "appointmentID" = %s
        RETURNING {APPOINTMENT_COLUMNS}
        """,
        (appointmentStatusPK, outcomeRecordedByUserID, appointmentID),
    )
    return cursor.fetchone()


def listAppointmentsForDay(
    connection: Connection,
    targetDate: date,
    professionalID: str | None,
) -> list[dict]:

    cursor = connection.execute(
        """
        SELECT a."appointmentID", a."patientID", a."professionalID", a."serviceID",
               a."startAt", a."endAt", a."durationMinutes", a."appointmentStatusPK",
               pa."firstName", pa."lastName", pa."nationalID",
               pr."fullName" AS "professionalName",
               s."name"      AS "serviceName"
          FROM "appointments" a
          JOIN "clinics"  c  ON c."clinicID" = a."clinicID"
          JOIN "patients" pa ON pa."clinicID"  = a."clinicID"
                            AND pa."patientID" = a."patientID"
          JOIN "professionals" pr ON pr."clinicID"       = a."clinicID"
                                 AND pr."professionalID" = a."professionalID"
          JOIN "services" s  ON s."clinicID"  = a."clinicID"
                            AND s."serviceID" = a."serviceID"
         WHERE a."startAt" >= ((%s::date)::timestamp     AT TIME ZONE c."timeZone")
           AND a."startAt" <  ((%s::date + 1)::timestamp AT TIME ZONE c."timeZone")
           AND (%s::uuid IS NULL OR a."professionalID" = %s::uuid)
         ORDER BY a."startAt", pr."fullName"
        """,
        (targetDate, targetDate, professionalID, professionalID),
    )
    return cursor.fetchall()


def listAppointmentsForPatient(
    connection: Connection, patientID: str
) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT a."appointmentID", a."professionalID", a."serviceID",
               a."startAt", a."endAt", a."appointmentStatusPK",
               a."cancellationReason", a."rescheduledToAppointmentID",
               pr."fullName" AS "professionalName",
               s."name"      AS "serviceName"
          FROM "appointments" a
          JOIN "professionals" pr ON pr."clinicID"       = a."clinicID"
                                 AND pr."professionalID" = a."professionalID"
          JOIN "services" s  ON s."clinicID"  = a."clinicID"
                            AND s."serviceID" = a."serviceID"
         WHERE a."patientID" = %s
         ORDER BY a."startAt" DESC
        """,
        (patientID,),
    )
    return cursor.fetchall()


def countAppointmentsByStatus(
    connection: Connection, fromDate: date, toDate: date
) -> list[dict]:
    cursor = connection.execute(
        """
        WITH "clinicWindow" AS (
            SELECT ((%s::date)::timestamp     AT TIME ZONE c."timeZone") AS "fromInstant",
                   ((%s::date + 1)::timestamp AT TIME ZONE c."timeZone") AS "toInstant"
              FROM "clinics" c
             WHERE c."clinicID" = "currentClinicID"()
        )
        SELECT st."appointmentStatusPK",
               st."name",
               count(a."appointmentID") AS "total"
          FROM "appointmentStatuses" st
          CROSS JOIN "clinicWindow" w
          LEFT JOIN "appointments" a
                 ON a."appointmentStatusPK" = st."appointmentStatusPK"
                AND a."startAt" >= w."fromInstant"
                AND a."startAt" <  w."toInstant"
         GROUP BY st."appointmentStatusPK", st."name"
         ORDER BY st."appointmentStatusPK"
        """,
        (fromDate, toDate),
    )
    return cursor.fetchall()
