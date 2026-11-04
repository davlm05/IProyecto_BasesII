-- =============================================================================
-- MediCitas · 10 · Row-Level Security 
-- =============================================================================

-- -----------------------------------------------------------------------------
-- clinics · RF1
-- -----------------------------------------------------------------------------
ALTER TABLE "clinics" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "clinicsPlatformAll" ON "clinics"
    FOR ALL
    USING ("isPlatformAdmin"())
    WITH CHECK ("isPlatformAdmin"());

CREATE POLICY "clinicsTenantSelect" ON "clinics"
    FOR SELECT
    USING ("clinicID" = "currentClinicID"());

-- -----------------------------------------------------------------------------
-- users · RF1, RF2
-- -----------------------------------------------------------------------------
ALTER TABLE "users" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "usersPlatformAll" ON "users"
    FOR ALL
    USING ("isPlatformAdmin"())
    WITH CHECK ("isPlatformAdmin"());

CREATE POLICY "usersTenantAll" ON "users"
    FOR ALL
    USING ("clinicID" = "currentClinicID"())
    WITH CHECK ("clinicID" = "currentClinicID"());

-- -----------------------------------------------------------------------------
-- Tablas de tenant con aislamiento simple
-- -----------------------------------------------------------------------------
ALTER TABLE "professionals"        ENABLE ROW LEVEL SECURITY;
ALTER TABLE "services"             ENABLE ROW LEVEL SECURITY;
ALTER TABLE "professionalServices" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "workingHours"         ENABLE ROW LEVEL SECURITY;
ALTER TABLE "scheduleBlocks"       ENABLE ROW LEVEL SECURITY;
ALTER TABLE "patients"             ENABLE ROW LEVEL SECURITY;
ALTER TABLE "appointments"         ENABLE ROW LEVEL SECURITY;
ALTER TABLE "auditChainHeads"      ENABLE ROW LEVEL SECURITY;

-- RF4
CREATE POLICY "professionalsTenantIsolation" ON "professionals"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

-- RF3
CREATE POLICY "servicesTenantIsolation" ON "services"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

-- RF4
CREATE POLICY "professionalServicesTenantIsolation" ON "professionalServices"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

-- RF14
CREATE POLICY "patientsTenantIsolation" ON "patients"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "appointmentsTenantIsolation" ON "appointments"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "auditChainHeadsTenantIsolation" ON "auditChainHeads"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

-- -----------------------------------------------------------------------------
-- workingHours y scheduleBlocks - fila "Horarios y bloqueos (RF5, RF6)"
-- -----------------------------------------------------------------------------
CREATE POLICY "workingHoursTenantSelect" ON "workingHours"
    FOR SELECT USING ("clinicID" = "currentClinicID"());

CREATE POLICY "workingHoursClinicAdminWrite" ON "workingHours"
    FOR ALL TO "medicitasClinicAdmin"
    USING ("clinicID" = "currentClinicID"())
    WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "workingHoursProfessionalOwnWrite" ON "workingHours"
    FOR ALL TO "medicitasProfessional"
    USING ("clinicID" = "currentClinicID"()
       AND "professionalID" = "currentProfessionalID"())
    WITH CHECK ("clinicID" = "currentClinicID"()
            AND "professionalID" = "currentProfessionalID"());

CREATE POLICY "scheduleBlocksTenantSelect" ON "scheduleBlocks"
    FOR SELECT USING ("clinicID" = "currentClinicID"());

CREATE POLICY "scheduleBlocksClinicAdminWrite" ON "scheduleBlocks"
    FOR ALL TO "medicitasClinicAdmin"
    USING ("clinicID" = "currentClinicID"())
    WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "scheduleBlocksProfessionalOwnWrite" ON "scheduleBlocks"
    FOR ALL TO "medicitasProfessional"
    USING ("clinicID" = "currentClinicID"()
       AND "professionalID" = "currentProfessionalID"())
    WITH CHECK ("clinicID" = "currentClinicID"()
            AND "professionalID" = "currentProfessionalID"());

-- -----------------------------------------------------------------------------
-- clinicalNotes - RF15 y la fila "Nota clinica" de la matriz
-- -----------------------------------------------------------------------------
ALTER TABLE "clinicalNotes" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "clinicalNotesOwnByProfessional" ON "clinicalNotes"
    FOR ALL
    TO "medicitasProfessional"
    USING ("clinicID" = "currentClinicID"()
       AND "professionalID" = "currentProfessionalID"())
    WITH CHECK ("clinicID" = "currentClinicID"()
            AND "professionalID" = "currentProfessionalID"());

-- -----------------------------------------------------------------------------
-- auditLogs - RF18 escribe, RF19 lee
-- -----------------------------------------------------------------------------
ALTER TABLE "auditLogs" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "auditLogsTenantInsert" ON "auditLogs"
    FOR INSERT
    WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "auditLogsClinicAdminSelect" ON "auditLogs"
    FOR SELECT
    TO "medicitasClinicAdmin"
    USING ("clinicID" = "currentClinicID"());
