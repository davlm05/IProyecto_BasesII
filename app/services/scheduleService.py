from datetime import date, datetime, time

from app.cache import redisTransactions
from app.cache.redisClient import RedisClientRegistry
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
    redisRegistry: RedisClientRegistry,
    requestContext: RequestContext,
    professionalID: str,
    weekday: int,
    startTimeLocal: time,
    endTimeLocal: time,
) -> dict:
    client = redisRegistry.getClient()
    
    _rejectIfNotOwnProfessional(requestContext, professionalID)

    with openTenantTransaction(pools, requestContext) as connection:
        professional = professionalRepository.findProfessionalByID(
            connection, professionalID
        )
        if professional is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El profesional no existe en su clinica."
            )

        resultado = scheduleRepository.insertWorkingHour(
            connection,
            clinicID=requestContext.clinicID,
            professionalID=professionalID,
            weekday=weekday,
            startTimeLocal=startTimeLocal,
            endTimeLocal=endTimeLocal,
        )
    # Se invalidan los datos de la cache para asegurar consistencia.
    redisTransactions.deleteKey(client, professionalID)
    return resultado


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
    redisRegistry: RedisClientRegistry,
) -> None:
    with openTenantTransaction(pools, requestContext) as connection:
        professionalID = scheduleRepository.deleteWorkingHour(
            connection, workingHourID
        )

        if professionalID is None:
            raise DomainError(
                RESOURCE_NOT_FOUND,
                "El bloque de horario no existe o no es suyo.",
            )

    # Invalidar después de confirmar la eliminación.
    redisTransactions.deleteKey(
        redisRegistry.getClient(),
        professionalID,
    )

# =============================================================================
# RF6 - Bloqueos de agenda
# =============================================================================
def createScheduleBlock(
    pools: ConnectionPoolRegistry,
    redisRegistry: RedisClientRegistry,
    requestContext: RequestContext,
    professionalID: str,
    startAt: datetime,
    endAt: datetime,
    reason: str,
) -> dict:
    client = redisRegistry.getClient()
    _rejectIfNotOwnProfessional(requestContext, professionalID)

    with openTenantTransaction(pools, requestContext) as connection:
        professional = professionalRepository.findProfessionalByID(
            connection, professionalID
        )
        if professional is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El profesional no existe en su clinica."
            )

        resultado = scheduleRepository.insertScheduleBlock(
            connection,
            clinicID=requestContext.clinicID,
            professionalID=professionalID,
            startAt=startAt,
            endAt=endAt,
            reason=reason,
            userID=requestContext.userID,
        )

    # Se invalidan los datos de la cache para asegurar consistencia.
    redisTransactions.deleteKey(client, professionalID)
    return resultado


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
    redisRegistry: RedisClientRegistry,
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
    redisTransactions.deleteKey(
        redisRegistry.getClient(),
        str(scheduleBlock["professionalID"]),
    )
