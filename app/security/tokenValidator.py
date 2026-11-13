import logging
import jwt
from jwt import PyJWKClient

from app.errors import DomainError, INVALID_TOKEN, MISSING_TOKEN

logger = logging.getLogger(__name__)

class AccessTokenValidator:

    def __init__(self, issuer: str, jwksUrl: str, audience: str):
        self._issuer = issuer
        self._audience = audience
        self._jwksClient = PyJWKClient(jwksUrl, cache_keys=True, max_cached_keys=16)

    def extractSubjectAndClaims(self, authorizationHeader: str | None) -> tuple[str, dict]:

        if not authorizationHeader:
            raise DomainError(
                MISSING_TOKEN,
                "La ruta exige un token de acceso en el encabezado Authorization.",
            )

        parts = authorizationHeader.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise DomainError(
                MISSING_TOKEN,
                "El encabezado Authorization debe tener la forma 'Bearer <token>'.",
            )

        encodedToken = parts[1].strip()

        try:
            signingKey = self._jwksClient.get_signing_key_from_jwt(encodedToken)
            claims = jwt.decode(
                encodedToken,
                signingKey.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["exp", "iss", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            raise DomainError(INVALID_TOKEN, "El token de acceso esta vencido.")
        except jwt.InvalidAudienceError:
            raise DomainError(
                INVALID_TOKEN,
                "El token no fue emitido para esta aplicacion.",
            )
        except jwt.InvalidIssuerError:
            raise DomainError(
                INVALID_TOKEN,
                "El token no proviene del proveedor de identidad esperado.",
            )
        except jwt.PyJWTError as error:
            logger.warning("Token rechazado: %s", error)
            raise DomainError(INVALID_TOKEN, "El token de acceso no es valido.")

        subject = claims.get("sub")
        if not subject:
            raise DomainError(INVALID_TOKEN, "El token no trae el claim 'sub'.")

        return subject, claims
