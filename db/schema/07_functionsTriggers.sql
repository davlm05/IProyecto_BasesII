-- =============================================================================
-- MediCitas · 07 · Funciones y triggers de dominio
-- =============================================================================

-- -----------------------------------------------------------------------------
-- setUpdatedAt · sello de modificacion generico
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION "setUpdatedAt"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    NEW."updatedAt" := now();
    RETURN NEW;
END;
$fn$;

-- -----------------------------------------------------------------------------
-- clinicsValidateTimeZone - RF1
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION "clinicsValidateTimeZone"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_timezone_names WHERE name = NEW."timeZone") THEN
        RAISE EXCEPTION 'Zona horaria IANA desconocida: %', NEW."timeZone"
            USING ERRCODE = 'MC008';
    END IF;
    RETURN NEW;
END;
$fn$;

CREATE TRIGGER "clinicsBiu10ValidateTimeZone"
    BEFORE INSERT OR UPDATE OF "timeZone" ON "clinics"
    FOR EACH ROW EXECUTE FUNCTION "clinicsValidateTimeZone"();

CREATE TRIGGER "clinicsBu90SetUpdatedAt"
    BEFORE UPDATE ON "clinics"
    FOR EACH ROW EXECUTE FUNCTION "setUpdatedAt"();

-- -----------------------------------------------------------------------------
-- patientsValidateBirthDate - RF14
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION "patientsValidateBirthDate"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    IF NEW."birthDate" > CURRENT_DATE THEN
        RAISE EXCEPTION 'La fecha de nacimiento no puede estar en el futuro: %', NEW."birthDate"
            USING ERRCODE = 'MC009';
    END IF;
    RETURN NEW;
END;
$fn$;

CREATE TRIGGER "patientsBiu10ValidateBirthDate"
    BEFORE INSERT OR UPDATE OF "birthDate" ON "patients"
    FOR EACH ROW EXECUTE FUNCTION "patientsValidateBirthDate"();

CREATE TRIGGER "patientsBu90SetUpdatedAt"
    BEFORE UPDATE ON "patients"
    FOR EACH ROW EXECUTE FUNCTION "setUpdatedAt"();

-- =============================================================================
-- appointments - triggers de INSERT (la reserva de RF9)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- I4 - appointmentsAssignTiming
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION "appointmentsAssignTiming"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
DECLARE
    vServiceDuration smallint;
BEGIN
    SELECT s."durationMinutes"
      INTO vServiceDuration
      FROM "services" s
     WHERE s."clinicID"  = NEW."clinicID"
       AND s."serviceID" = NEW."serviceID";

    IF vServiceDuration IS NULL THEN
        RAISE EXCEPTION 'El servicio % no existe en la clinica %',
            NEW."serviceID", NEW."clinicID"
            USING ERRCODE = '23503';
    END IF;

    NEW."durationMinutes" := vServiceDuration;
    NEW."endAt"           := NEW."startAt" + make_interval(mins => vServiceDuration);
    RETURN NEW;
END;
$fn$;

-- -----------------------------------------------------------------------------
-- RF4 - appointmentsValidateProfessionalService
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION "appointmentsValidateProfessionalService"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM "professionalServices" ps
         WHERE ps."clinicID"       = NEW."clinicID"
           AND ps."professionalID" = NEW."professionalID"
           AND ps."serviceID"      = NEW."serviceID"
    ) THEN
        RAISE EXCEPTION 'El profesional % no esta habilitado para el servicio %',
            NEW."professionalID", NEW."serviceID"
            USING ERRCODE = 'MC005';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM "professionals" p
         WHERE p."clinicID"       = NEW."clinicID"
           AND p."professionalID" = NEW."professionalID"
           AND p."isActive"
    ) THEN
        RAISE EXCEPTION 'El profesional % no esta activo', NEW."professionalID"
            USING ERRCODE = 'MC005';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM "services" s
         WHERE s."clinicID"  = NEW."clinicID"
           AND s."serviceID" = NEW."serviceID"
           AND s."isActive"
    ) THEN
        RAISE EXCEPTION 'El servicio % no esta activo', NEW."serviceID"
            USING ERRCODE = 'MC005';
    END IF;

    RETURN NEW;
END;
$fn$;

