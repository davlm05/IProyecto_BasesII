from datetime import date, datetime, timedelta, timezone

from psycopg import Connection

from app.db.connectionPools import ConnectionPoolRegistry
from app.db.transaction import openTenantTransaction
from app.errors import DomainError, RESOURCE_NOT_FOUND
from app.repositories import availabilityRepository, professionalRepository
from app.security.requestContext import RequestContext

MAX_DAYS_IN_RANGE = 31


def overlapsAnyBusyInterval(
    slotStart: datetime, slotEnd: datetime, busyIntervals: list[dict]
) -> bool:
    for busyInterval in busyIntervals:
        if slotStart < busyInterval["endAt"] and busyInterval["startAt"] < slotEnd:
            return True
    return False


def buildSlotsForWorkingInterval(
    intervalStart: datetime,
    intervalEnd: datetime,
    durationMinutes: int,
    busyIntervals: list[dict],
    earliestAllowedStart: datetime,
) -> list[dict]:
    slotDuration = timedelta(minutes=durationMinutes)
    availableSlots: list[dict] = []

    slotStart = intervalStart
    while slotStart + slotDuration <= intervalEnd:
        slotEnd = slotStart + slotDuration

        isInTheFuture = slotStart >= earliestAllowedStart
        isFree = not overlapsAnyBusyInterval(slotStart, slotEnd, busyIntervals)

        if isInTheFuture and isFree:
            availableSlots.append({"startAt": slotStart, "endAt": slotEnd})

        slotStart = slotEnd

    return availableSlots


def calculateProfessionalAvailability(
    connection: Connection,
    professionalID: str,
    serviceID: str,
    targetDate: date,
    durationMinutes: int,
) -> list[dict]:

    workingIntervals = availabilityRepository.listWorkingIntervalsForDate(
        connection, professionalID, targetDate
    )

    if not workingIntervals:
        return []

    dayStart = workingIntervals[0]["startAt"]
    dayEnd = workingIntervals[-1]["endAt"]

    busyIntervals = availabilityRepository.listBusyIntervals(
        connection, professionalID, dayStart, dayEnd
    )

    earliestAllowedStart = datetime.now(timezone.utc)

    availableSlots: list[dict] = []
    for workingInterval in workingIntervals:
        availableSlots.extend(
            buildSlotsForWorkingInterval(
                intervalStart=workingInterval["startAt"],
                intervalEnd=workingInterval["endAt"],
                durationMinutes=durationMinutes,
                busyIntervals=busyIntervals,
                earliestAllowedStart=earliestAllowedStart,
            )
        )

    return availableSlots


def getProfessionalAvailability(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    professionalID: str,
    serviceID: str,
    targetDate: date,
) -> dict:
    with openTenantTransaction(pools, requestContext) as connection:
        durationMinutes = availabilityRepository.findServiceDurationMinutes(
            connection, serviceID
        )
        if durationMinutes is None:
            raise DomainError(
                RESOURCE_NOT_FOUND,
                "El servicio no existe o no esta activo en su clinica.",
            )

        professional = professionalRepository.findProfessionalByID(
            connection, professionalID
        )
        if professional is None:
            raise DomainError(
                RESOURCE_NOT_FOUND, "El profesional no existe en su clinica."
            )

        availableSlots = calculateProfessionalAvailability(
            connection, professionalID, serviceID, targetDate, durationMinutes
        )

        return {
            "professionalID": professionalID,
            "professionalName": professional["fullName"],
            "serviceID": serviceID,
            "durationMinutes": durationMinutes,
            "targetDate": targetDate,
            "availableSlots": availableSlots,
        }


def getServiceAvailability(
    pools: ConnectionPoolRegistry,
    requestContext: RequestContext,
    serviceID: str,
    fromDate: date,
    toDate: date,
) -> dict:
    if toDate < fromDate:
        raise DomainError(
            RESOURCE_NOT_FOUND, "La fecha final no puede ser anterior a la inicial."
        )

    numberOfDays = (toDate - fromDate).days + 1
    if numberOfDays > MAX_DAYS_IN_RANGE:
        raise DomainError(
            RESOURCE_NOT_FOUND,
            f"El rango no puede exceder {MAX_DAYS_IN_RANGE} dias.",
        )

    with openTenantTransaction(pools, requestContext) as connection:
        durationMinutes = availabilityRepository.findServiceDurationMinutes(
            connection, serviceID
        )
        if durationMinutes is None:
            raise DomainError(
                RESOURCE_NOT_FOUND,
                "El servicio no existe o no esta activo en su clinica.",
            )

        professionals = professionalRepository.listProfessionalsOfferingService(
            connection, serviceID
        )

        availabilityByProfessional: list[dict] = []
        for professional in professionals:
            professionalID = str(professional["professionalID"])

            for dayOffset in range(numberOfDays):
                targetDate = fromDate + timedelta(days=dayOffset)

                availableSlots = calculateProfessionalAvailability(
                    connection, professionalID, serviceID, targetDate, durationMinutes
                )

                # Solo se devuelven los dias con espacio: RF8 pide "los
                # profesionales que tienen espacio", de modo que un dia vacio
                # no aporta nada a la respuesta.
                if availableSlots:
                    availabilityByProfessional.append(
                        {
                            "professionalID": professionalID,
                            "professionalName": professional["fullName"],
                            "serviceID": serviceID,
                            "durationMinutes": durationMinutes,
                            "targetDate": targetDate,
                            "availableSlots": availableSlots,
                        }
                    )

        return {
            "serviceID": serviceID,
            "durationMinutes": durationMinutes,
            "fromDate": fromDate,
            "toDate": toDate,
            "availabilityByProfessional": availabilityByProfessional,
        }
