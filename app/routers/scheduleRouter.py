from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.schemas.scheduleSchemas import (
    ConflictingAppointmentResponse,
    CreateScheduleBlockRequest,
    CreateWorkingHourRequest,
    ProfessionalAvailabilityResponse,
    ScheduleBlockResponse,
    ServiceAvailabilityResponse,
    WorkingHourResponse,
)
from app.security.dependencies import (
    CLINIC_ADMIN,
    PROFESSIONAL,
    RECEPTION,
    requireRoles,
)
from app.security.requestContext import RequestContext
from app.services import availabilityService, scheduleService

router = APIRouter(tags=["Agenda y disponibilidad"])

# =============================================================================
# RF5 - Horario de atencion semanal
# =============================================================================
@router.post(
    "/professionals/{professionalID}/workingHours",
    status_code=status.HTTP_201_CREATED,
    response_model=WorkingHourResponse,
    summary="RF5 · Anadir un bloque al horario semanal de un profesional",
)
def createWorkingHour(
    request: Request,
    professionalID: UUID,
    createWorkingHourRequest: CreateWorkingHourRequest,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, PROFESSIONAL)
    ),
):
    return scheduleService.createWorkingHour(
        request.app.state.pools,
        requestContext,
        professionalID=professionalID,
        weekday=createWorkingHourRequest.weekday,
        startTimeLocal=createWorkingHourRequest.startTimeLocal,
        endTimeLocal=createWorkingHourRequest.endTimeLocal,
    )


@router.get(
    "/professionals/{professionalID}/workingHours",
    response_model=list[WorkingHourResponse],
    summary="RF5 · Consultar el horario semanal de un profesional",
)
def listWorkingHours(
    request: Request,
    professionalID: UUID,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return scheduleService.listWorkingHours(
        request.app.state.pools, requestContext, professionalID
    )


@router.delete(
    "/workingHours/{workingHourID}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="RF5 · Retirar un bloque del horario semanal",
)
def deleteWorkingHour(
    request: Request,
    workingHourID: UUID,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, PROFESSIONAL)
    ),
):
    scheduleService.deleteWorkingHour(
        request.app.state.pools, requestContext, workingHourID
    )


# =============================================================================
# RF6 - Bloqueos de agenda
# =============================================================================
@router.post(
    "/scheduleBlocks",
    status_code=status.HTTP_201_CREATED,
    response_model=ScheduleBlockResponse,
    summary="RF6 · Registrar un bloqueo de agenda por vacaciones o permiso",
)
def createScheduleBlock(
    request: Request,
    createScheduleBlockRequest: CreateScheduleBlockRequest,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, PROFESSIONAL)
    ),
):
    return scheduleService.createScheduleBlock(
        request.app.state.pools,
        requestContext,
        professionalID=createScheduleBlockRequest.professionalID,
        startAt=createScheduleBlockRequest.startAt,
        endAt=createScheduleBlockRequest.endAt,
        reason=createScheduleBlockRequest.reason,
    )


@router.get(
    "/scheduleBlocks",
    response_model=list[ScheduleBlockResponse],
    summary="RF6 · Listar los bloqueos de agenda de un rango de fechas",
)
def listScheduleBlocks(
    request: Request,
    fromDate: date = Query(description="Primer dia del rango, inclusive."),
    toDate: date = Query(description="Ultimo dia del rango, inclusive."),
    professionalID: UUID | None = Query(
        default=None, description="Si se omite, devuelve los de toda la clinica."
    ),
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return scheduleService.listScheduleBlocks(
        request.app.state.pools, requestContext, professionalID, fromDate, toDate
    )


@router.get(
    "/scheduleBlocks/{scheduleBlockID}/conflicts",
    response_model=list[ConflictingAppointmentResponse],
    summary="RF6 · Listar las citas vigentes que caen dentro de un bloqueo",
)
def listBlockConflicts(
    request: Request,
    scheduleBlockID: UUID,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return scheduleService.listBlockConflicts(
        request.app.state.pools, requestContext, scheduleBlockID
    )


@router.delete(
    "/scheduleBlocks/{scheduleBlockID}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="RF6 · Levantar un bloqueo de agenda",
)
def deleteScheduleBlock(
    request: Request,
    scheduleBlockID: UUID,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, PROFESSIONAL)
    ),
):
    scheduleService.deleteScheduleBlock(
        request.app.state.pools, requestContext, scheduleBlockID
    )


# =============================================================================
# RF7 y RF8 - Disponibilidad
# =============================================================================
@router.get(
    "/availability/professional",
    response_model=ProfessionalAvailabilityResponse,
    summary="RF7 · Calcular los espacios disponibles de un profesional en una fecha",
)
def getProfessionalAvailability(
    request: Request,
    professionalID: UUID = Query(),
    serviceID: UUID = Query(
        description="Determina la duracion del espacio que se busca (I4)."
    ),
    targetDate: date = Query(
        description="Fecha a consultar, interpretada en la zona de la clinica."
    ),
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return availabilityService.getProfessionalAvailability(
        request.app.state.pools,
        requestContext,
        professionalID=professionalID,
        serviceID=serviceID,
        targetDate=targetDate,
    )


@router.get(
    "/availability/service",
    response_model=ServiceAvailabilityResponse,
    summary="RF8 · Consultar disponibilidad por servicio en un rango de fechas",
)
def getServiceAvailability(
    request: Request,
    serviceID: UUID = Query(),
    fromDate: date = Query(),
    toDate: date = Query(),
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    """
    RF8: devuelve los profesionales que tienen espacio y cuales son.

    Solo se incluyen las combinaciones de profesional y dia con al menos un
    espacio libre. El rango esta topado a 31 dias.
    """
    return availabilityService.getServiceAvailability(
        request.app.state.pools,
        requestContext,
        serviceID=serviceID,
        fromDate=fromDate,
        toDate=toDate,
    )
