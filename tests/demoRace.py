"""
Uso:
    python -m tests.demoRaceCondition
    python -m tests.demoRaceCondition --attempts 4 --keep
"""

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from tests.test_seguridad_api import API_URL, consultar, obtener_token

PROFESSIONAL_ID = "11111111-0020-0000-0000-000000000001"
SERVICE_ID = "11111111-0030-0000-0000-000000000001"
PATIENT_IDS = (
    "11111111-0040-0000-0000-000000000001",
    "11111111-0040-0000-0000-000000000002",
    "11111111-0040-0000-0000-000000000003",
)

USERNAMES = ("santaLuciaReception", "santaLuciaAdmin")

COSTA_RICA = timezone(timedelta(hours=-6))


# =============================================================================
# Utilidades HTTP
# =============================================================================
def sendPost(route, token, body):
    request = Request(
        API_URL + route,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


def nextWorkingDate(daysAhead):
    """Una fecha futura de lunes a viernes: el horario de la semilla es 1 a 5."""
    targetDate = datetime.now(COSTA_RICA).date() + timedelta(days=daysAhead)

    while targetDate.weekday() >= 5:
        targetDate += timedelta(days=1)

    return targetDate


def findContestedSlot(token, targetDate):
    """RF7: toma el primer espacio libre, que sera el espacio disputado."""
    parameters = urlencode({
        "professionalID": PROFESSIONAL_ID,
        "serviceID": SERVICE_ID,
        "targetDate": targetDate.isoformat(),
    })

    status, payload = consultar(
        f"/availability/professional?{parameters}", token
    )

    if status != 200:
        raise SystemExit(
            f"No se pudo consultar la disponibilidad: {status} {payload}"
        )

    if not payload["availableSlots"]:
        raise SystemExit(
            f"El profesional no tiene espacios libres el {targetDate}. "
            "Pruebe con otro valor de --daysAhead."
        )

    return payload["availableSlots"][0]["startAt"]


# =============================================================================
# Evidencia independiente de la API
# =============================================================================
def readEnvironmentValue(key):
    envFile = Path(__file__).resolve().parents[1] / ".env"

    for line in envFile.read_text(encoding="utf-8").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip().strip("\"'")

    raise SystemExit(f"No se encontro {key} en .env")


def countRowsInPostgres(startAt):
    query = (
        'SELECT count(*) FROM "appointments" '
        f"WHERE \"professionalID\" = '{PROFESSIONAL_ID}' "
        f"AND \"startAt\" = '{startAt}'::timestamptz "
        "AND \"appointmentStatusPK\" NOT IN ('cancelled', 'rescheduled')"
    )

    databaseUser = readEnvironmentValue("POSTGRES_USER")
    databaseName = readEnvironmentValue("POSTGRES_DB")

    try:
        completedProcess = subprocess.run(
            [
                "docker", "exec", "postgresDB",
                "psql", "-U", databaseUser, "-d", databaseName, "-tAc", query,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return None, str(error)

    if completedProcess.returncode != 0:
        return None, completedProcess.stderr.strip()

    return int(completedProcess.stdout.strip()), None


# =============================================================================
# La carrera
# =============================================================================
def runRace(attempts, startAt, tokensByUsername):
    barrier = Barrier(attempts)

    def attemptReservation(attemptNumber):
        username = USERNAMES[attemptNumber % len(USERNAMES)]
        patientID = PATIENT_IDS[attemptNumber % len(PATIENT_IDS)]

        barrier.wait(timeout=30)
        startedAt = datetime.now()

        status, payload = sendPost(
            "/appointments",
            tokensByUsername[username],
            {
                "patientID": patientID,
                "professionalID": PROFESSIONAL_ID,
                "serviceID": SERVICE_ID,
                "startAt": startAt,
            },
        )

        elapsedMilliseconds = (
            datetime.now() - startedAt
        ).total_seconds() * 1000

        return {
            "attemptNumber": attemptNumber + 1,
            "username": username,
            "patientID": patientID,
            "status": status,
            "payload": payload,
            "elapsedMilliseconds": elapsedMilliseconds,
        }

    with ThreadPoolExecutor(max_workers=attempts) as executor:
        futures = [
            executor.submit(attemptReservation, attemptNumber)
            for attemptNumber in range(attempts)
        ]
        results = [future.result(timeout=60) for future in futures]

    return sorted(results, key=lambda result: result["attemptNumber"])


def printResults(results):
    print()
    print(f"{'#':>2}  {'usuario':<20} {'HTTP':<5} {'ms':>7}  resultado")
    print("-" * 78)

    for result in results:
        payload = result["payload"]

        if result["status"] == 201:
            detail = f"cita {payload['appointmentID']}"
        else:
            detail = (
                f"{payload.get('errorCode', '?')}: "
                f"{payload.get('detail', '')}"
            )

        print(
            f"{result['attemptNumber']:>2}  {result['username']:<20} "
            f"{result['status']:<5} {result['elapsedMilliseconds']:>7.0f}  "
            f"{detail}"
        )


# =============================================================================
# Entrada
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Prueba de carrera de RF9 contra un solo espacio libre."
    )
    parser.add_argument(
        "--attempts", type=int, default=3,
        help="Reservas simultaneas sobre el mismo espacio (por omision 3).",
    )
    parser.add_argument(
        "--daysAhead", type=int, default=21,
        help="A cuantos dias buscar el espacio disputado (por omision 21).",
    )
    parser.add_argument(
        "--keep", action="store_true",
        help="No cancelar la cita ganadora al terminar.",
    )
    arguments = parser.parse_args()

    if arguments.attempts < 2:
        raise SystemExit("La carrera necesita al menos dos intentos.")

    print("Pidiendo tokens a Keycloak...")
    tokensByUsername = {
        username: obtener_token(username) for username in USERNAMES
    }

    targetDate = nextWorkingDate(arguments.daysAhead)
    receptionToken = tokensByUsername["santaLuciaReception"]
    startAt = findContestedSlot(receptionToken, targetDate)

    print(f"Espacio disputado: {startAt} (profesional {PROFESSIONAL_ID})")
    print(f"Intentos simultaneos: {arguments.attempts}")

    results = runRace(arguments.attempts, startAt, tokensByUsername)
    printResults(results)

    accepted = [result for result in results if result["status"] == 201]
    rejected = [result for result in results if result["status"] == 409]
    unexpected = [
        result for result in results if result["status"] not in (201, 409)
    ]

    print()
    print(
        f"Aceptadas: {len(accepted)}   "
        f"Rechazadas con 409: {len(rejected)}   "
        f"Inesperadas: {len(unexpected)}"
    )

    rowCount, databaseError = countRowsInPostgres(startAt)

    if databaseError is None:
        print(f"Filas vigentes en PostgreSQL para ese espacio: {rowCount}")
    else:
        print(f"No se pudo contar en PostgreSQL ({databaseError}).")

    for result in rejected:
        errorCode = result["payload"].get("errorCode")

        if errorCode not in ("slotTaken", "serializationConflict"):
            print(
                f"AVISO: el intento {result['attemptNumber']} fallo con "
                f"'{errorCode}', que no es un conflicto de carrera."
            )

    if accepted and not arguments.keep:
        appointmentID = accepted[0]["payload"]["appointmentID"]
        status, _ = sendPost(
            f"/appointments/{appointmentID}/cancel",
            receptionToken,
            {"cancellationReason": "Limpieza de la prueba de carrera"},
        )
        print(
            "Cita ganadora cancelada para dejar el espacio libre "
            f"(HTTP {status})."
        )

    isCorrect = (
        len(accepted) == 1
        and len(unexpected) == 0
        and (databaseError is not None or rowCount == 1)
    )

    print()
    print("RESULTADO: " + (
        "exactamente una reserva gano el espacio (I1 sostenido)."
        if isCorrect else
        "el sistema NO se comporto como I1 exige. Revisar la salida de arriba."
    ))

    return 0 if isCorrect else 1


if __name__ == "__main__":
    sys.exit(main())
