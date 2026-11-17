import logging
import redis
from uuid import UUID

from app.config import ApplicationConfig

logger = logging.getLogger(__name__)

# Time To Live = 1 hora hasta que la llave expire
TTL_SEGUNDOS = 3600 

# Clave: ProfSchedules:{professionalID}:{serviceID}:{targetDate}
def createKey(params: dict) -> str:
    professionalID = params["professionalID"]
    serviceID = params["serviceID"]
    targetDate = params["targetDate"]
    return f"ProfSchedules:{professionalID}:{serviceID}:{targetDate}"
    
def getKey(client: redis.Redis, params: dict):
    key = createKey(params)
    cachedKey = client.get(key)
    if cachedKey is None:
        return None
    return json.loads(cachedKey)
    
def saveKey(client: redis.Redis, params: dict, resultado):
    key = createKey(params)
    client.setex(key, TTL_SEGUNDOS, json.dumps(resultado, default=str))   # Se guarda con tiempo de expiración de 1h

def deleteKey(client: redis.Redis, professionalID: str):
    idx = f"ProfSchedules:{professionalID}:*"
    keys = list(client.scan_iter(match=idx))
    if keys:
        client.delete(*keys)