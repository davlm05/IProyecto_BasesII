-- =============================================================================
-- MediCitas · 09 · Contexto de tenant y resolucion de identidad
-- =============================================================================

CREATE OR REPLACE FUNCTION "currentClinicID"()
RETURNS uuid
LANGUAGE sql
STABLE
AS $fn$
    SELECT nullif(current_setting('app.currentClinicID', true), '')::uuid
$fn$;

CREATE OR REPLACE FUNCTION "currentRoleCode"()
RETURNS text
LANGUAGE sql
STABLE
AS $fn$
    SELECT nullif(current_setting('app.currentRoleCode', true), '')
$fn$;

CREATE OR REPLACE FUNCTION "currentUserID"()
RETURNS uuid
LANGUAGE sql
STABLE
AS $fn$
    SELECT nullif(current_setting('app.currentUserID', true), '')::uuid
$fn$;

CREATE OR REPLACE FUNCTION "currentProfessionalID"()
RETURNS uuid
LANGUAGE sql
STABLE
AS $fn$
    SELECT nullif(current_setting('app.currentProfessionalID', true), '')::uuid
$fn$;

CREATE OR REPLACE FUNCTION "isPlatformAdmin"()
RETURNS boolean
LANGUAGE sql
STABLE
AS $fn$
    SELECT coalesce("currentRoleCode"() = 'platformAdmin', false)
$fn$;

-- =============================================================================
-- resolveIdentity
-- =============================================================================
CREATE OR REPLACE FUNCTION "resolveIdentity"("pSubject" text)
RETURNS TABLE (
    "userID"         uuid,
    "clinicID"       uuid,
    "rolePK"         text,
    "isActive"       boolean,
    "professionalID" uuid
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
    SELECT u."userID",
           u."clinicID",
           u."rolePK",
           u."isActive",
           p."professionalID"
      FROM "users" u
      LEFT JOIN "professionals" p
             ON p."userID" = u."userID"
     WHERE u."identityProviderSubject" = "pSubject"
$fn$;


REVOKE ALL ON FUNCTION "resolveIdentity"(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION "resolveIdentity"(text) TO
    "medicitasPlatform", "medicitasClinicAdmin",
    "medicitasReception", "medicitasProfessional";
