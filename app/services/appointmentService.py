from datetime import date, datetime, timezone
import psycopg
from psycopg import Connection

from app.config import ApplicationConfig
from app.db.connectionPools import ConnectionPoolRegistry
from app.db.transaction import openTenantTransaction, runWithSerializationRetry
from app.errors import (
    APPOINTMENT_NOT_RESERVED,
    DomainError,
    FORBIDDEN_NOT_OWN_RESOURCE,
    OUTCOME_BEFORE_START,
    RESCHEDULE_OVERLAPS_ORIGIN,
    RESOURCE_NOT_FOUND,
)
from app.repositories import appointmentRepository
from app.security.requestContext import RequestContext


# =============================================================================
# RF9 - Reservar
# =============================================================================
def reserveAppointment(
    pools: ConnectionPoolRegistry,
    config: ApplicationConfig,
    requestContext: RequestContext,
    patientID: str,
    professionalID: str,
    serviceID: str,
    startAt: datetime,
) -> dict:
    def executeReservation() -> dict:
        with openTenantTransaction(pools, requestContext) as connection:
            return appointmentRepository.insertAppointment(
                connection,
                clinicID=requestContext.clinicID,
                patientID=patientID,
                professionalID=professionalID,
                serviceID=serviceID,
                startAt=startAt,
                createdByUserID=requestContext.userID,
            )

    createdAppointment = runWithSerializationRetry(
        config.reservationMaxRetries, executeReservation
    )

    # AQUI se invalidara la cache de disponibilidad cuando se implemente el
    # modulo 6, y debe hacerse DESPUES del commit: si se invalidara antes y la
    # transaccion fallara, se habria tirado una entrada valida. Invalidar
    # despues tiene el riesgo opuesto -que el borrado falle y quede una entrada
    # vieja- pero ese lo corrige el TTL, mientras que servir disponibilidad
    # inventada no lo corrige nada.

    return createdAppointment


# =============================================================================
# RF10 - Reprogramar
# =============================================================================
def rescheduleAppointment(
    pools: ConnectionPoolRegistry,
    config: ApplicationConfig,
    requestContext: RequestContext,
    appointmentID: str,
    newStartAt: datetime,
    newProfessionalID: str | None,
) -> dict:
    def executeReschedule() -> dict:
        with openTenantTransaction(pools, requestContext) as connection:
            originalAppointment = appointmentRepository.findAppointmentByID(
                connection, appointmentID
            )
            if originalAppointment is None:
                raise DomainError(
                    RESOURCE_NOT_FOUND, "La cita no existe en su clinica."
                )
            if originalAppointment["appointmentStatusPK"] != "reserved":
                raise DomainError(
                    APPOINTMENT_NOT_RESERVED,
                    f"Solo se reprograma una cita reservada, y esta esta en "
                    f"estado '{originalAppointment['appointmentStatusPK']}'.",
                )

            targetProfessionalID = newProfessionalID or str(
                originalAppointment["professionalID"]
            )

            try:
                newAppointment = appointmentRepository.insertAppointment(
                    connection,
                    clinicID=requestContext.clinicID,
                    patientID=str(originalAppointment["patientID"]),
                    professionalID=targetProfessionalID,
                    serviceID=str(originalAppointment["serviceID"]),
                    startAt=newStartAt,
                    createdByUserID=requestContext.userID,
                )
            except psycopg.errors.ExclusionViolation:
                raise DomainError(
                    RESCHEDULE_OVERLAPS_ORIGIN,
                    "El espacio destino esta ocupado. Si se solapa con el de la "
                    "cita original, cancele y reserve de nuevo.",
                )

            closedOriginalAppointment = appointmentRepository.markAppointmentAsRescheduled(
                connection,
                appointmentID=appointmentID,
                newAppointmentID=str(newAppointment["appointmentID"]),
            )

            return {
                "originalAppointment": closedOriginalAppointment,
                "newAppointment": newAppointment,
            }

    rescheduleResult = runWithSerializationRetry(
        config.reservationMaxRetries, executeReschedule
    )

    # Invalidar la cache de los DOS espacios (el liberado y el tomado) cuando
    # exista el modulo 6. I7 exige que el espacio liberado se vea libre en la
    # siguiente consulta.

    return rescheduleResult


