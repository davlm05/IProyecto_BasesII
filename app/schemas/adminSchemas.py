from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# Clinicas - RF1
# =============================================================================
class CreateClinicRequest(BaseModel):
    """RF1: alta de clinica con su primer usuario administrador."""

    code: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$",
    )
    name: str = Field(min_length=1, max_length=200)
    timeZone: str = Field(
        min_length=3,
        max_length=64,
    )
    firstAdminIdentityProviderSubject: str = Field(
        min_length=1,
        max_length=255,
    )


class ClinicResponse(BaseModel):
    clinicID: UUID
    code: str
    name: str
    timeZone: str
    isActive: bool
    createdAt: datetime


class CreateClinicResponse(BaseModel):
    clinic: ClinicResponse
    firstAdminUserID: UUID


# =============================================================================
# Usuarios - RF2
# =============================================================================
class CreateUserRequest(BaseModel):
    """RF2: alta de usuario de la clinica."""

    identityProviderSubject: str = Field(min_length=1, max_length=255)
    rolePK: str = Field(
        pattern=r"^(clinicAdmin|reception|professional)$",
    )


class UpdateUserRoleRequest(BaseModel):
    rolePK: str = Field(pattern=r"^(clinicAdmin|reception|professional)$")


class UpdateUserActiveStateRequest(BaseModel):
    isActive: bool


class UserResponse(BaseModel):
    userID: UUID
    clinicID: UUID | None
    identityProviderSubject: str
    rolePK: str
    isActive: bool
    deactivatedAt: datetime | None = None
    createdAt: datetime


# =============================================================================
# Catalogos globales
# =============================================================================
class SpecialtyResponse(BaseModel):
    specialtyID: UUID
    code: str
    name: str


class RoleResponse(BaseModel):
    rolePK: str
    name: str
    description: str


class AppointmentStatusResponse(BaseModel):
    appointmentStatusPK: str
    name: str
    isFinal: bool
    occupiesSlot: bool


class AppointmentStatusTransitionResponse(BaseModel):
    fromAppointmentStatusPK: str
    toAppointmentStatusPK: str


# =============================================================================
# Servicios - RF3
# =============================================================================
class CreateServiceRequest(BaseModel):
    """RF3: nombre, duracion en minutos y especialidad que requiere."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    durationMinutes: int = Field(ge=5, le=480, multiple_of=5)
    specialtyID: UUID


class UpdateServiceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    durationMinutes: int = Field(ge=5, le=480, multiple_of=5)
    isActive: bool


class ServiceResponse(BaseModel):
    serviceID: UUID
    clinicID: UUID
    name: str
    description: str | None = None
    durationMinutes: int
    specialtyID: UUID
    specialtyName: str | None = None
    isActive: bool
    createdAt: datetime


# =============================================================================
# Profesionales - RF4
# =============================================================================
class CreateProfessionalRequest(BaseModel):

    userID: UUID
    specialtyID: UUID
    fullName: str = Field(min_length=1, max_length=200)
    licenseCode: str | None = Field(default=None, max_length=50)
    serviceIDs: list[UUID] = Field(
        default_factory=list,
    )


class ReplaceProfessionalServicesRequest(BaseModel):
    serviceIDs: list[UUID]


class UpdateProfessionalActiveStateRequest(BaseModel):
    isActive: bool


class ProfessionalServiceResponse(BaseModel):
    serviceID: UUID
    name: str
    durationMinutes: int
    isActive: bool


class ProfessionalResponse(BaseModel):
    professionalID: UUID
    clinicID: UUID
    userID: UUID
    specialtyID: UUID
    specialtyName: str | None = None
    fullName: str
    licenseCode: str | None = None
    isActive: bool
    createdAt: datetime
