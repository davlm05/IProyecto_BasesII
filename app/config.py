import os
from dataclasses import dataclass

def readRequiredVariable(variableName: str) -> str:
    value = os.environ.get(variableName, "").strip()
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno obligatoria {variableName}. "
            f"Copie .env.example a .env antes de levantar la pila."
        )
    return value

def readOptionalVariable(variableName: str, defaultValue: str) -> str:
    value = os.environ.get(variableName, "").strip()
    return value if value else defaultValue

@dataclass(frozen=True)
class DatabaseRoleCredentials:

    databaseRoleName: str
    password: str

@dataclass(frozen=True)
class ApplicationConfig:
    databaseHost: str
    databasePort: int
    databaseName: str
    connectionPoolSizePerRole: int
    credentialsByRolePK: dict[str, DatabaseRoleCredentials]
    oidcIssuer: str
    oidcJwksUrl: str
    oidcAudience: str
    reservationMaxRetries: int
    logLevel: str

# -----------------------------------------------------------------------------
# Traduccion rol del dominio -> perfil de base de datos
# -----------------------------------------------------------------------------
DATABASE_ROLE_BY_ROLE_PK = {
    "platformAdmin": "medicitasPlatform",
    "clinicAdmin": "medicitasClinicAdmin",
    "reception": "medicitasReception",
    "professional": "medicitasProfessional",
}

IDENTITY_RESOLUTION_ROLE_PK = "platformAdmin"

def loadConfig() -> ApplicationConfig:

    credentialsByRolePK = {
        "platformAdmin": DatabaseRoleCredentials(
            databaseRoleName="medicitasPlatform",
            password=readRequiredVariable("MEDICITAS_PLATFORM_PASSWORD"),
        ),
        "clinicAdmin": DatabaseRoleCredentials(
            databaseRoleName="medicitasClinicAdmin",
            password=readRequiredVariable("MEDICITAS_CLINIC_ADMIN_PASSWORD"),
        ),
        "reception": DatabaseRoleCredentials(
            databaseRoleName="medicitasReception",
            password=readRequiredVariable("MEDICITAS_RECEPTION_PASSWORD"),
        ),
        "professional": DatabaseRoleCredentials(
            databaseRoleName="medicitasProfessional",
            password=readRequiredVariable("MEDICITAS_PROFESSIONAL_PASSWORD"),
        ),
    }

    return ApplicationConfig(
        databaseHost=readOptionalVariable("MEDICITAS_DB_HOST", "postgres"),
        databasePort=int(readOptionalVariable("MEDICITAS_DB_PORT", "5432")),
        databaseName=readRequiredVariable("POSTGRES_DB"),
        connectionPoolSizePerRole=int(
            readOptionalVariable("MEDICITAS_DB_POOL_SIZE", "5")
        ),
        credentialsByRolePK=credentialsByRolePK,
        oidcIssuer=readRequiredVariable("KEYCLOAK_ISSUER"),
        oidcJwksUrl=readRequiredVariable("KEYCLOAK_JWKS_URL"),
        oidcAudience=readRequiredVariable("KEYCLOAK_AUDIENCE"),
        reservationMaxRetries=int(
            readOptionalVariable("MEDICITAS_RESERVATION_MAX_RETRIES", "3")
        ),
        logLevel=readOptionalVariable("MEDICITAS_LOG_LEVEL", "info"),
    )
