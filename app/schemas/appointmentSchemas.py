from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


# =============================================================================
# Reserva - RF9
# =============================================================================
class CreateAppointmentRequest(BaseModel):
    patientID: UUID
    professionalID: UUID
    serviceID: UUID
    startAt: datetime


# =============================================================================
# Reprogramacion - RF10
# =============================================================================
class RescheduleAppointmentRequest(BaseModel):
    startAt: datetime
    professionalID: UUID | None = Field(
        default=None)


# =============================================================================
# Cancelacion - RF11
# =============================================================================
class CancelAppointmentRequest(BaseModel):
    cancellationReason: str = Field(
        min_length=1,
        max_length=500,
    )


# =============================================================================
# Desenlace - RF12
# =============================================================================
class RecordOutcomeRequest(BaseModel):
    appointmentStatusPK: str = Field(
        pattern=r"^(attended|absent)$"
    )


# =============================================================================
# Respuestas
# =============================================================================
class AppointmentResponse(BaseModel):
    appointmentID: UUID
    clinicID: UUID
    patientID: UUID
    professionalID: UUID
    serviceID: UUID
    startAt: datetime
    endAt: datetime
    durationMinutes: int
    appointmentStatusPK: str
    createdByUserID: UUID
    createdAt: datetime
    cancelledAt: datetime | None = None
    cancelledByUserID: UUID | None = None
    cancellationReason: str | None = None
    outcomeRecordedAt: datetime | None = None
    outcomeRecordedByUserID: UUID | None = None
    rescheduledToAppointmentID: UUID | None = None


class RescheduleAppointmentResponse(BaseModel):
    originalAppointment: AppointmentResponse
    newAppointment: AppointmentResponse


class DayAgendaItemResponse(BaseModel):
    appointmentID: UUID
    patientID: UUID
    professionalID: UUID
    serviceID: UUID
    startAt: datetime
    endAt: datetime
    durationMinutes: int
    appointmentStatusPK: str
    firstName: str
    lastName: str
    nationalID: str
    professionalName: str
    serviceName: str


class PatientAppointmentHistoryItemResponse(BaseModel):
    appointmentID: UUID
    professionalID: UUID
    serviceID: UUID
    startAt: datetime
    endAt: datetime
    appointmentStatusPK: str
    cancellationReason: str | None = None
    rescheduledToAppointmentID: UUID | None = None
    professionalName: str
    serviceName: str


class AppointmentStatusCountResponse(BaseModel):
    appointmentStatusPK: str
    name: str
    total: int


# =============================================================================
# Notas clinicas - RF15
# =============================================================================
class WriteClinicalNoteRequest(BaseModel):
    content: str = Field(min_length=1, max_length=20000)


class ClinicalNoteResponse(BaseModel):
    clinicalNoteID: UUID
    clinicID: UUID
    appointmentID: UUID
    professionalID: UUID
    content: str
    createdAt: datetime
    updatedAt: datetime
