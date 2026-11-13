import logging

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import ApplicationConfig, IDENTITY_RESOLUTION_ROLE_PK

logger = logging.getLogger(__name__)

class ConnectionPoolRegistry:

    def __init__(self, config: ApplicationConfig):
        self._config = config
        self._poolByRolePK: dict[str, ConnectionPool] = {}

    def openAllPools(self) -> None:
        for rolePK, credentials in self._config.credentialsByRolePK.items():
            connectionString = (
                f"host={self._config.databaseHost} "
                f"port={self._config.databasePort} "
                f"dbname={self._config.databaseName} "
                f"user={credentials.databaseRoleName} "
                f"password={credentials.password}"
            )

            pool = ConnectionPool(
                conninfo=connectionString,
                min_size=1,
                max_size=self._config.connectionPoolSizePerRole,
                kwargs={"row_factory": dict_row},
                name=f"pool-{credentials.databaseRoleName}",
                open=False,
            )
            pool.open(wait=True, timeout=30)

            self._poolByRolePK[rolePK] = pool
            logger.info(
                "Pool abierto para el rol %s con el perfil %s",
                rolePK,
                credentials.databaseRoleName,
            )

    def closeAllPools(self) -> None:
        for rolePK, pool in self._poolByRolePK.items():
            pool.close()
            logger.info("Pool cerrado para el rol %s", rolePK)

    def poolForRole(self, rolePK: str) -> ConnectionPool:
        pool = self._poolByRolePK.get(rolePK)
        if pool is None:
            raise RuntimeError(f"No hay pool de conexiones para el rol {rolePK}")
        return pool

    def identityPool(self) -> ConnectionPool:
        return self.poolForRole(IDENTITY_RESOLUTION_ROLE_PK)
