from fastapi import Depends, Header, Request
from app.errors import DomainError, FORBIDDEN_ROLE
from app.security.requestContext import RequestContext

PLATFORM_ADMIN = "platformAdmin"
CLINIC_ADMIN = "clinicAdmin"
RECEPTION = "reception"
PROFESSIONAL = "professional"


def getRequestContext(
    request: Request,
    authorization: str | None = Header(default=None),
) -> RequestContext:
    tokenValidator = request.app.state.tokenValidator
    identityResolver = request.app.state.identityResolver

    subject, claims = tokenValidator.extractSubjectAndClaims(authorization)
    return identityResolver.resolveSubject(subject, claims)


def requireRoles(*allowedRolePKs: str):
    def checkRoleIsAllowed(
        requestContext: RequestContext = Depends(getRequestContext),
    ) -> RequestContext:
        if requestContext.rolePK not in allowedRolePKs:
            raise DomainError(
                FORBIDDEN_ROLE,
                f"La operacion esta permitida para los roles "
                f"{', '.join(allowedRolePKs)} y su rol es {requestContext.rolePK}.",
            )
        return requestContext

    return checkRoleIsAllowed
