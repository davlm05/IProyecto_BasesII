from datetime import date

from app.db.connectionPools import ConnectionPoolRegistry
from app.db.transaction import openTenantTransaction
from app.repositories import auditRepository
from app.security.requestContext import RequestContext
from app.services import auditService

MAX_AUDIT_ROWS = 500


def listAuditLogs(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    userID: str | None,
    patientID: str | None,
    fromDate: date | None,
    toDate: date | None,
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        auditLogs = auditRepository.listAuditLogs(
            connection,
            userID=userID,
            patientID=patientID,
            fromDate=fromDate,
            toDate=toDate,
            maxRows=MAX_AUDIT_ROWS,
        )

        auditService.recordAction(
            connection,
            requestContext,
            auditActionPK=auditService.READ_AUDIT_LOG,
            entityType="auditLogs",
            entityID=None,
            patientID=patientID,
            metadata={
                "operation": "listAuditLogs",
                "filterUserID": userID,
                "filterPatientID": patientID,
                "returnedRows": len(auditLogs),
            },
        )

        return auditLogs


def verifyAuditChain(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        anomalies = auditRepository.verifyAuditChain(
            connection, requestContext.clinicID
        )

    return {
        "clinicID": requestContext.clinicID,
        "isIntact": len(anomalies) == 0,
        "anomalies": anomalies,
    }
