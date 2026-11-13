from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.schemas.adminSchemas import (
    AppointmentStatusResponse,
    AppointmentStatusTransitionResponse,
    ClinicResponse,
    CreateClinicRequest,
    CreateClinicResponse,
    CreateProfessionalRequest,
    CreateServiceRequest,
    CreateUserRequest,
    ProfessionalResponse,
    ProfessionalServiceResponse,
    ReplaceProfessionalServicesRequest,
    RoleResponse,
    ServiceResponse,
    SpecialtyResponse,
    UpdateProfessionalActiveStateRequest,
    UpdateServiceRequest,
    UpdateUserActiveStateRequest,
    UpdateUserRoleRequest,
    UserResponse,
)
from app.security.dependencies import (
    CLINIC_ADMIN,
    PLATFORM_ADMIN,
    PROFESSIONAL,
    RECEPTION,
    getRequestContext,
    requireRoles,
)
from app.security.requestContext import RequestContext
from app.services import adminService

router = APIRouter(tags=["Administracion"])

# =============================================================================
# RF1 - Clinicas
# =============================================================================
@router.post(
    "/clinics",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateClinicResponse,
    summary="RF1 - Dar de alta una clinica con su primer administrador",
)
def createClinic(
    request: Request,
    createClinicRequest: CreateClinicRequest,
    requestContext: RequestContext = Depends(requireRoles(PLATFORM_ADMIN)),
):
    return adminService.createClinicWithFirstAdmin(
        request.app.state.pools,
        requestContext,
        code=createClinicRequest.code,
        name=createClinicRequest.name,
        timeZone=createClinicRequest.timeZone,
        firstAdminIdentityProviderSubject=(
            createClinicRequest.firstAdminIdentityProviderSubject
        ),
    )


@router.get(
    "/clinics",
    response_model=list[ClinicResponse],
    summary="RF1 - Listar clinicas de la plataforma",
)
def listClinics(
    request: Request,
    requestContext: RequestContext = Depends(requireRoles(PLATFORM_ADMIN)),
):
    return adminService.listClinics(request.app.state.pools, requestContext)


