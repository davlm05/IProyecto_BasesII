-- =============================================================================
-- MediCitas · 12 · Credenciales de los cinco perfiles y comprobacion final
-- =============================================================================

-- medicitasOwner - migraciones y semilla. 
ALTER ROLE "medicitasOwner"        WITH LOGIN PASSWORD 'ownerPassword';

ALTER ROLE "medicitasPlatform"     WITH LOGIN PASSWORD 'platformPassword';
ALTER ROLE "medicitasClinicAdmin"  WITH LOGIN PASSWORD 'clinicAdminPassword';
ALTER ROLE "medicitasReception"    WITH LOGIN PASSWORD 'receptionPassword';
ALTER ROLE "medicitasProfessional" WITH LOGIN PASSWORD 'professionalPassword';

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
