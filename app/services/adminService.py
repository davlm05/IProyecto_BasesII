from psycopg import Connection

from app.db.connectionPools import ConnectionPoolRegistry
from app.db.transaction import openTenantTransaction
from app.errors import DomainError, INVALID_REQUEST, RESOURCE_NOT_FOUND
from app.repositories import (
    catalogRepository,
    clinicRepository,
    professionalRepository,
    serviceRepository,
    userRepository,
)
from app.security.requestContext import RequestContext


# =============================================================================
# RF1 - Alta de clinica
# =============================================================================
def createClinicWithFirstAdmin(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    code: str,
    name: str,
    timeZone: str,
    firstAdminIdentityProviderSubject: str,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        clinic = clinicRepository.insertClinic(connection, code, name, timeZone)

        firstAdminUser = userRepository.insertUser(
            connection,
            clinicID=str(clinic["clinicID"]),
            identityProviderSubject=firstAdminIdentityProviderSubject,
            rolePK="clinicAdmin",
        )

        return {
            "clinic": clinic,
            "firstAdminUserID": str(firstAdminUser["userID"]),
        }


def listClinics(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return clinicRepository.listClinics(connection)


def getOwnClinic(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> dict:
    if requestContext.clinicID is None:
        raise DomainError(
            INVALID_REQUEST,
            "El administrador de plataforma no pertenece a ninguna clinica.",
        )

    with openTenantTransaction(pools, requestContext) as connection:
        clinic = clinicRepository.findClinicByID(connection, requestContext.clinicID)

    if clinic is None:
        raise DomainError(RESOURCE_NOT_FOUND, "La clinica no existe.")
    return clinic


# =============================================================================
# RF2 - Usuarios de la clinica
# =============================================================================
def createUser(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    identityProviderSubject: str,
    rolePK: str,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        return userRepository.insertUser(
            connection,
            clinicID=requestContext.clinicID,
            identityProviderSubject=identityProviderSubject,
            rolePK=rolePK,
        )

def listUsers(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return userRepository.listUsers(connection)

def updateUserRole(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    userID: str,
    rolePK: str,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        updatedUser = userRepository.updateUserRole(connection, userID, rolePK)

    if updatedUser is None:
        raise DomainError(RESOURCE_NOT_FOUND, "El usuario no existe en su clinica.")
    return updatedUser


def setUserActiveState(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    userID: str,
    isActive: bool,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        updatedUser = userRepository.setUserActiveState(connection, userID, isActive)

    if updatedUser is None:
        raise DomainError(RESOURCE_NOT_FOUND, "El usuario no existe en su clinica.")
    return updatedUser


# =============================================================================
# Catalogos globales
# =============================================================================
def listSpecialties(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return catalogRepository.listSpecialties(connection)


def listRoles(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return catalogRepository.listRoles(connection)


def listAppointmentStatuses(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return catalogRepository.listAppointmentStatuses(connection)


def listAppointmentStatusTransitions(
    pools: ConnectionPoolRegistry, requestContext: RequestContext
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return catalogRepository.listAppointmentStatusTransitions(connection)


# =============================================================================
# RF3 - Catalogo de servicios
# =============================================================================
def createService(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    name: str,
    description: str | None,
    durationMinutes: int,
    specialtyID: str,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        return serviceRepository.insertService(
            connection,
            clinicID=requestContext.clinicID,
            name=name,
            description=description,
            durationMinutes=durationMinutes,
            specialtyID=specialtyID,
        )


def listServices(
    pools: ConnectionPoolRegistry, requestContext: RequestContext, onlyActive: bool
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return serviceRepository.listServices(connection, onlyActive)


def updateService(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    serviceID: str,
    name: str,
    description: str | None,
    durationMinutes: int,
    isActive: bool,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        updatedService = serviceRepository.updateService(
            connection, serviceID, name, description, durationMinutes, isActive
        )

    if updatedService is None:
        raise DomainError(RESOURCE_NOT_FOUND, "El servicio no existe en su clinica.")
    return updatedService


# =============================================================================
# RF4 - Profesionales
# =============================================================================
def createProfessional(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    userID: str,
    specialtyID: str,
    fullName: str,
    licenseCode: str | None,
    serviceIDs: list[str],
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        professional = professionalRepository.insertProfessional(
            connection,
            clinicID=requestContext.clinicID,
            userID=userID,
            specialtyID=specialtyID,
            fullName=fullName,
            licenseCode=licenseCode,
        )

        professionalID = str(professional["professionalID"])
        for serviceID in serviceIDs:
            professionalRepository.insertProfessionalService(
                connection,
                clinicID=requestContext.clinicID,
                professionalID=professionalID,
                serviceID=serviceID,
            )

        return professional


def listProfessionals(
    pools: ConnectionPoolRegistry, requestContext: RequestContext, onlyActive: bool
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return professionalRepository.listProfessionals(connection, onlyActive)


def replaceProfessionalServices(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    professionalID: str,
    serviceIDs: list[str],
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        professional = professionalRepository.findProfessionalByID(
            connection, professionalID
        )
        if professional is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El profesional no existe en su clinica."
            )

        professionalRepository.deleteProfessionalServices(connection, professionalID)
        for serviceID in serviceIDs:
            professionalRepository.insertProfessionalService(
                connection,
                clinicID=requestContext.clinicID,
                professionalID=professionalID,
                serviceID=serviceID,
            )

        return professionalRepository.listProfessionalServices(
            connection, professionalID
        )


def listProfessionalServices(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    professionalID: str,
) -> list[dict]:
    with openTenantTransaction(pools, requestContext) as connection:
        return professionalRepository.listProfessionalServices(
            connection, professionalID
        )


def setProfessionalActiveState(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    professionalID: str,
    isActive: bool,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        updatedProfessional = professionalRepository.setProfessionalActiveState(
            connection, professionalID, isActive
        )

    if updatedProfessional is None:
        raise DomainError(RESOURCE_NOT_FOUND, "El profesional no existe en su clinica.")
    return updatedProfessional
