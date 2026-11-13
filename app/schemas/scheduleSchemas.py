from datetime import date, datetime, time
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

# =============================================================================
# Horario de atencion - RF5
# =============================================================================
class CreateWorkingHourRequest(BaseModel):
    weekday: int = Field(
        ge=1,
        le=7,    
    )
    startTimeLocal: time
    endTimeLocal: time

    @model_validator(mode="after")
    def checkStartIsBeforeEnd(self) -> "CreateWorkingHourRequest":
        if self.startTimeLocal >= self.endTimeLocal:
            raise ValueError("startTimeLocal debe ser anterior a endTimeLocal")
        return self


class WorkingHourResponse(BaseModel):
    workingHourID: UUID
    clinicID: UUID
    professionalID: UUID
    weekday: int
    startTimeLocal: time
    endTimeLocal: time
    createdAt: datetime


# =============================================================================
# Bloqueos de agenda - RF6
# =============================================================================
class CreateScheduleBlockRequest(BaseModel):
    professionalID: UUID
    startAt: datetime = Field(
        description="Instante de inicio, con zona horaria (ISO 8601)."
    )
    endAt: datetime
    reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def checkStartIsBeforeEnd(self) -> "CreateScheduleBlockRequest":
        if self.startAt >= self.endAt:
            raise ValueError("startAt debe ser anterior a endAt")
        return self


class ScheduleBlockResponse(BaseModel):
    scheduleBlockID: UUID
    clinicID: UUID
    professionalID: UUID
    startAt: datetime
    endAt: datetime
    reason: str
    userID: UUID
    createdAt: datetime


class ConflictingAppointmentResponse(BaseModel):
    appointmentID: UUID
    patientID: UUID
    professionalID: UUID
    serviceID: UUID
    startAt: datetime
    endAt: datetime
    appointmentStatusPK: str
    firstName: str
    lastName: str


# =============================================================================
# Disponibilidad - RF7, RF8
# =============================================================================
class AvailableSlotResponse(BaseModel):
    startAt: datetime
    endAt: datetime


class ProfessionalAvailabilityResponse(BaseModel):
    professionalID: UUID
    professionalName: str | None = None
    serviceID: UUID
    durationMinutes: int
    targetDate: date
    availableSlots: list[AvailableSlotResponse]


class ServiceAvailabilityResponse(BaseModel):
    serviceID: UUID
    durationMinutes: int
    fromDate: date
    toDate: date
    availabilityByProfessional: list[ProfessionalAvailabilityResponse]
