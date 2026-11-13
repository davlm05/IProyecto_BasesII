from psycopg import Connection

from app.db.connectionPools import ConnectionPoolRegistry
from app.db.transaction import openTenantTransaction
from app.errors import DomainError, RESOURCE_NOT_FOUND
from app.repositories import appointmentRepository, patientRepository
from app.security.requestContext import RequestContext
from app.services import auditService
from datetime import date


def createPatient(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    nationalID: str,
    firstName: str,
    lastName: str,
    birthDate: date,
    phone: str | None,
    email: str | None,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        createdPatient = patientRepository.insertPatient(
            connection,
            clinicID=requestContext.clinicID,
            nationalID=nationalID,
            firstName=firstName,
            lastName=lastName,
            birthDate=birthDate,
            phone=phone,
            email=email,
        )

        patientID = str(createdPatient["patientID"])
        auditService.recordAction(
            connection,
            requestContext,
            auditActionPK=auditService.WRITE_PATIENT_CONTACT,
            entityType="patients",
            entityID=patientID,
            patientID=patientID,
            metadata={"operation": "createPatient"},
        )

        return createdPatient


def listPatients(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    searchText: str | None,
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return patientRepository.listPatients(connection, searchText)


def getPatient(
    pools: ConnectionPoolRegistry, requestContext: RequestContext, patientID: str
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        patient = patientRepository.findPatientByID(connection, patientID)

        if patient is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El paciente no existe en su clinica."
            )

        auditService.recordAction(
            connection,
            requestContext,
            auditActionPK=auditService.READ_PATIENT_CONTACT,
            entityType="patients",
            entityID=patientID,
            patientID=patientID,
            metadata={"operation": "getPatient"},
        )

        return patient


def updatePatient(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    patientID: str,
    firstName: str,
    lastName: str,
    birthDate: date,
    phone: str | None,
    email: str | None,
) -> dict:
    """RF14: actualiza un paciente. Auditado como escritura de contacto."""
    with openTenantTransaction(pools, requestContext) as connection:
        updatedPatient = patientRepository.updatePatient(
            connection,
            patientID=patientID,
            firstName=firstName,
            lastName=lastName,
            birthDate=birthDate,
            phone=phone,
            email=email,
        )

        if updatedPatient is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El paciente no existe en su clinica."
            )

        auditService.recordAction(
            connection,
            requestContext,
            auditActionPK=auditService.WRITE_PATIENT_CONTACT,
            entityType="patients",
            entityID=patientID,
            patientID=patientID,
            metadata={"operation": "updatePatient"},
        )

        return updatedPatient


def getPatientAppointmentHistory(
    pools: ConnectionPoolRegistry, requestContext: RequestContext, patientID: str
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        patient = patientRepository.findPatientByID(connection, patientID)
        if patient is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El paciente no existe en su clinica."
            )

        appointmentHistory = appointmentRepository.listAppointmentsForPatient(
            connection, patientID
        )

        auditService.recordAction(
            connection,
            requestContext,
            auditActionPK=auditService.READ_PATIENT_HISTORY,
            entityType="appointments",
            entityID=None,
            patientID=patientID,
            metadata={
                "operation": "getPatientAppointmentHistory",
                "appointmentCount": len(appointmentHistory),
            },
        )

        return appointmentHistory
