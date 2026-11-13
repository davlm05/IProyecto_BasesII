import logging

from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import loadConfig
from app.db.connectionPools import ConnectionPoolRegistry
from app.errors import (
    DomainError,
    INTERNAL_ERROR,
    INVALID_REQUEST,
    ProblemDefinition,
    RESOURCE_NOT_FOUND,
    buildProblemBody,
    translateSqlstate,
)
from app.routers import (
    adminRouter,
    appointmentRouter,
    auditRouter,
    patientRouter,
    scheduleRouter,
)
from app.security.identityResolver import IdentityResolver
from app.security.tokenValidator import AccessTokenValidator

logger = logging.getLogger("medicitas")

PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"

def buildProblemResponse(
    problem: ProblemDefinition, detail: str, request: Request
) -> JSONResponse:
    return JSONResponse(
        status_code=problem.statusCode,
        content=buildProblemBody(problem, detail, request.url.path),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )

@asynccontextmanager
async def applicationLifespan(application: FastAPI):

    config = loadConfig()

    logging.basicConfig(
        level=config.logLevel.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    pools = ConnectionPoolRegistry(config)
    pools.openAllPools()

    application.state.config = config
    application.state.pools = pools
    application.state.tokenValidator = AccessTokenValidator(
        issuer=config.oidcIssuer,
        jwksUrl=config.oidcJwksUrl,
        audience=config.oidcAudience,
    )
    application.state.identityResolver = IdentityResolver(pools)

    logger.info("MediCitas API lista")

    yield

    pools.closeAllPools()
    logger.info("MediCitas API detenida")

application = FastAPI(
    title="MediCitas",
    version="1.0.0",
    summary="Plataforma SaaS multi-tenant de gestion de citas medicas",
    lifespan=applicationLifespan,
)

# =============================================================================
# Manejadores de error
# =============================================================================
@application.exception_handler(DomainError)
async def handleDomainError(request: Request, error: DomainError) -> JSONResponse:
    """Errores que la aplicacion lanza a proposito y sabe explicar."""
    return buildProblemResponse(error.problem, error.detail, request)


@application.exception_handler(psycopg.Error)
async def handleDatabaseError(
    request: Request, error: psycopg.Error
) -> JSONResponse:

    problem, detail = translateSqlstate(error.sqlstate)

    if problem.statusCode >= 500:
        logger.exception(
            "Fallo de base de datos no previsto (sqlstate=%s)", error.sqlstate
        )
    else:
        logger.info(
            "Operacion rechazada por el motor (sqlstate=%s, errorCode=%s)",
            error.sqlstate,
            problem.errorCode,
        )

    return buildProblemResponse(problem, detail, request)


@application.exception_handler(RequestValidationError)
async def handleRequestValidationError(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    problemBody = buildProblemBody(
        INVALID_REQUEST,
        "Alguno de los campos enviados no es valido. Revise 'validationErrors'.",
        request.url.path,
    )
    problemBody["validationErrors"] = [
        {
            "field": ".".join(str(part) for part in validationError.get("loc", [])),
            "message": validationError.get("msg", ""),
        }
        for validationError in error.errors()
    ]

    return JSONResponse(
        status_code=INVALID_REQUEST.statusCode,
        content=problemBody,
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


@application.exception_handler(StarletteHTTPException)
async def handleHttpException(
    request: Request, error: StarletteHTTPException
) -> JSONResponse:
    if error.status_code == RESOURCE_NOT_FOUND.statusCode:
        problem = RESOURCE_NOT_FOUND
    else:
        problem = ProblemDefinition(
            errorCode="httpError",
            title="Error de la solicitud",
            statusCode=error.status_code,
        )

    return buildProblemResponse(problem, str(error.detail), request)


@application.exception_handler(Exception)
async def handleUnexpectedError(request: Request, error: Exception) -> JSONResponse:
    logger.exception("Error no previsto procesando %s", request.url.path)
    return buildProblemResponse(
        INTERNAL_ERROR,
        "Ocurrio un error interno. El detalle quedo en los registros del servicio.",
        request,
    )


# =============================================================================
# Rutas
# =============================================================================
@application.get(
    "/health",
    tags=["Operacion"],
    summary="Comprobar que el servicio responde",
)
def getHealth():
    return {"status": "ok", "service": "medicitas"}


# El orden importa en un solo caso: appointmentRouter declara
# /appointments/day y /appointments/countsByStatus ANTES de
# /appointments/{appointmentID}, porque si no "day" se interpretaria como un
# identificador de cita. FastAPI resuelve las rutas en orden de declaracion.
application.include_router(adminRouter.router)
application.include_router(scheduleRouter.router)
application.include_router(appointmentRouter.router)
application.include_router(patientRouter.router)
application.include_router(auditRouter.router)
