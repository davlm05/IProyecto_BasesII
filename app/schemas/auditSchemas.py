from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class AuditLogResponse(BaseModel):
    auditLogPK: int
    clinicID: UUID
    sequenceNo: int
    occurredAt: datetime
    userID: UUID | None = None
    rolePK: str
    auditActionPK: str
    entityType: str
    entityID: UUID | None = None
    patientID: UUID | None = None
    requestID: UUID | None = None
    metadata: dict
    previousHashHex: str
    rowHashHex: str

class AuditChainAnomalyResponse(BaseModel):
    sequenceNo: int | None = None
    auditLogPK: int | None = None
    anomaly: str
    detail: str

class AuditChainVerificationResponse(BaseModel):
    clinicID: UUID
    isIntact: bool
    anomalies: list[AuditChainAnomalyResponse]