-- -----------------------------------------------------------------------------
-- I3 - appointmentsValidateSchedule
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION "appointmentsValidateSchedule"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
DECLARE
    vClinicTimeZone   text;
    vAppointmentEnd   timestamptz;
    vStartLocal       timestamp;
    vEndLocal         timestamp;
    vEndTimeToCompare time;
    vIsCovered        boolean;
BEGIN
    SELECT c."timeZone" INTO vClinicTimeZone
      FROM "clinics" c
     WHERE c."clinicID" = NEW."clinicID";

    IF vClinicTimeZone IS NULL THEN
        RAISE EXCEPTION 'La clinica % no existe', NEW."clinicID"
            USING ERRCODE = '23503';
    END IF;

    vAppointmentEnd := NEW."endAt";
    vStartLocal     := NEW."startAt"   AT TIME ZONE vClinicTimeZone;
    vEndLocal       := vAppointmentEnd AT TIME ZONE vClinicTimeZone;

    IF vEndLocal::date > vStartLocal::date AND vEndLocal::time <> time '00:00:00' THEN
        RAISE EXCEPTION 'La cita cruza la medianoche local de la clinica (inicio %, fin %)',
            vStartLocal, vEndLocal
            USING ERRCODE = 'MC010';
    END IF;

    vEndTimeToCompare := CASE
        WHEN vEndLocal::date > vStartLocal::date THEN time '24:00:00'
        ELSE vEndLocal::time
    END;

    SELECT EXISTS (
        SELECT 1
          FROM "workingHours" wh
         WHERE wh."professionalID" = NEW."professionalID"
           AND wh."weekday"        = EXTRACT(ISODOW FROM vStartLocal)::smallint
           AND wh."startTimeLocal" <= vStartLocal::time
           AND wh."endTimeLocal"   >= vEndTimeToCompare
    ) INTO vIsCovered;

    IF NOT vIsCovered THEN
        RAISE EXCEPTION 'La cita no cae dentro del horario de atencion del profesional (hora local %)',
            vStartLocal
            USING ERRCODE = 'MC001';
    END IF;

    IF EXISTS (
        SELECT 1
          FROM "scheduleBlocks" sb
         WHERE sb."professionalID" = NEW."professionalID"
           AND tstzrange(sb."startAt", sb."endAt", '[)')
            && tstzrange(NEW."startAt", vAppointmentEnd, '[)')
    ) THEN
        RAISE EXCEPTION 'La cita cae dentro de un bloqueo de agenda del profesional'
            USING ERRCODE = 'MC002';
    END IF;

    RETURN NEW;
END;
$fn$;

CREATE TRIGGER "appointmentsBi10AssignTiming"
    BEFORE INSERT ON "appointments"
    FOR EACH ROW EXECUTE FUNCTION "appointmentsAssignTiming"();

CREATE TRIGGER "appointmentsBi20ValidateProfessionalService"
    BEFORE INSERT ON "appointments"
    FOR EACH ROW EXECUTE FUNCTION "appointmentsValidateProfessionalService"();

CREATE TRIGGER "appointmentsBi30ValidateSchedule"
    BEFORE INSERT ON "appointments"
    FOR EACH ROW EXECUTE FUNCTION "appointmentsValidateSchedule"();

-- =============================================================================
-- appointments - triggers de UPDATE (RF10 a RF13)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- RF10 e I4 - appointmentsPreventImmutableChange
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION "appointmentsPreventImmutableChange"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    IF NEW."durationMinutes" <> OLD."durationMinutes"
    OR NEW."endAt"           <> OLD."endAt" THEN
        RAISE EXCEPTION 'La duracion de una cita la determina el servicio y no se altera (I4)'
            USING ERRCODE = 'MC011';
    END IF;

    IF NEW."appointmentID"   <> OLD."appointmentID"
    OR NEW."clinicID"        <> OLD."clinicID"
    OR NEW."patientID"       <> OLD."patientID"
    OR NEW."professionalID"  <> OLD."professionalID"
    OR NEW."serviceID"       <> OLD."serviceID"
    OR NEW."startAt"         <> OLD."startAt"
    OR NEW."createdByUserID" <> OLD."createdByUserID"
    OR NEW."createdAt"       <> OLD."createdAt" THEN
        RAISE EXCEPTION 'Una cita no se mueve ni se reasigna: reprograme creando una cita nueva (RF10)'
            USING ERRCODE = 'MC004';
    END IF;

    RETURN NEW;