@router.get(
    "/clinics/current",
    response_model=ClinicResponse,
    summary="Consultar la clinica del usuario autenticado",
)
def getCurrentClinic(
    request: Request,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return adminService.getOwnClinic(request.app.state.pools, requestContext)


# =============================================================================
# RF2 - Usuarios de la clinica
# =============================================================================
@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    summary="RF2 - Dar de alta un usuario de la clinica",
)
def createUser(
    request: Request,
    createUserRequest: CreateUserRequest,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.createUser(
        request.app.state.pools,
        requestContext,
        identityProviderSubject=createUserRequest.identityProviderSubject,
        rolePK=createUserRequest.rolePK,
    )

@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="RF2 - Listar los usuarios de la clinica",
)
def listUsers(
    request: Request,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.listUsers(request.app.state.pools, requestContext)


@router.patch(
    "/users/{userID}/role",
    response_model=UserResponse,
    summary="RF2 - Asignar rol a un usuario",
)
def updateUserRole(
    request: Request,
    userID: UUID,
    updateUserRoleRequest: UpdateUserRoleRequest,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.updateUserRole(
        request.app.state.pools,
        requestContext,
        userID=userID,
        rolePK=updateUserRoleRequest.rolePK,
    )

@router.patch(
    "/users/{userID}/activeState",
    response_model=UserResponse,
    summary="RF2 - Baja logica o reactivacion de un usuario",
)
def updateUserActiveState(
    request: Request,
    userID: UUID,
    updateUserActiveStateRequest: UpdateUserActiveStateRequest,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.setUserActiveState(
        request.app.state.pools,
        requestContext,
        userID=userID,
        isActive=updateUserActiveStateRequest.isActive,
    )

# =============================================================================
# Catalogos globales
# =============================================================================
@router.get(
    "/specialties",
    response_model=list[SpecialtyResponse],
    summary="Listar el catalogo de especialidades",
)
def listSpecialties(
    request: Request,
    requestContext: RequestContext = Depends(getRequestContext),
):
    return adminService.listSpecialties(request.app.state.pools, requestContext)


@router.get(
    "/roles",
    response_model=list[RoleResponse],
    summary="Listar los roles del sistema",
)
def listRoles(
    request: Request,
    requestContext: RequestContext = Depends(getRequestContext),
):
    return adminService.listRoles(request.app.state.pools, requestContext)


@router.get(
    "/appointmentStatuses",
    response_model=list[AppointmentStatusResponse],
    summary="RF13 - Listar los estados de la cita",
)
def listAppointmentStatuses(
    request: Request,
    requestContext: RequestContext = Depends(getRequestContext),
):
    return adminService.listAppointmentStatuses(
        request.app.state.pools, requestContext
    )


@router.get(
    "/appointmentStatuses/transitions",
    response_model=list[AppointmentStatusTransitionResponse],
    summary="RF13 - Listar las transiciones de estado permitidas",
)
def listAppointmentStatusTransitions(
    request: Request,
    requestContext: RequestContext = Depends(getRequestContext),
):
    return adminService.listAppointmentStatusTransitions(
        request.app.state.pools, requestContext
    )

# =============================================================================
# RF3 - Servicios
# =============================================================================
@router.post(
    "/services",
    status_code=status.HTTP_201_CREATED,
    response_model=ServiceResponse,
    summary="RF3 - Crear un servicio del catalogo de la clinica",
)
def createService(
    request: Request,
    createServiceRequest: CreateServiceRequest,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.createService(
        request.app.state.pools,
        requestContext,
        name=createServiceRequest.name,
        description=createServiceRequest.description,
        durationMinutes=createServiceRequest.durationMinutes,
        specialtyID=createServiceRequest.specialtyID,
    )

@router.get(
    "/services",
    response_model=list[ServiceResponse],
    summary="RF3 - Listar el catalogo de servicios",
)
def listServices(
    request: Request,
    onlyActive: bool = Query(
        default=True, description="Si es false incluye tambien los inactivos."
    ),
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return adminService.listServices(
        request.app.state.pools, requestContext, onlyActive
    )


@router.put(
    "/services/{serviceID}",
    response_model=ServiceResponse,
    summary="RF3 - Actualizar un servicio",
)
def updateService(
    request: Request,
    serviceID: UUID,
    updateServiceRequest: UpdateServiceRequest,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.updateService(
        request.app.state.pools,
        requestContext,
        serviceID=serviceID,
        name=updateServiceRequest.name,
        description=updateServiceRequest.description,
        durationMinutes=updateServiceRequest.durationMinutes,
        isActive=updateServiceRequest.isActive,
    )


# =============================================================================
# RF4 - Profesionales
# =============================================================================
@router.post(
    "/professionals",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfessionalResponse,
    summary="RF4 - Registrar un profesional con su especialidad y servicios",
)
def createProfessional(
    request: Request,
    createProfessionalRequest: CreateProfessionalRequest,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.createProfessional(
        request.app.state.pools,
        requestContext,
        userID=createProfessionalRequest.userID,
        specialtyID=createProfessionalRequest.specialtyID,
        fullName=createProfessionalRequest.fullName,
        licenseCode=createProfessionalRequest.licenseCode,
        serviceIDs=createProfessionalRequest.serviceIDs,
    )


@router.get(
    "/professionals",
    response_model=list[ProfessionalResponse],
    summary="RF4 - Listar los profesionales de la clinica",
)
def listProfessionals(
    request: Request,
    onlyActive: bool = Query(default=True),
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return adminService.listProfessionals(
        request.app.state.pools, requestContext, onlyActive
    )


@router.get(
    "/professionals/{professionalID}/services",
    response_model=list[ProfessionalServiceResponse],
    summary="RF4 - Listar los servicios que un profesional puede atender",
)
def listProfessionalServices(
    request: Request,
    professionalID: UUID,
    requestContext: RequestContext = Depends(
        requireRoles(CLINIC_ADMIN, RECEPTION, PROFESSIONAL)
    ),
):
    return adminService.listProfessionalServices(
        request.app.state.pools, requestContext, professionalID
    )


@router.put(
    "/professionals/{professionalID}/services",
    response_model=list[ProfessionalServiceResponse],
    summary="RF4 - Reemplazar los servicios habilitados de un profesional",
)
def replaceProfessionalServices(
    request: Request,
    professionalID: UUID,
    replaceProfessionalServicesRequest: ReplaceProfessionalServicesRequest,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.replaceProfessionalServices(
        request.app.state.pools,
        requestContext,
        professionalID=professionalID,
        serviceIDs=replaceProfessionalServicesRequest.serviceIDs,
    )


@router.patch(
    "/professionals/{professionalID}/activeState",
    response_model=ProfessionalResponse,
    summary="RF4 - Activar o desactivar un profesional",
)
def updateProfessionalActiveState(
    request: Request,
    professionalID: UUID,
    updateProfessionalActiveStateRequest: UpdateProfessionalActiveStateRequest,
    requestContext: RequestContext = Depends(requireRoles(CLINIC_ADMIN)),
):
    return adminService.setProfessionalActiveState(
        request.app.state.pools,
        requestContext,
        professionalID=professionalID,
        isActive=updateProfessionalActiveStateRequest.isActive,
    )
