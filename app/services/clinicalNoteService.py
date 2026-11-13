from app.db.connectionPools import ConnectionPoolRegistry
from app.db.transaction import openTenantTransaction
from app.errors import DomainError, FORBIDDEN_NOT_OWN_RESOURCE, RESOURCE_NOT_FOUND
from app.repositories import appointmentRepository, clinicalNoteRepository
from app.security.requestContext import RequestContext
from app.services import auditService


def writeClinicalNote(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    appointmentID: str,
    content: str,
) -> dict:

    with openTenantTransaction(pools, requestContext) as connection:
        appointment = appointmentRepository.findAppointmentByID(
            connection, appointmentID
        )
        if appointment is None:
            raise DomainError(RESOURCE_NOT_FOUND, "La cita no existe en su clinica.")

        if str(appointment["professionalID"]) != str(requestContext.professionalID):
            raise DomainError(
                FORBIDDEN_NOT_OWN_RESOURCE,
                "La nota clinica solo la escribe el profesional que atendio la cita.",
            )

        existingNote = clinicalNoteRepository.findClinicalNoteByAppointment(
            connection, appointmentID
        )

        if existingNote is None:
            savedNote = clinicalNoteRepository.insertClinicalNote(
                connection,
                clinicID=requestContext.clinicID,
                appointmentID=appointmentID,
                professionalID=requestContext.professionalID,
                content=content,
            )
            operationName = "createClinicalNote"
        else:
            savedNote = clinicalNoteRepository.updateClinicalNote(
                connection, appointmentID, content
            )
            operationName = "updateClinicalNote"

        auditService.recordAction(
            connection,
            requestContext,
            auditActionPK=auditService.WRITE_CLINICAL_NOTE,
            entityType="clinicalNotes",
            entityID=str(savedNote["clinicalNoteID"]),
            patientID=str(appointment["patientID"]),
            metadata={
                "operation": operationName,
                "appointmentID": appointmentID,
                "contentLength": len(content),
            },
        )

        return savedNote


def getClinicalNote(
    pools: ConnectionPoolRegistry, requestContext: RequestContext, appointmentID: str
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        clinicalNote = clinicalNoteRepository.findClinicalNoteByAppointment(
            connection, appointmentID
        )
        if clinicalNote is None:
            raise DomainError(
                RESOURCE_NOT_FOUND,
                "La cita no tiene nota clinica, o la nota no es suya.",
            )

        appointment = appointmentRepository.findAppointmentByID(
            connection, appointmentID
        )

        auditService.recordAction(
            connection,
            requestContext,
            auditActionPK=auditService.READ_CLINICAL_NOTE,
            entityType="clinicalNotes",
            entityID=str(clinicalNote["clinicalNoteID"]),
            patientID=str(appointment["patientID"]) if appointment else None,
            metadata={"operation": "getClinicalNote", "appointmentID": appointmentID},
        )

        return clinicalNote
