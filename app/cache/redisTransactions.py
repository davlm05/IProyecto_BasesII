import logging
import redis
import json
from uuid import UUID

from app.config import ApplicationConfig

logger = logging.getLogger(__name__)

# Time To Live = 1 hora hasta que la llave expire
TTL_SEGUNDOS = 3600 

# Clave: ProfSchedules:{professionalID}:{serviceID}:{targetDate}
def createKey(params: dict) -> str:
    clinicID = params["clinicID"]
    professionalID = params["professionalID"]
    serviceID = params["serviceID"]
    targetDate = params["targetDate"]
    return (
        f"ProfSchedules:{clinicID}:"
        f"{professionalID}:{serviceID}:{targetDate}"
    )
    
def getKey(client: redis.Redis, params: dict):
    key = createKey(params)
    try:
        cachedKey = client.get(key)

        if cachedKey is None:
            return None

        return json.loads(cachedKey)
    except redis.exceptions.RedisError as error:
        logger.warning(
            "No se pudo consultar Redis: %s. Se consultara PostgreSQL.",
            error,
        )
        return None
    
def saveKey(client: redis.Redis, params: dict, resultado):
    key = createKey(params)
    try:
        client.setex(
            key,
            TTL_SEGUNDOS,
            json.dumps(resultado, default=str),
        )
    except redis.exceptions.RedisError as error:
        logger.warning(
            "No se pudo guardar disponibilidad en Redis: %s",
            error,
        )

def deleteKey(client: redis.Redis, professionalID: str):
    patron = f"ProfSchedules:*:{professionalID}:*"
    try:
        keys = list(client.scan_iter(match=patron))

        if keys:
            client.delete(*keys)
    except redis.exceptions.RedisError as error:
        logger.warning(
            "No se pudo invalidar la cache de Redis: %s",
            error,
        )