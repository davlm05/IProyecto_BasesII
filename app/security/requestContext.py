from dataclasses import dataclass

@dataclass(frozen=True)
class RequestContext:
    userID: str
    clinicID: str | None
    rolePK: str
    professionalID: str | None
    requestID: str

    @property
    def isPlatformAdmin(self) -> bool:
        return self.rolePK == "platformAdmin"

    @property
    def isProfessional(self) -> bool:
        return self.rolePK == "professional"
