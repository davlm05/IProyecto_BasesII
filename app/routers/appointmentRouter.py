from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.schemas.appointmentSchemas import (
    AppointmentResponse,
    AppointmentStatusCountResponse,
    CancelAppointmentRequest,
    ClinicalNoteResponse,
    CreateAppointmentRequest,
    DayAgendaItemResponse,
    RecordOutcomeRequest,
    RescheduleAppointmentRequest,
    RescheduleAppointmentResponse,
    WriteClinicalNoteRequest,
)
from app.security.dependencies import (
    CLINIC_ADMIN,
    PROFESSIONAL,
    RECEPTION,
    requireRoles,
)
from app.security.requestContext import RequestContext
from app.services import appointmentService, clinicalNoteService

router = APIRouter(tags=["Citas"])


# =============================================================================
# RF9 - Reservar
# =============================================================================
@router.post(
    "/appointments",
    status_code=status.HTTP_201_CREATED,
    response_model=AppointmentResponse,
    summary="RF9 - Reservar una cita",
    responses={
        201: {"description": "Reserva concedida."},
        409: {
            "description": "El espacio ya esta tomado (errorCode slotTaken), o "
            "hubo un conflicto de concurrencia que no se resolvio con los "
            "reintentos."
        },
        422: {
            "description": "Solicitud invalida: fuera del horario del "
            "profesional, dentro de un bloqueo, profesional no habilitado para "
            "el servicio, o un recurso de otra clinica."
        },
    },
)
def reserveAppointment(
    request: Request,
    createAppointmentRequest: CreateAppointmentRequest,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION)
    ),
):
    return appointmentService.reserveAppointment(
        request.app.state.pools,
        request.app.state.config,
        requestContext,
        patientID=createAppointmentRequest.patientID,
        professionalID=createAppointmentRequest.professionalID,
        serviceID=createAppointmentRequest.serviceID,
        startAt=createAppointmentRequest.startAt,
    )


# =============================================================================
# RF10 - Reprogramar
# =============================================================================
@router.post(
    "/appointments/{appointmentID}/reschedule",
    response_model=RescheduleAppointmentResponse,
    summary="RF10 - Reprogramar una cita hacia otro espacio",
    responses={
        200: {"description": "Reprogramada: devuelve la cita cerrada y la nueva."},
        409: {
            "description": "El espacio destino esta ocupado, o la cita ya tiene "
            "un estado final."
        },
    },
)
def rescheduleAppointment(
    request: Request,
    appointmentID: UUID,
    rescheduleAppointmentRequest: RescheduleAppointmentRequest,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION)
    ),
):
    return appointmentService.rescheduleAppointment(
        request.app.state.pools,
        request.app.state.config,
        requestContext,
        appointmentID=appointmentID,
        newStartAt=rescheduleAppointmentRequest.startAt,
        newProfessionalID=rescheduleAppointmentRequest.professionalID,
    )


# =============================================================================
# RF11 - Cancelar
# =============================================================================
@router.post(
    "/appointments/{appointmentID}/cancel",
    response_model=AppointmentResponse,
    summary="RF11 - Cancelar una cita",
)
def cancelAppointment(
    request: Request,
    appointmentID: UUID,
    cancelAppointmentRequest: CancelAppointmentRequest,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION)
    ),
):
    return appointmentService.cancelAppointment(
        request.app.state.pools,
        requestContext,
        appointmentID=appointmentID,
        cancellationReason=cancelAppointmentRequest.cancellationReason,
    )


# =============================================================================
# RF12 - Desenlace
# =============================================================================
@router.post(
    "/appointments/{appointmentID}/outcome",
    response_model=AppointmentResponse,
    summary="RF12 - Registrar el desenlace de una cita (atendida o ausencia)",
)
def recordAppointmentOutcome(
    request: Request,
    appointmentID: UUID,
    recordOutcomeRequest: RecordOutcomeRequest,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return appointmentService.recordAppointmentOutcome(
        request.app.state.pools,
        requestContext,
        appointmentID=appointmentID,
        appointmentStatusPK=recordOutcomeRequest.appointmentStatusPK,
    )


# =============================================================================
# RF20 y RF21 - Operacion diaria
# =============================================================================
@router.get(
    "/appointments/day",
    response_model=list[DayAgendaItemResponse],
    summary="RF20 - Mostrar la agenda del dia",
)
def getDayAgenda(
    request: Request,
    targetDate: date = Query(
        description="Dia a mostrar, en la zona horaria de la clinica."
    ),
    professionalID: UUID | None = Query(
        default=None,
        description="Si se omite, devuelve la agenda de toda la clinica. Un "
        "profesional recibe siempre solo la suya.",
    ),
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return appointmentService.getDayAgenda(
        request.app.state.pools, requestContext, targetDate, professionalID
    )


@router.get(
    "/appointments/countsByStatus",
    response_model=list[AppointmentStatusCountResponse],
    summary="RF21 - Contar las citas por estado en un rango de fechas",
)
def countAppointmentsByStatus(
    request: Request,
    fromDate: date = Query(),
    toDate: date = Query(),
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION)
    ),
):
    return appointmentService.countAppointmentsByStatus(
        request.app.state.pools, requestContext, fromDate, toDate
    )


# =============================================================================
# Consulta de una cita
# =============================================================================
@router.get(
    "/appointments/{appointmentID}",
    response_model=AppointmentResponse,
    summary="Consultar una cita por su identificador",
)
def getAppointment(
    request: Request,
    appointmentID: UUID,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return appointmentService.getAppointment(
        request.app.state.pools, requestContext, appointmentID
    )


# =============================================================================
# RF15 - Nota clinica. Solo el profesional, y solo de sus citas.
# =============================================================================
@router.put(
    "/appointments/{appointmentID}/clinicalNote",
    response_model=ClinicalNoteResponse,
    summary="RF15 - Escribir o corregir la nota clinica de una cita atendida",
)
def writeClinicalNote(
    request: Request,
    appointmentID: UUID,
    writeClinicalNoteRequest: WriteClinicalNoteRequest,
    requestContext: RequestContext = Depends(requireRoles(PROFESSIONAL)),
):
    return clinicalNoteService.writeClinicalNote(
        request.app.state.pools,
        requestContext,
        appointmentID=appointmentID,
        content=writeClinicalNoteRequest.content,
    )


@router.get(
    "/appointments/{appointmentID}/clinicalNote",
    response_model=ClinicalNoteResponse,
    summary="RF15 - Leer la nota clinica de una cita propia",
)
def getClinicalNote(
    request: Request,
    appointmentID: UUID,
    requestContext: RequestContext = Depends(requireRoles(PROFESSIONAL)),
):
    return clinicalNoteService.getClinicalNote(
        request.app.state.pools, requestContext, appointmentID
    )