END;
$fn$;

-- -----------------------------------------------------------------------------
-- RF13 - appointmentsValidateStatusTransition
-- --------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION "appointmentsValidateStatusTransition"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    IF NEW."appointmentStatusPK" = OLD."appointmentStatusPK" THEN
        RETURN NEW;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM "appointmentStatusTransitions" t
         WHERE t."fromAppointmentStatusPK" = OLD."appointmentStatusPK"
           AND t."toAppointmentStatusPK"   = NEW."appointmentStatusPK"
    ) THEN
        RAISE EXCEPTION 'Transicion de estado no permitida: % -> %',
            OLD."appointmentStatusPK", NEW."appointmentStatusPK"
            USING ERRCODE = 'MC003';
    END IF;

    RETURN NEW;
END;
$fn$;

CREATE TRIGGER "appointmentsBu10PreventImmutableChange"
    BEFORE UPDATE ON "appointments"
    FOR EACH ROW EXECUTE FUNCTION "appointmentsPreventImmutableChange"();

CREATE TRIGGER "appointmentsBu20ValidateStatusTransition"
    BEFORE UPDATE ON "appointments"
    FOR EACH ROW EXECUTE FUNCTION "appointmentsValidateStatusTransition"();

CREATE TRIGGER "appointmentsBu90SetUpdatedAt"
    BEFORE UPDATE ON "appointments"
    FOR EACH ROW EXECUTE FUNCTION "setUpdatedAt"();

-- =============================================================================
-- clinicalNotes - RF15
-- =============================================================================

CREATE OR REPLACE FUNCTION "clinicalNotesValidateAppointmentAttended"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM "appointments" a
         WHERE a."clinicID"            = NEW."clinicID"
           AND a."appointmentID"       = NEW."appointmentID"
           AND a."appointmentStatusPK" = 'attended'
    ) THEN
        RAISE EXCEPTION 'Solo se adjunta nota clinica a una cita en estado attended (RF15)'
            USING ERRCODE = 'MC007';
    END IF;
    RETURN NEW;
END;
$fn$;

CREATE TRIGGER "clinicalNotesBiu10ValidateAppointmentAttended"
    BEFORE INSERT OR UPDATE ON "clinicalNotes"
    FOR EACH ROW EXECUTE FUNCTION "clinicalNotesValidateAppointmentAttended"();

CREATE TRIGGER "clinicalNotesBu90SetUpdatedAt"
    BEFORE UPDATE ON "clinicalNotes"
    FOR EACH ROW EXECUTE FUNCTION "setUpdatedAt"();

-- =============================================================================
-- I6 - la bitacora no admite modificacion ni borrado
-- =============================================================================
CREATE OR REPLACE FUNCTION "auditLogsPreventMutation"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    RAISE EXCEPTION 'La bitacora de auditoria es append-only: % no esta permitido (I6)', TG_OP
        USING ERRCODE = 'MC006';
END;
$fn$;

CREATE TRIGGER "auditLogsBud10PreventMutation"
    BEFORE UPDATE OR DELETE ON "auditLogs"
    FOR EACH ROW EXECUTE FUNCTION "auditLogsPreventMutation"();

-- -----------------------------------------------------------------------------
-- Resto de sellos de modificacion
-- -----------------------------------------------------------------------------
CREATE TRIGGER "usersBu90SetUpdatedAt"
    BEFORE UPDATE ON "users"
    FOR EACH ROW EXECUTE FUNCTION "setUpdatedAt"();

CREATE TRIGGER "professionalsBu90SetUpdatedAt"
    BEFORE UPDATE ON "professionals"
    FOR EACH ROW EXECUTE FUNCTION "setUpdatedAt"();

CREATE TRIGGER "servicesBu90SetUpdatedAt"
    BEFORE UPDATE ON "services"
    FOR EACH ROW EXECUTE FUNCTION "setUpdatedAt"();

CREATE TRIGGER "workingHoursBu90SetUpdatedAt"
    BEFORE UPDATE ON "workingHours"
    FOR EACH ROW EXECUTE FUNCTION "setUpdatedAt"();
