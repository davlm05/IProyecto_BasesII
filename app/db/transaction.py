import logging
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

import psycopg
from psycopg import Connection

from app.db.connectionPools import ConnectionPoolRegistry
from app.security.requestContext import RequestContext

logger = logging.getLogger(__name__)

ResultType = TypeVar("ResultType")

def applyTenantContext(connection: Connection, requestContext: RequestContext) -> None:
    connection.execute(
        """
        SELECT set_config('app.currentClinicID',       %s, true),
               set_config('app.currentRoleCode',       %s, true),
               set_config('app.currentUserID',         %s, true),
               set_config('app.currentProfessionalID', %s, true)
        """,
        (
            requestContext.clinicID or "",
            requestContext.rolePK,
            requestContext.userID,
            requestContext.professionalID or "",
        ),
    )

@contextmanager
def openTenantTransaction(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> Iterator[Connection]:
    pool = pools.poolForRole(requestContext.rolePK)
    with pool.connection() as connection:
        applyTenantContext(connection, requestContext)
        yield connection

def runWithSerializationRetry(
    maxRetries: int, operation: Callable[[], ResultType]
) -> ResultType:
    lastError: psycopg.Error | None = None

    for attemptNumber in range(1, maxRetries + 1):
        try:
            return operation()
        except (psycopg.errors.SerializationFailure, psycopg.errors.DeadlockDetected) as error:
            lastError = error
            logger.warning(
                "Conflicto de concurrencia (%s) en el intento %s de %s",
                error.sqlstate,
                attemptNumber,
                maxRetries,
            )
    raise lastError  
