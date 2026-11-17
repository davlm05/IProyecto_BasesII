import logging
import redis

from app.config import ApplicationConfig

logger = logging.getLogger(__name__)


class RedisClientRegistry:
    def __init__(self, config: ApplicationConfig):
        self._config = config
        self._client: redis.Redis
        
        
    def openRedisClient(self) -> None:

        self._client = redis.Redis(
            host=self._config.redisHost,
            port=self._config.redisPort,
            db=self._config.redisDB,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        
        try:
            self._client.ping()
            logger.info("Cliente de Redis conectado")
        except redis.ConnectionError as error:
            logger.error("No se pudo conectar al cliente de Redis: %s", error,)
        
    def closeRedisClient(self) -> None:
        if self._client is not None:
            self._client.close()
            logger.info("Cliente Redis cerrado")
            
    def getClient(self) -> redis.Redis:
        if self._client is not None:
            return self._client