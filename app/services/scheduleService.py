from datetime import date, datetime, time

from app.db.connectionPools import ConnectionPoolRegistry
from app.db.transaction import openTenantTransaction
from app.errors import DomainError, FORBIDDEN_NOT_OWN_RESOURCE, RESOURCE_NOT_FOUND
from app.repositories import professionalRepository, scheduleRepository
from app.security.requestContext import RequestContext


def _rejectIfNotOwnProfessional(
    requestContext: RequestContext, professionalID: str
) -> None:
    """Un profesional solo opera sobre su propia agenda (matriz de permisos)."""
    if requestContext.isProfessional and str(requestContext.professionalID) != str(
        professionalID
    ):
        raise DomainError(
            FORBIDDEN_NOT_OWN_RESOURCE,
            "Un profesional solo gestiona su propio horario y sus propios bloqueos.",
        )


# =============================================================================
# RF5 - Horario de atencion semanal
# =============================================================================
def createWorkingHour(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    professionalID: str,
    weekday: int,
    startTimeLocal: time,
    endTimeLocal: time,
) -> dict:
    _rejectIfNotOwnProfessional(requestContext, professionalID)

    with openTenantTransaction(pools, requestContext) as connection:
        professional = professionalRepository.findProfessionalByID(
            connection, professionalID
        )
        if professional is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El profesional no existe en su clinica."
            )

        return scheduleRepository.insertWorkingHour(
            connection,
            clinicID=requestContext.clinicID,
            professionalID=professionalID,
            weekday=weekday,
            startTimeLocal=startTimeLocal,
            endTimeLocal=endTimeLocal,
        )

    # Al cambiar el horario cambia la disponibilidad futura: aqui habra que
    # invalidar la cache del profesional cuando exista el modulo 6.


def listWorkingHours(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    professionalID: str,
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return scheduleRepository.listWorkingHours(connection, professionalID)


def deleteWorkingHour(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    workingHourID: str,
) -> None:
    with openTenantTransaction(pools, requestContext) as connection:
        deletedRowCount = scheduleRepository.deleteWorkingHour(
            connection, workingHourID
        )

    if deletedRowCount == 0:
        raise DomainError(
            RESOURCE_NOT_FOUND, "El bloque de horario no existe o no es suyo."
        )


# =============================================================================
# RF6 - Bloqueos de agenda
# =============================================================================
def createScheduleBlock(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    professionalID: str,
    startAt: datetime,
    endAt: datetime,
    reason: str,
) -> dict:
    _rejectIfNotOwnProfessional(requestContext, professionalID)

    with openTenantTransaction(pools, requestContext) as connection:
        professional = professionalRepository.findProfessionalByID(
            connection, professionalID
        )
        if professional is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El profesional no existe en su clinica."
            )

        return scheduleRepository.insertScheduleBlock(
            connection,
            clinicID=requestContext.clinicID,
            professionalID=professionalID,
            startAt=startAt,
            endAt=endAt,
            reason=reason,
            userID=requestContext.userID,
        )

    # Invalidar la cache de disponibilidad del profesional para los dias que
    # abarca el bloqueo, cuando exista el modulo 6.


def listScheduleBlocks(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    professionalID: str | None,
    fromDate: date,
    toDate: date,
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return scheduleRepository.listScheduleBlocks(
            connection, professionalID, fromDate, toDate
        )


def listBlockConflicts(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    scheduleBlockID: str,
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        scheduleBlock = scheduleRepository.findScheduleBlockByID(
            connection, scheduleBlockID
        )
        if scheduleBlock is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El bloqueo no existe en su clinica."
            )

        return scheduleRepository.listAppointmentsConflictingWithBlock(
            connection, scheduleBlockID
        )


def deleteScheduleBlock(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    scheduleBlockID: str,
) -> None:
    with openTenantTransaction(pools, requestContext) as connection:
        scheduleBlock = scheduleRepository.findScheduleBlockByID(
            connection, scheduleBlockID
        )
        if scheduleBlock is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El bloqueo no existe en su clinica."
            )

        _rejectIfNotOwnProfessional(
            requestContext, str(scheduleBlock["professionalID"])
        )

        deletedRowCount = scheduleRepository.deleteScheduleBlock(
            connection, scheduleBlockID
        )

    if deletedRowCount == 0:
        raise DomainError(RESOURCE_NOT_FOUND, "El bloqueo no existe o no es suyo.")
