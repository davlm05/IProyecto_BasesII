from psycopg import Connection

from app.repositories import auditRepository
from app.security.requestContext import RequestContext

READ_CLINICAL_NOTE = "readClinicalNote"
WRITE_CLINICAL_NOTE = "writeClinicalNote"
READ_PATIENT_CONTACT = "readPatientContact"
WRITE_PATIENT_CONTACT = "writePatientContact"
READ_PATIENT_HISTORY = "readPatientHistory"
READ_AUDIT_LOG = "readAuditLog"


def recordAction(
    connection: Connection,
    requestContext: RequestContext,
    auditActionPK: str,
    entityType: str,
    entityID: str | None = None,
    patientID: str | None = None,
    metadata: dict | None = None,
) -> None:
    if requestContext.clinicID is None:
        return

    auditRepository.insertAuditLog(
        connection=connection,
        clinicID=requestContext.clinicID,
        userID=requestContext.userID,
        rolePK=requestContext.rolePK,
        auditActionPK=auditActionPK,
        entityType=entityType,
        entityID=entityID,
        patientID=patientID,
        requestID=requestContext.requestID,
        metadata=metadata or {},
    )
