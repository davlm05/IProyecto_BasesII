import logging
import uuid

from app.db.connectionPools import ConnectionPoolRegistry
from app.errors import (
    DomainError,
    FORBIDDEN_ROLE,
    INACTIVE_USER,
    TENANT_CLAIM_MISMATCH,
    UNKNOWN_IDENTITY,
)
from app.security.requestContext import RequestContext

logger = logging.getLogger(__name__)

TENANT_CLAIM_NAMES = ("clinicID", "clinicId", "clinic_id")

DOMAIN_ROLE_NAMES = frozenset(
    ("platformAdmin", "clinicAdmin", "reception", "professional")
)


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
        self._rejectTamperedRoleClaim(subject, claims, identityRow["rolePK"])

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

    def _rejectTamperedRoleClaim(
        self, subject: str, claims: dict, rolePKFromDatabase: str
    ) -> None:
        """RF17: el rol que viaja en el token se compara con el de la base.

        La autoridad sigue siendo PostgreSQL -- el rol efectivo es el de
        "resolveIdentity" --, pero si el token declara roles de dominio y
        ninguno coincide con el de la base, la peticion se rechaza con 403 en
        lugar de operar con un rol que el proveedor de identidad no concedio.
        Si el token no trae ningun rol de dominio no hay nada que contradecir.
        """
        rolesInToken = claims.get("realm_access", {}).get("roles") or []
        domainRolesInToken = DOMAIN_ROLE_NAMES.intersection(rolesInToken)

        if not domainRolesInToken or rolePKFromDatabase in domainRolesInToken:
            return

        logger.warning(
            "El rol del token contradice el de la base: sub=%s token=%s base=%s",
            subject,
            sorted(domainRolesInToken),
            rolePKFromDatabase,
        )
        raise DomainError(
            FORBIDDEN_ROLE,
            "El rol que declara el token no coincide con el rol asignado al "
            "usuario en la plataforma.",
        )
