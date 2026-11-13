from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

class CreatePatientRequest(BaseModel):
    nationalID: str = Field(
        min_length=5,
        max_length=30,
        pattern=r"^[A-Za-z0-9-]{5,30}$",
    )
    firstName: str = Field(min_length=1, max_length=100)
    lastName: str = Field(min_length=1, max_length=100)
    birthDate: date
    phone: str | None = Field(
        default=None, max_length=20, pattern=r"^\+?[0-9 ()-]{7,20}$"
    )
    email: str | None = Field(default=None, max_length=255)


class UpdatePatientRequest(BaseModel):
    firstName: str = Field(min_length=1, max_length=100)
    lastName: str = Field(min_length=1, max_length=100)
    birthDate: date
    phone: str | None = Field(
        default=None, max_length=20, pattern=r"^\+?[0-9 ()-]{7,20}$"
    )
    email: str | None = Field(default=None, max_length=255)


class PatientResponse(BaseModel):
    patientID: UUID
    clinicID: UUID
    nationalID: str
    firstName: str
    lastName: str
    birthDate: date
    phone: str | None = None
    email: str | None = None
    isActive: bool
    createdAt: datetime
    updatedAt: datetime