# =============================================================================
# RF11 - Cancelar
# =============================================================================
def cancelAppointment(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    appointmentID: str,
    cancellationReason: str,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        existingAppointment = appointmentRepository.findAppointmentByID(
            connection, appointmentID
        )
        if existingAppointment is None:
            raise DomainError(RESOURCE_NOT_FOUND, "La cita no existe en su clinica.")

        if existingAppointment["appointmentStatusPK"] != "reserved":
            raise DomainError(
                APPOINTMENT_NOT_RESERVED,
                f"Solo se cancela una cita reservada, y esta esta en estado "
                f"'{existingAppointment['appointmentStatusPK']}'.",
            )

        cancelledAppointment = appointmentRepository.cancelAppointment(
            connection,
            appointmentID=appointmentID,
            cancelledByUserID=requestContext.userID,
            cancellationReason=cancellationReason,
        )

    # I7: el espacio queda libre en el mismo instante del commit, porque el
    # estado 'cancelled' sale del filtro de las consultas de disponibilidad.
    # Cuando exista la cache, hay que invalidar aqui o I8 se rompe.

    return cancelledAppointment


# =============================================================================
# RF12 - Registrar el desenlace
# =============================================================================
def recordAppointmentOutcome(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    appointmentID: str,
    appointmentStatusPK: str,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        existingAppointment = appointmentRepository.findAppointmentByID(
            connection, appointmentID
        )
        if existingAppointment is None:
            raise DomainError(RESOURCE_NOT_FOUND, "La cita no existe en su clinica.")

        if requestContext.isProfessional and str(
            existingAppointment["professionalID"]
        ) != str(requestContext.professionalID):
            raise DomainError(
                FORBIDDEN_NOT_OWN_RESOURCE,
                "Un profesional solo registra el desenlace de sus propias citas.",
            )

        if existingAppointment["appointmentStatusPK"] != "reserved":
            raise DomainError(
                APPOINTMENT_NOT_RESERVED,
                f"Solo se registra el desenlace de una cita reservada, y esta "
                f"esta en estado '{existingAppointment['appointmentStatusPK']}'.",
            )

        if datetime.now(timezone.utc) < existingAppointment["startAt"]:
            raise DomainError(
                OUTCOME_BEFORE_START,
                "El desenlace solo se registra una vez pasada la hora de inicio "
                "de la cita.",
            )

        return appointmentRepository.recordAppointmentOutcome(
            connection,
            appointmentID=appointmentID,
            appointmentStatusPK=appointmentStatusPK,
            outcomeRecordedByUserID=requestContext.userID,
        )


# =============================================================================
# Consultas
# =============================================================================
def getAppointment(
    pools: ConnectionPoolRegistry, requestContext: RequestContext, appointmentID: str
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        appointment = appointmentRepository.findAppointmentByID(
            connection, appointmentID
        )

    if appointment is None:
        raise DomainError(RESOURCE_NOT_FOUND, "La cita no existe en su clinica.")
    return appointment


def getDayAgenda(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    targetDate: date,
    professionalID: str | None,
) -> list[dict]:
    effectiveProfessionalID = professionalID
    if requestContext.isProfessional:
        effectiveProfessionalID = requestContext.professionalID

    with openTenantTransaction(pools, requestContext) as connection:
        return appointmentRepository.listAppointmentsForDay(
            connection, targetDate, effectiveProfessionalID
        )


def countAppointmentsByStatus(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    fromDate: date,
    toDate: date,
) -> list[dict]:
    """RF21: cuenta las citas por estado dentro de un rango de fechas."""
    with openTenantTransaction(pools, requestContext) as connection:
        return appointmentRepository.countAppointmentsByStatus(
            connection, fromDate, toDate
        )
