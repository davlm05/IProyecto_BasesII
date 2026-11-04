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
