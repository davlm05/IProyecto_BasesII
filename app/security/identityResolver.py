import logging
import uuid

from app.db.connectionPools import ConnectionPoolRegistry
from app.errors import (
    DomainError,
    INACTIVE_USER,
    TENANT_CLAIM_MISMATCH,
    UNKNOWN_IDENTITY,
)
from app.security.requestContext import RequestContext

logger = logging.getLogger(__name__)

TENANT_CLAIM_NAMES = ("clinicID", "clinicId", "clinic_id")


class IdentityResolver:
    """Resuelve la identidad de una peticion preguntandole a la base de datos."""

    def __init__(self, pools: ConnectionPoolRegistry):
        self._pools = pools

    def resolveSubject(self, subject: str, claims: dict) -> RequestContext:

        pool = self._pools.identityPool()

        with pool.connection() as connection:
            cursor = connection.execute(
                """
                SELECT "userID", "clinicID", "rolePK", "isActive", "professionalID"
                  FROM "resolveIdentity"(%s)
                """,
                (subject,),
            )
            identityRow = cursor.fetchone()

        if identityRow is None:
            logger.warning("Token valido de un sub no registrado: %s", subject)
            raise DomainError(
                UNKNOWN_IDENTITY,
                "La identidad del token no corresponde a ningun usuario de la plataforma.",
            )

        if not identityRow["isActive"]:
            raise DomainError(
                INACTIVE_USER,
                "El usuario esta desactivado y no puede operar en el sistema.",
            )

        clinicIDFromDatabase = identityRow["clinicID"]
        self._rejectTamperedTenantClaim(subject, claims, clinicIDFromDatabase)

        return RequestContext(
            userID=str(identityRow["userID"]),
            clinicID=str(clinicIDFromDatabase) if clinicIDFromDatabase else None,
            rolePK=identityRow["rolePK"],
            professionalID=(
                str(identityRow["professionalID"])
                if identityRow["professionalID"]
                else None
            ),
            requestID=str(uuid.uuid4()),
        )

    def _rejectTamperedTenantClaim(
        self, subject: str, claims: dict, clinicIDFromDatabase
    ) -> None:
        for claimName in TENANT_CLAIM_NAMES:
            claimValue = claims.get(claimName)
            if claimValue is None:
                continue
            if str(claimValue) != str(clinicIDFromDatabase):
                logger.warning(
                    "Intento de cambiar el tenant desde el token: sub=%s "
                    "claim=%s token=%s base=%s",
                    subject,
                    claimName,
                    claimValue,
                    clinicIDFromDatabase,
                )
                raise DomainError(
                    TENANT_CLAIM_MISMATCH,
                    "El token declara una clinica distinta a la que le "
                    "corresponde al usuario.",
                )
