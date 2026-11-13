from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status

from app.schemas.appointmentSchemas import PatientAppointmentHistoryItemResponse
from app.schemas.patientSchemas import (
    CreatePatientRequest,
    PatientResponse,
    UpdatePatientRequest,
)
from app.security.dependencies import (
    CLINIC_ADMIN,
    PROFESSIONAL,
    RECEPTION,
    requireRoles,
)
from app.security.requestContext import RequestContext
from app.services import patientService

router = APIRouter(tags=["Pacientes"])

@router.post(
    "/patients",
    status_code=status.HTTP_201_CREATED,
    response_model=PatientResponse,
    summary="RF14 - Registrar un paciente de la clinica",
)
def createPatient(
    request: Request,
    createPatientRequest: CreatePatientRequest,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION)
    ),
):
    return patientService.createPatient(
        request.app.state.pools,
        requestContext,
        nationalID=createPatientRequest.nationalID,
        firstName=createPatientRequest.firstName,
        lastName=createPatientRequest.lastName,
        birthDate=createPatientRequest.birthDate,
        phone=createPatientRequest.phone,
        email=createPatientRequest.email,
    )


@router.get(
    "/patients",
    response_model=list[PatientResponse],
    summary="RF14 - Listar o buscar pacientes de la clinica",
)
def listPatients(
    request: Request,
    searchText: str | None = Query(
        default=None,
        description="Busca por el inicio del apellido o del nombre. Si se "
        "omite, devuelve los primeros 200 pacientes activos.",
    ),
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return patientService.listPatients(
        request.app.state.pools, requestContext, searchText
    )


@router.get(
    "/patients/{patientID}",
    response_model=PatientResponse,
    summary="RF14 - Consultar la ficha de un paciente",
)
def getPatient(
    request: Request,
    patientID: UUID,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return patientService.getPatient(
        request.app.state.pools, requestContext, patientID
    )


@router.put(
    "/patients/{patientID}",
    response_model=PatientResponse,
    summary="RF14 - Actualizar un paciente",
)
def updatePatient(
    request: Request,
    patientID: UUID,
    updatePatientRequest: UpdatePatientRequest,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION)
    ),
):
    return patientService.updatePatient(
        request.app.state.pools,
        requestContext,
        patientID=patientID,
        firstName=updatePatientRequest.firstName,
        lastName=updatePatientRequest.lastName,
        birthDate=updatePatientRequest.birthDate,
        phone=updatePatientRequest.phone,
        email=updatePatientRequest.email,
    )


@router.get(
    "/patients/{patientID}/appointments",
    response_model=list[PatientAppointmentHistoryItemResponse],
    summary="RF16 - Consultar el historial de citas de un paciente",
)
def getPatientAppointmentHistory(
    request: Request,
    patientID: UUID,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return patientService.getPatientAppointmentHistory(
        request.app.state.pools, requestContext, patientID
    )
