-- =============================================================================
-- MediCitas · 11 · Privilegios de menor privilegio
-- =============================================================================

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

DO $$
DECLARE
    vFunction record;
BEGIN
    FOR vFunction IN
        SELECT p."oid"::regprocedure AS "signature"
          FROM pg_proc p
          JOIN pg_namespace n ON n."oid" = p."pronamespace"
          JOIN pg_roles    r ON r."oid" = p."proowner"
         WHERE n."nspname" = 'public'
           AND r."rolname" = 'medicitasOwner'
    LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', vFunction."signature");
    END LOOP;
END
$$;

GRANT USAGE ON SCHEMA public TO
    "medicitasPlatform", "medicitasClinicAdmin",
    "medicitasReception", "medicitasProfessional";

-- -----------------------------------------------------------------------------
-- Catalogos de referencia
-- -----------------------------------------------------------------------------
GRANT SELECT ON "roles" TO "medicitasPlatform";

GRANT SELECT ON
    "roles", "specialties", "appointmentStatuses",
    "appointmentStatusTransitions", "auditActions"
TO "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";

-- -----------------------------------------------------------------------------
-- clinics · RF1
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON "clinics" TO "medicitasPlatform";
GRANT SELECT                 ON "clinics" TO
    "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";

-- -----------------------------------------------------------------------------
-- users · RF1, RF2
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON "users" TO "medicitasPlatform";
GRANT SELECT, INSERT, UPDATE ON "users" TO "medicitasClinicAdmin";

-- -----------------------------------------------------------------------------
-- professionals, services, professionalServices · RF3, RF4
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE         ON "professionals"        TO "medicitasClinicAdmin";
GRANT SELECT, INSERT, UPDATE         ON "services"             TO "medicitasClinicAdmin";
GRANT SELECT, INSERT,         DELETE ON "professionalServices" TO "medicitasClinicAdmin";

GRANT SELECT ON "professionals", "services", "professionalServices"
TO "medicitasReception", "medicitasProfessional";

-- -----------------------------------------------------------------------------
-- workingHours, scheduleBlocks · RF5, RF6
-- -----------------------------------------------------------------------------
-- edita, y por eso la tabla tampoco tiene "updatedAt".
GRANT SELECT, INSERT, UPDATE, DELETE ON "workingHours"   TO "medicitasClinicAdmin", "medicitasProfessional";
GRANT SELECT, INSERT,         DELETE ON "scheduleBlocks" TO "medicitasClinicAdmin", "medicitasProfessional";
GRANT SELECT                         ON "workingHours", "scheduleBlocks" TO "medicitasReception";

-- -----------------------------------------------------------------------------
-- patients · RF14
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON "patients" TO "medicitasClinicAdmin", "medicitasReception";
GRANT SELECT                 ON "patients" TO "medicitasProfessional";

-- -----------------------------------------------------------------------------
-- appointments · RF9 a RF13, RF16, RF20, RF21
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON "appointments" TO "medicitasClinicAdmin", "medicitasReception";

GRANT SELECT ON "appointments" TO "medicitasProfessional";
GRANT UPDATE ("appointmentStatusPK", "outcomeRecordedAt", "outcomeRecordedByUserID")
    ON "appointments" TO "medicitasProfessional";

-- -----------------------------------------------------------------------------
-- clinicalNotes · RF15, el dato mas sensible
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE ON "clinicalNotes" TO "medicitasProfessional";

-- -----------------------------------------------------------------------------
-- auditLogs · RF18, RF19, I6
-- -----------------------------------------------------------------------------
GRANT INSERT ON "auditLogs" TO
    "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT SELECT ON "auditLogs" TO "medicitasClinicAdmin";

REVOKE UPDATE, DELETE, TRUNCATE ON "auditLogs" FROM
    "medicitasPlatform", "medicitasClinicAdmin",
    "medicitasReception", "medicitasProfessional";

GRANT SELECT ON "auditChainHeads" TO "medicitasClinicAdmin";

-- -----------------------------------------------------------------------------
-- Funciones
-- -----------------------------------------------------------------------------
GRANT EXECUTE ON FUNCTION "currentClinicID"()       TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT EXECUTE ON FUNCTION "currentRoleCode"()       TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT EXECUTE ON FUNCTION "currentUserID"()         TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT EXECUTE ON FUNCTION "currentProfessionalID"() TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT EXECUTE ON FUNCTION "isPlatformAdmin"()       TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";

-- RF17
GRANT EXECUTE ON FUNCTION "resolveIdentity"(text) TO
    "medicitasPlatform", "medicitasClinicAdmin",
    "medicitasReception", "medicitasProfessional";


GRANT EXECUTE ON FUNCTION "verifyAuditChain"(uuid)      TO "medicitasClinicAdmin";
GRANT EXECUTE ON FUNCTION "auditGenesisHash"(uuid)      TO "medicitasClinicAdmin";
GRANT EXECUTE ON FUNCTION "auditRowHash"(text, bytea)   TO "medicitasClinicAdmin";
GRANT EXECUTE ON FUNCTION "auditCanonicalPayload"(uuid, bigint, timestamptz, uuid, text, text, text, uuid, uuid, uuid, jsonb)
                                                        TO "medicitasClinicAdmin";
