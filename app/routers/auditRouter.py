from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.schemas.auditSchemas import (
    AuditChainVerificationResponse,
    AuditLogResponse,
)
from app.security.dependencies import CLINIC_ADMIN, requireRoles
from app.security.requestContext import RequestContext
from app.services import auditQueryService

router = APIRouter(tags=["Auditoria"])


@router.get(
    "/auditLogs",
    response_model=list[AuditLogResponse],
    summary="RF19 - Consultar la bitacora con filtros por usuario, paciente y fechas",
)
def listAuditLogs(
    request: Request,
    userID: UUID | None = Query(
        default=None, description="Filtra por el usuario que realizo la accion."
    ),
    patientID: UUID | None = Query(
        default=None, description="Filtra por el paciente afectado."
    ),
    fromDate: date | None = Query(default=None, description="Desde esta fecha."),
    toDate: date | None = Query(
        default=None, description="Hasta esta fecha, inclusive."
    ),
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return auditQueryService.listAuditLogs(
        request.app.state.pools,
        requestContext,
        userID=userID,
        patientID=patientID,
        fromDate=fromDate,
        toDate=toDate,
    )


@router.get(
    "/auditLogs/verification",
    response_model=AuditChainVerificationResponse,
    summary="Verificar la cadena de huellas de la bitacora",
)
def verifyAuditChain(
    request: Request,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return auditQueryService.verifyAuditChain(
        request.app.state.pools, requestContext
    )
