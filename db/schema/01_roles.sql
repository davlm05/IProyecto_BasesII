-- =============================================================================
-- MediCitas · 01 · Roles de base de datos
-- =============================================================================
DO $$
DECLARE
    vRoleName text;
BEGIN
    FOREACH vRoleName IN ARRAY ARRAY[
        'medicitasOwner',
        'medicitasPlatform',
        'medicitasClinicAdmin',
        'medicitasReception',
        'medicitasProfessional'
    ]
    LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = vRoleName) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', vRoleName);
        END IF;
    END LOOP;
END
$$;

ALTER SCHEMA public OWNER TO "medicitasOwner";

GRANT USAGE ON SCHEMA public TO
    "medicitasPlatform", "medicitasClinicAdmin",
    "medicitasReception", "medicitasProfessional";

ALTER TYPE "timeRange" OWNER TO "medicitasOwner";

DO $$
DECLARE
    vFunction record;
BEGIN
    FOR vFunction IN
        SELECT p."oid"::regprocedure AS "signature"
          FROM pg_proc p
          JOIN pg_namespace n ON n."oid" = p."pronamespace"
          LEFT JOIN pg_depend d
                 ON d."objid"   = p."oid"
                AND d."classid" = 'pg_proc'::regclass
                AND d."deptype" = 'e'
         WHERE n."nspname" = 'public'
           AND d."objid" IS NULL
           AND p."proowner" <> '"medicitasOwner"'::regrole
    LOOP
        EXECUTE format('ALTER FUNCTION %s OWNER TO "medicitasOwner"', vFunction."signature");
    END LOOP;
END
$$;
