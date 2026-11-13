from dataclasses import dataclass

@dataclass(frozen=True)
class ProblemDefinition:
    errorCode: str
    title: str
    statusCode: int

class DomainError(Exception):

    def __init__(self, problem: ProblemDefinition, detail: str):
        super().__init__(detail)
        self.problem = problem
        self.detail = detail

# =============================================================================
# Errores de autenticacion y autorizacion (RF17)
# =============================================================================
MISSING_TOKEN = ProblemDefinition(
    "missingToken", "Falta el token de acceso", 401
)
INVALID_TOKEN = ProblemDefinition(
    "invalidToken", "Token de acceso invalido", 401
)
UNKNOWN_IDENTITY = ProblemDefinition(
    "unknownIdentity", "Identidad no registrada en la plataforma", 403
)
INACTIVE_USER = ProblemDefinition(
    "inactiveUser", "Usuario desactivado", 403
)
TENANT_CLAIM_MISMATCH = ProblemDefinition(
    "tenantClaimMismatch", "El token declara una clinica que no le corresponde", 403
)
FORBIDDEN_ROLE = ProblemDefinition(
    "forbiddenRole", "Su rol no permite esta operacion", 403
)
FORBIDDEN_NOT_OWN_RESOURCE = ProblemDefinition(
    "forbiddenNotOwnResource", "Solo puede operar sobre sus propios registros", 403
)

# =============================================================================
# Errores de negocio
# =============================================================================
RESOURCE_NOT_FOUND = ProblemDefinition(
    "resourceNotFound", "Recurso no encontrado", 404
)
INVALID_REQUEST = ProblemDefinition(
    "invalidRequest", "Solicitud invalida", 422
)
OUTCOME_BEFORE_START = ProblemDefinition(
    "outcomeBeforeStart", "La cita todavia no ha empezado", 422
)
APPOINTMENT_NOT_RESERVED = ProblemDefinition(
    "appointmentNotReserved", "La cita ya tiene un estado final", 409
)
RESCHEDULE_OVERLAPS_ORIGIN = ProblemDefinition(
    "rescheduleOverlapsOrigin",
    "El espacio destino se solapa con el de la cita original",
    409,
)
INTERNAL_ERROR = ProblemDefinition(
    "internalError", "Error interno del servicio", 500
)

# =============================================================================
# Traduccion SQLSTATE -> Problem Details
# =============================================================================
PROBLEM_BY_SQLSTATE: dict[str, tuple[ProblemDefinition, str]] = {
    "MC001": (
        ProblemDefinition("outsideWorkingHours", "Fuera del horario de atencion", 422),
        "La cita no cae dentro del horario de atencion del profesional (I3).",
    ),
    "MC002": (
        ProblemDefinition("scheduleBlocked", "Agenda bloqueada", 422),
        "La cita cae dentro de un bloqueo de agenda del profesional (I3).",
    ),
    "MC003": (
        ProblemDefinition("invalidStatusTransition", "Transicion de estado no permitida", 409),
        "El ciclo de vida de la cita no admite esa transicion (RF13).",
    ),
    "MC004": (
        ProblemDefinition("appointmentImmutable", "La cita no se puede mover", 409),
        "Una cita no se mueve ni se reasigna: para cambiar su espacio hay que "
        "reprogramarla, lo que crea una cita nueva (RF10).",
    ),
    "MC005": (
        ProblemDefinition("professionalNotEnabledForService", "Profesional no habilitado", 422),
        "El profesional no esta habilitado para ese servicio, o el profesional "
        "o el servicio estan inactivos (RF4).",
    ),
    "MC006": (
        ProblemDefinition("auditLogImmutable", "La bitacora no se puede modificar", 403),
        "La bitacora de auditoria solo admite agregar registros (I6).",
    ),
    "MC007": (
        ProblemDefinition("appointmentNotAttended", "La cita no esta atendida", 409),
        "Solo se adjunta nota clinica a una cita en estado atendida (RF15).",
    ),
    "MC008": (
        ProblemDefinition("unknownTimeZone", "Zona horaria desconocida", 422),
        "La zona horaria indicada no es una zona IANA valida (RF1).",
    ),
    "MC009": (
        ProblemDefinition("birthDateInFuture", "Fecha de nacimiento invalida", 422),
        "La fecha de nacimiento no puede estar en el futuro (RF14).",
    ),
    "MC010": (
        ProblemDefinition("appointmentCrossesMidnight", "La cita cruza la medianoche", 422),
        "La cita cruzaria la medianoche local de la clinica.",
    ),
    "MC011": (
        ProblemDefinition("appointmentDurationImmutable", "La duracion no se puede alterar", 409),
        "La duracion de una cita la determina el servicio y ninguna operacion "
        "la altera por su cuenta (I4).",
    ),
    "23P01": (
        ProblemDefinition("slotTaken", "Espacio ya tomado", 409),
        "El espacio solicitado ya esta ocupado por otra cita vigente.",
    ),
    "23505": (
        ProblemDefinition("duplicateResource", "Registro duplicado", 409),
        "Ya existe un registro con esos datos.",
    ),
    "23503": (
        ProblemDefinition("relatedResourceNotFound", "Recurso referenciado inexistente", 422),
        "Alguno de los recursos referenciados no existe dentro de su clinica.",
    ),
    "23514": (
        ProblemDefinition("constraintViolated", "Datos invalidos", 422),
        "Los datos enviados no cumplen una restriccion del modelo.",
    ),
    "23502": (
        ProblemDefinition("missingRequiredField", "Falta un campo obligatorio", 422),
        "Falta un campo obligatorio del registro.",
    ),
    "42501": (
        ProblemDefinition("insufficientDatabasePrivilege", "Privilegios insuficientes", 403),
        "Su perfil no tiene privilegios sobre ese dato.",
    ),
    "40001": (
        ProblemDefinition("serializationConflict", "Conflicto de concurrencia", 409),
        "La operacion no pudo completarse por un conflicto de concurrencia. "
        "Vuelva a intentarlo.",
    ),
    "40P01": (
        ProblemDefinition("serializationConflict", "Conflicto de concurrencia", 409),
        "La operacion no pudo completarse por un bloqueo mutuo entre "
        "transacciones. Vuelva a intentarlo.",
    ),
}

UNEXPECTED_DATABASE_PROBLEM = (
    ProblemDefinition("databaseError", "Error de base de datos", 500),
    "La base de datos rechazo la operacion por un motivo no previsto.",
)


def translateSqlstate(sqlstate: str | None) -> tuple[ProblemDefinition, str]:
    if sqlstate is None:
        return UNEXPECTED_DATABASE_PROBLEM
    return PROBLEM_BY_SQLSTATE.get(sqlstate, UNEXPECTED_DATABASE_PROBLEM)


def buildProblemBody(
    problem: ProblemDefinition, detail: str, instancePath: str
) -> dict:
    return {
        "type": f"/errors/{problem.errorCode}",
        "title": problem.title,
        "status": problem.statusCode,
        "detail": detail,
        "instance": instancePath,
        "errorCode": problem.errorCode,
    }
