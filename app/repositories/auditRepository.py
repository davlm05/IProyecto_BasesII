import json
from datetime import date
from psycopg import Connection

def insertAuditLog(
    connection: Connection,
    clinicID: str,
    userID: str,
    rolePK: str,
    auditActionPK: str,
    entityType: str,
    entityID: str | None,
    patientID: str | None,
    requestID: str,
    metadata: dict,
) -> None:
    connection.execute(
        """
        INSERT INTO "auditLogs"
               ("clinicID", "userID", "rolePK", "auditActionPK",
                "entityType", "entityID", "patientID", "requestID", "metadata")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        (
            clinicID,
            userID,
            rolePK,
            auditActionPK,
            entityType,
            entityID,
            patientID,
            requestID,
            json.dumps(metadata, default=str),
        ),
    )


def listAuditLogs(
    connection: Connection,
    userID: str | None,
    patientID: str | None,
    fromDate: date | None,
    toDate: date | None,
    maxRows: int,
) -> list[dict]:
    cursor = connection.execute(
        """
        WITH "clinicWindow" AS (
            SELECT CASE WHEN %s::date IS NULL THEN NULL
                        ELSE ((%s::date)::timestamp AT TIME ZONE c."timeZone") END
                   AS "fromInstant",
                   CASE WHEN %s::date IS NULL THEN NULL
                        ELSE ((%s::date + 1)::timestamp AT TIME ZONE c."timeZone") END
                   AS "toInstant"
              FROM "clinics" c
             WHERE c."clinicID" = "currentClinicID"()
        )
        SELECT a."auditLogPK", a."clinicID", a."sequenceNo", a."occurredAt",
               a."userID", a."rolePK", a."auditActionPK", a."entityType",
               a."entityID", a."patientID", a."requestID", a."metadata",
               encode(a."previousHash", 'hex') AS "previousHashHex",
               encode(a."rowHash",      'hex') AS "rowHashHex"
          FROM "auditLogs" a
          CROSS JOIN "clinicWindow" w
         WHERE (%s::uuid IS NULL OR a."userID"    = %s::uuid)
           AND (%s::uuid IS NULL OR a."patientID" = %s::uuid)
           AND (w."fromInstant" IS NULL OR a."occurredAt" >= w."fromInstant")
           AND (w."toInstant"   IS NULL OR a."occurredAt" <  w."toInstant")
         ORDER BY a."sequenceNo" DESC
         LIMIT %s
        """,
        (
            fromDate, fromDate,
            toDate, toDate,
            userID, userID,
            patientID, patientID,
            maxRows,
        ),
    )
    return cursor.fetchall()


def verifyAuditChain(connection: Connection, clinicID: str) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT "sequenceNo", "auditLogPK", "anomaly", "detail"
          FROM "verifyAuditChain"(%s)
         ORDER BY "sequenceNo"
        """,
        (clinicID,),
    )
    return cursor.fetchall()
