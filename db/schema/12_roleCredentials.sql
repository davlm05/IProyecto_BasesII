-- =============================================================================
-- MediCitas · 12 · Credenciales de los cinco perfiles y comprobacion final
-- =============================================================================
ALTER ROLE "medicitasOwner"        WITH LOGIN PASSWORD :'ownerPassword';

ALTER ROLE "medicitasPlatform"     WITH LOGIN PASSWORD :'platformPassword';
ALTER ROLE "medicitasClinicAdmin"  WITH LOGIN PASSWORD :'clinicAdminPassword';
ALTER ROLE "medicitasReception"    WITH LOGIN PASSWORD :'receptionPassword';
ALTER ROLE "medicitasProfessional" WITH LOGIN PASSWORD :'professionalPassword';

-- Comprobacion de cierre. Ninguno de los cuatro perfiles puede crear objetos en
-- el esquema
DO $$
DECLARE
    vRoleName text;
BEGIN
    FOREACH vRoleName IN ARRAY ARRAY[
        'medicitasPlatform',
        'medicitasClinicAdmin',
        'medicitasReception',
        'medicitasProfessional'
    ]
    LOOP
        IF has_schema_privilege(vRoleName, 'public', 'CREATE') THEN
            RAISE EXCEPTION
                'El perfil % puede crear objetos en el esquema public; revise 11_privileges.sql',
                vRoleName;
        END IF;
    END LOOP;
END
$$;

DO $$
DECLARE
    vForeignTables    bigint;
    vForeignFunctions bigint;
BEGIN
    SELECT count(*) INTO vForeignTables
      FROM pg_class c
      JOIN pg_namespace n ON n."oid" = c."relnamespace"
      JOIN pg_roles     r ON r."oid" = c."relowner"
     WHERE n."nspname" = 'public'
       AND c."relkind" IN ('r', 'p')
       AND r."rolname" <> 'medicitasOwner';

    SELECT count(*) INTO vForeignFunctions
      FROM pg_proc p
      JOIN pg_namespace n ON n."oid" = p."pronamespace"
      JOIN pg_roles     r ON r."oid" = p."proowner"
      LEFT JOIN pg_depend d
             ON d."objid" = p."oid"
            AND d."classid" = 'pg_proc'::regclass
            AND d."deptype" = 'e'
     WHERE n."nspname" = 'public'
       AND d."objid" IS NULL
       AND r."rolname" <> 'medicitasOwner';

    IF vForeignTables > 0 OR vForeignFunctions > 0 THEN
        RAISE EXCEPTION
            'Propiedad incorrecta: % tablas y % funciones no pertenecen a medicitasOwner',
            vForeignTables, vForeignFunctions;
    END IF;
END
$$;