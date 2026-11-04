
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'timeRange') THEN
        CREATE TYPE "timeRange" AS RANGE (subtype = time);
    END IF;
END
$$;

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

CREATE TABLE "roles" (
    "rolePK"      text PRIMARY KEY,
    "name"        text NOT NULL,
    "description" text NOT NULL,
    CONSTRAINT "rolesPKFormat" CHECK ("rolePK" ~ '^[a-z][a-zA-Z]{2,39}$')
);

INSERT INTO "roles" ("rolePK", "name", "description") VALUES
    ('platformAdmin', 'Administrador de plataforma',
     'Pertenece a la empresa que vende el servicio. Da de alta clinicas y su primer administrador. No accede a datos clinicos de ninguna clinica.'),
    ('clinicAdmin',   'Administrador de clinica',
     'Gestiona usuarios, profesionales, servicios, horarios y bloqueos de su clinica. Unico que consulta la bitacora de auditoria.'),
    ('reception',     'Recepcion',
     'Registra pacientes y opera la agenda: reserva, reprograma, cancela y registra el desenlace de las citas.'),
    ('professional',  'Profesional de salud',
     'Consulta su propia agenda y redacta la nota clinica de las citas que atendio.');

CREATE TABLE "specialties" (
    "specialtyID" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "code"        text NOT NULL UNIQUE,
    "name"        text NOT NULL,
    CONSTRAINT "specialtiesCodeFormat" CHECK ("code" ~ '^[a-z][a-zA-Z]{2,39}$')
);

INSERT INTO "specialties" ("code", "name") VALUES
    ('generalMedicine', 'Medicina general'),
    ('pediatrics',      'Pediatria'),
    ('dermatology',     'Dermatologia'),
    ('cardiology',      'Cardiologia'),
    ('nutrition',       'Nutricion'),
    ('psychology',      'Psicologia'),
    ('dentistry',       'Odontologia'),
    ('ophthalmology',   'Oftalmologia');

CREATE TABLE "appointmentStatuses" (
    "appointmentStatusPK" text    PRIMARY KEY,
    "name"                text    NOT NULL,
    "isFinal"             boolean NOT NULL,
    "occupiesSlot"        boolean NOT NULL,
    CONSTRAINT "appointmentStatusesPKFormat" CHECK ("appointmentStatusPK" ~ '^[a-z][a-zA-Z]{2,39}$')
);

INSERT INTO "appointmentStatuses" ("appointmentStatusPK", "name", "isFinal", "occupiesSlot") VALUES
    ('reserved',    'Reservada',    false, true),
    ('attended',    'Atendida',     true,  true),
    ('absent',      'Ausente',      true,  true),
    ('cancelled',   'Cancelada',    true,  false),
    ('rescheduled', 'Reprogramada', true,  false);

CREATE TABLE "appointmentStatusTransitions" (
    "fromAppointmentStatusPK" text NOT NULL REFERENCES "appointmentStatuses" ("appointmentStatusPK"),
    "toAppointmentStatusPK"   text NOT NULL REFERENCES "appointmentStatuses" ("appointmentStatusPK"),
    CONSTRAINT "appointmentStatusTransitionsPk"
        PRIMARY KEY ("fromAppointmentStatusPK", "toAppointmentStatusPK"),
    CONSTRAINT "appointmentStatusTransitionsNotReflexive"
        CHECK ("fromAppointmentStatusPK" <> "toAppointmentStatusPK")
);

INSERT INTO "appointmentStatusTransitions" ("fromAppointmentStatusPK", "toAppointmentStatusPK") VALUES
    ('reserved', 'attended'),
    ('reserved', 'absent'),
    ('reserved', 'cancelled'),
    ('reserved', 'rescheduled');

CREATE TABLE "auditActions" (
    "auditActionPK" text    PRIMARY KEY,
    "name"          text    NOT NULL,
    "isWrite"       boolean NOT NULL,
    CONSTRAINT "auditActionsPKFormat" CHECK ("auditActionPK" ~ '^[a-z][a-zA-Z]{2,39}$')
);

INSERT INTO "auditActions" ("auditActionPK", "name", "isWrite") VALUES
    ('readClinicalNote',    'Lectura de nota clinica',              false),
    ('writeClinicalNote',   'Escritura de nota clinica',            true),
    ('readPatientContact',  'Lectura de datos de contacto',         false),
    ('writePatientContact', 'Escritura de datos de contacto',       true),
    ('readPatientHistory',  'Lectura del historial del paciente',   false),
    ('readAuditLog',        'Consulta de la bitacora de auditoria', false);

CREATE TABLE "clinics" (
    "clinicID"  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "code"      text        NOT NULL,
    "name"      text        NOT NULL,
    "timeZone"  text        NOT NULL,
    "isActive"  boolean     NOT NULL DEFAULT true,
    "createdAt" timestamptz NOT NULL DEFAULT now(),
    "updatedAt" timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "clinicsCodeUnique"   UNIQUE ("code"),
    CONSTRAINT "clinicsCodeFormat"   CHECK ("code" ~ '^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$'),
    CONSTRAINT "clinicsNameNotBlank" CHECK (length(btrim("name")) > 0)
);

CREATE TABLE "users" (
    "userID"                  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"                uuid        REFERENCES "clinics" ("clinicID"),
    "identityProviderSubject" text        NOT NULL,
    "rolePK"                  text        NOT NULL REFERENCES "roles" ("rolePK"),
    "isActive"                boolean     NOT NULL DEFAULT true,
    "deactivatedAt"           timestamptz,
    "createdAt"               timestamptz NOT NULL DEFAULT now(),
    "updatedAt"               timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "usersSubjectUnique" UNIQUE ("identityProviderSubject"),
    CONSTRAINT "usersClinicUnique"  UNIQUE ("clinicID", "userID"),

    CONSTRAINT "usersTenancyByRole" CHECK (
        ("rolePK" =  'platformAdmin' AND "clinicID" IS NULL)
     OR ("rolePK" <> 'platformAdmin' AND "clinicID" IS NOT NULL)
    ),

    CONSTRAINT "usersDeactivationConsistent" CHECK (
        ("isActive" AND "deactivatedAt" IS NULL)
     OR (NOT "isActive" AND "deactivatedAt" IS NOT NULL)
    )
);

CREATE TABLE "professionals" (
    "professionalID" uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"       uuid        NOT NULL REFERENCES "clinics" ("clinicID"),
    "userID"         uuid        NOT NULL,
    "specialtyID"    uuid        NOT NULL REFERENCES "specialties" ("specialtyID"),
    "fullName"       text        NOT NULL,
    "licenseCode"    text,
    "isActive"       boolean     NOT NULL DEFAULT true,
    "createdAt"      timestamptz NOT NULL DEFAULT now(),
    "updatedAt"      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "professionalsClinicUnique"    UNIQUE ("clinicID", "professionalID"),
    CONSTRAINT "professionalsSpecialtyUnique" UNIQUE ("clinicID", "professionalID", "specialtyID"),

    CONSTRAINT "professionalsUserUnique"      UNIQUE ("userID"),
    
    CONSTRAINT "professionalsUserSameClinic"  FOREIGN KEY ("clinicID", "userID")
        REFERENCES "users" ("clinicID", "userID"), 
    CONSTRAINT "professionalsLicenseUnique"   UNIQUE ("clinicID", "licenseCode"),
    CONSTRAINT "professionalsNameNotBlank"    CHECK (length(btrim("fullName")) > 0)
);

CREATE TABLE "services" (
    "serviceID"       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"        uuid        NOT NULL REFERENCES "clinics" ("clinicID"),
    "name"            text        NOT NULL,
    "description"     text,
    "durationMinutes" smallint    NOT NULL,
    "specialtyID"     uuid        NOT NULL REFERENCES "specialties" ("specialtyID"),
    "isActive"        boolean     NOT NULL DEFAULT true,
    "createdAt"       timestamptz NOT NULL DEFAULT now(),
    "updatedAt"       timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "servicesClinicUnique"    UNIQUE ("clinicID", "serviceID"),
    CONSTRAINT "servicesSpecialtyUnique" UNIQUE ("clinicID", "serviceID", "specialtyID"),
    CONSTRAINT "servicesNameUnique"      UNIQUE ("clinicID", "name"),

    CONSTRAINT "servicesDurationRange"   CHECK ("durationMinutes" BETWEEN 5 AND 480),
    CONSTRAINT "servicesDurationStep"    CHECK ("durationMinutes" % 5 = 0),
    CONSTRAINT "servicesNameNotBlank"    CHECK (length(btrim("name")) > 0)
);

CREATE TABLE "professionalServices" (
    "clinicID"       uuid        NOT NULL,
    "professionalID" uuid        NOT NULL,
    "serviceID"      uuid        NOT NULL,
    "specialtyID"    uuid        NOT NULL,
    "createdAt"      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "professionalServicesPk" PRIMARY KEY ("clinicID", "professionalID", "serviceID"),

    CONSTRAINT "professionalServicesProfessionalFk"
        FOREIGN KEY ("clinicID", "professionalID", "specialtyID")
        REFERENCES "professionals" ("clinicID", "professionalID", "specialtyID")
        ON DELETE CASCADE,

    CONSTRAINT "professionalServicesServiceFk"
        FOREIGN KEY ("clinicID", "serviceID", "specialtyID")
        REFERENCES "services" ("clinicID", "serviceID", "specialtyID")
        ON DELETE CASCADE
);

CREATE TABLE "patients" (
    "patientID"  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"   uuid        NOT NULL REFERENCES "clinics" ("clinicID"),
    "nationalID" text        NOT NULL,
    "firstName"  text        NOT NULL,
    "lastName"   text        NOT NULL,
    "birthDate"  date        NOT NULL,
    "phone"      text,
    "email"      text,
    "isActive"   boolean     NOT NULL DEFAULT true,
    "createdAt"  timestamptz NOT NULL DEFAULT now(),
    "updatedAt"  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "patientsClinicUnique"     UNIQUE ("clinicID", "patientID"),

    CONSTRAINT "patientsNationalIDUnique" UNIQUE ("clinicID", "nationalID"),

    CONSTRAINT "patientsNationalIDFormat"    CHECK ("nationalID" ~ '^[A-Za-z0-9-]{5,30}$'),
    CONSTRAINT "patientsFirstNameNotBlank"   CHECK (length(btrim("firstName")) > 0),
    CONSTRAINT "patientsLastNameNotBlank"    CHECK (length(btrim("lastName")) > 0),

    CONSTRAINT "patientsBirthDateLowerBound" CHECK ("birthDate" >= DATE '1900-01-01'),
    CONSTRAINT "patientsEmailFormat" CHECK ("email" IS NULL OR "email" ~ '^[^@[:space:]]+@[^@[:space:]]+\.[A-Za-z]{2,}$'),
    CONSTRAINT "patientsPhoneFormat" CHECK ("phone" IS NULL OR "phone" ~ '^\+?[0-9 ()-]{7,20}$')
);

CREATE INDEX "patientsClinicLastNameIdx"
    ON "patients" ("clinicID", lower("lastName"), lower("firstName"))
    WHERE "isActive";

CREATE TABLE "workingHours" (
    "workingHourID"  uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"       uuid        NOT NULL,
    "professionalID" uuid        NOT NULL,
    "weekday"        smallint    NOT NULL,
    "startTimeLocal" time        NOT NULL,
    "endTimeLocal"   time        NOT NULL,
    "createdAt"      timestamptz NOT NULL DEFAULT now(),
    "updatedAt"      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "workingHoursClinicUnique" UNIQUE ("clinicID", "workingHourID"),

    CONSTRAINT "workingHoursProfessionalFk"
        FOREIGN KEY ("clinicID", "professionalID")
        REFERENCES "professionals" ("clinicID", "professionalID")
        ON DELETE CASCADE,

    CONSTRAINT "workingHoursWeekdayRange" CHECK ("weekday" BETWEEN 1 AND 7),
    CONSTRAINT "workingHoursOrder"        CHECK ("startTimeLocal" < "endTimeLocal"),

    CONSTRAINT "workingHoursNoOverlap" EXCLUDE USING gist (
        "professionalID" WITH =,
        "weekday"        WITH =,
        "timeRange"("startTimeLocal", "endTimeLocal", '[)') WITH &&
    )
);

CREATE TABLE "scheduleBlocks" (
    "scheduleBlockID" uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"        uuid        NOT NULL,
    "professionalID"  uuid        NOT NULL,
    "startAt"         timestamptz NOT NULL,
    "endAt"           timestamptz NOT NULL,
    "reason"          text        NOT NULL,
    "userID"          uuid        NOT NULL,
    "createdAt"       timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "scheduleBlocksClinicUnique" UNIQUE ("clinicID", "scheduleBlockID"),

    CONSTRAINT "scheduleBlocksProfessionalFk"
        FOREIGN KEY ("clinicID", "professionalID")
        REFERENCES "professionals" ("clinicID", "professionalID")
        ON DELETE CASCADE,

    CONSTRAINT "scheduleBlocksUserFk"
        FOREIGN KEY ("clinicID", "userID")
        REFERENCES "users" ("clinicID", "userID"),

    CONSTRAINT "scheduleBlocksOrder"          CHECK ("startAt" < "endAt"),
    CONSTRAINT "scheduleBlocksReasonNotBlank" CHECK (length(btrim("reason")) > 0)
);

CREATE INDEX "scheduleBlocksPeriodIdx"
    ON "scheduleBlocks" USING gist (
        "professionalID",
        tstzrange("startAt", "endAt", '[)')
    );

CREATE TABLE "appointments" (
    "appointmentID"       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"            uuid        NOT NULL REFERENCES "clinics" ("clinicID"),

    "patientID"           uuid        NOT NULL,
    "professionalID"      uuid        NOT NULL,
    "serviceID"           uuid        NOT NULL,
    "startAt"             timestamptz NOT NULL,
    "durationMinutes"     smallint    NOT NULL,
    "endAt"               timestamptz NOT NULL,
    "appointmentStatusPK" text        NOT NULL DEFAULT 'reserved'
        REFERENCES "appointmentStatuses" ("appointmentStatusPK"),

    "createdByUserID" uuid        NOT NULL,
    "createdAt"       timestamptz NOT NULL DEFAULT now(),
    "updatedAt"       timestamptz NOT NULL DEFAULT now(),

    "cancelledAt"        timestamptz,
    "cancelledByUserID"  uuid,
    "cancellationReason" text,

    "outcomeRecordedAt"       timestamptz,
    "outcomeRecordedByUserID" uuid,

    "rescheduledToAppointmentID" uuid,

    CONSTRAINT "appointmentsClinicUnique"       UNIQUE ("clinicID", "appointmentID"),
    CONSTRAINT "appointmentsProfessionalUnique" UNIQUE ("clinicID", "appointmentID", "professionalID"),
    CONSTRAINT "appointmentsPatientUnique"      UNIQUE ("clinicID", "appointmentID", "patientID"),

    CONSTRAINT "appointmentsPatientFk"
        FOREIGN KEY ("clinicID", "patientID")
        REFERENCES "patients" ("clinicID", "patientID"),

    CONSTRAINT "appointmentsProfessionalFk"
        FOREIGN KEY ("clinicID", "professionalID")
        REFERENCES "professionals" ("clinicID", "professionalID"),

    CONSTRAINT "appointmentsServiceFk"
        FOREIGN KEY ("clinicID", "serviceID")
        REFERENCES "services" ("clinicID", "serviceID"),

    CONSTRAINT "appointmentsCreatorFk"
        FOREIGN KEY ("clinicID", "createdByUserID")
        REFERENCES "users" ("clinicID", "userID"),

    CONSTRAINT "appointmentsCancellerFk"
        FOREIGN KEY ("clinicID", "cancelledByUserID")
        REFERENCES "users" ("clinicID", "userID"),

    CONSTRAINT "appointmentsOutcomeRecorderFk"
        FOREIGN KEY ("clinicID", "outcomeRecordedByUserID")
        REFERENCES "users" ("clinicID", "userID"),

    CONSTRAINT "appointmentsRescheduledToFk"
        FOREIGN KEY ("clinicID", "rescheduledToAppointmentID", "patientID")
        REFERENCES "appointments" ("clinicID", "appointmentID", "patientID"),

    CONSTRAINT "appointmentsRescheduledToUnique" UNIQUE ("rescheduledToAppointmentID"),
    CONSTRAINT "appointmentsNotSelfReschedule"
        CHECK ("rescheduledToAppointmentID" IS NULL OR "rescheduledToAppointmentID" <> "appointmentID"),

    CONSTRAINT "appointmentsDurationRange" CHECK ("durationMinutes" BETWEEN 5 AND 480),
    CONSTRAINT "appointmentsEndAfterStart" CHECK ("endAt" > "startAt"),

    CONSTRAINT "appointmentsCancellationConsistent" CHECK (
        ("appointmentStatusPK" = 'cancelled') = ("cancelledAt" IS NOT NULL)
    AND ("cancelledAt" IS NOT NULL)           = ("cancelledByUserID" IS NOT NULL)
    AND ("cancelledAt" IS NOT NULL)           = ("cancellationReason" IS NOT NULL)
    ),
    CONSTRAINT "appointmentsOutcomeConsistent" CHECK (
        ("appointmentStatusPK" IN ('attended', 'absent')) = ("outcomeRecordedAt" IS NOT NULL)
    AND ("outcomeRecordedAt" IS NOT NULL)                 = ("outcomeRecordedByUserID" IS NOT NULL)
    ),
    CONSTRAINT "appointmentsRescheduleConsistent" CHECK (
        ("appointmentStatusPK" = 'rescheduled') = ("rescheduledToAppointmentID" IS NOT NULL)
    ),

    CONSTRAINT "appointmentsOutcomeAfterStart" CHECK (
        "outcomeRecordedAt" IS NULL OR "outcomeRecordedAt" >= "startAt"
    ),
    CONSTRAINT "appointmentsCancellationReasonNotBlank" CHECK (
        "cancellationReason" IS NULL OR length(btrim("cancellationReason")) > 0
    ),

    CONSTRAINT "appointmentsProfessionalNoOverlap" EXCLUDE USING gist (
        "professionalID" WITH =,
        tstzrange("startAt", "endAt", '[)') WITH &&
    ) WHERE ("appointmentStatusPK" NOT IN ('cancelled', 'rescheduled')),

    CONSTRAINT "appointmentsPatientNoOverlap" EXCLUDE USING gist (
        "clinicID"  WITH =,
        "patientID" WITH =,
        tstzrange("startAt", "endAt", '[)') WITH &&
    ) WHERE ("appointmentStatusPK" NOT IN ('cancelled', 'rescheduled'))
);

CREATE INDEX "appointmentsClinicProfessionalStartIdx"
    ON "appointments" ("clinicID", "professionalID", "startAt")
    WHERE "appointmentStatusPK" NOT IN ('cancelled', 'rescheduled');

CREATE INDEX "appointmentsClinicStartIdx"
    ON "appointments" ("clinicID", "startAt")
    WHERE "appointmentStatusPK" NOT IN ('cancelled', 'rescheduled');

CREATE INDEX "appointmentsClinicPatientStartIdx"
    ON "appointments" ("clinicID", "patientID", "startAt" DESC);

CREATE INDEX "appointmentsClinicStatusStartIdx"
    ON "appointments" ("clinicID", "appointmentStatusPK", "startAt");

CREATE TABLE "clinicalNotes" (
    "clinicalNoteID" uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"       uuid        NOT NULL REFERENCES "clinics" ("clinicID"),
    "appointmentID"  uuid        NOT NULL,
    "professionalID" uuid        NOT NULL,
    "content"        text        NOT NULL,
    "createdAt"      timestamptz NOT NULL DEFAULT now(),
    "updatedAt"      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "clinicalNotesAppointmentUnique" UNIQUE ("appointmentID"),
    CONSTRAINT "clinicalNotesClinicUnique"      UNIQUE ("clinicID", "clinicalNoteID"),

    CONSTRAINT "clinicalNotesAuthorIsAttendingFk"
        FOREIGN KEY ("clinicID", "appointmentID", "professionalID")
        REFERENCES "appointments" ("clinicID", "appointmentID", "professionalID"),

    CONSTRAINT "clinicalNotesContentNotBlank" CHECK (length(btrim("content")) > 0)
);

CREATE TABLE "auditLogs" (
    "auditLogPK"    bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "clinicID"      uuid        NOT NULL REFERENCES "clinics" ("clinicID"),
    "sequenceNo"    bigint      NOT NULL,
    "occurredAt"    timestamptz NOT NULL DEFAULT clock_timestamp(),
    "userID"        uuid,
    "rolePK"        text        NOT NULL REFERENCES "roles" ("rolePK"),
    "auditActionPK" text        NOT NULL REFERENCES "auditActions" ("auditActionPK"),
    "entityType"    text        NOT NULL,
    "entityID"      uuid,
    "patientID"     uuid,
    "requestID"     uuid,
    "metadata"      jsonb       NOT NULL DEFAULT '{}'::jsonb,
    "previousHash"  bytea       NOT NULL,
    "rowHash"       bytea       NOT NULL,

    CONSTRAINT "auditLogsSequenceUnique"   UNIQUE ("clinicID", "sequenceNo"),
    CONSTRAINT "auditLogsSequencePositive" CHECK ("sequenceNo" > 0),

    CONSTRAINT "auditLogsUserFk"
        FOREIGN KEY ("clinicID", "userID")
        REFERENCES "users" ("clinicID", "userID"),

    CONSTRAINT "auditLogsPatientFk"
        FOREIGN KEY ("clinicID", "patientID")
        REFERENCES "patients" ("clinicID", "patientID"),

    CONSTRAINT "auditLogsEntityTypeNotBlank" CHECK (length(btrim("entityType")) > 0),

    CONSTRAINT "auditLogsHashLength" CHECK (
        length("previousHash") = 32 AND length("rowHash") = 32
    )
);

CREATE INDEX "auditLogsClinicOccurredAtIdx" ON "auditLogs" ("clinicID", "occurredAt" DESC);

CREATE INDEX "auditLogsClinicUserIdx"       ON "auditLogs" ("clinicID", "userID", "occurredAt" DESC);

CREATE INDEX "auditLogsClinicPatientIdx"    ON "auditLogs" ("clinicID", "patientID", "occurredAt" DESC)
    WHERE "patientID" IS NOT NULL;

CREATE TABLE "auditChainHeads" (
    "clinicID"       uuid        PRIMARY KEY REFERENCES "clinics" ("clinicID"),
    "lastSequenceNo" bigint      NOT NULL DEFAULT 0,
    "lastHash"       bytea       NOT NULL,
    "updatedAt"      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "auditChainHeadsSequenceNonNegative" CHECK ("lastSequenceNo" >= 0),
    CONSTRAINT "auditChainHeadsHashLength"          CHECK (length("lastHash") = 32)
);

CREATE OR REPLACE FUNCTION "setUpdatedAt"()
RETURNS trigger
LANGUAGE plpgsql
AS $fn$
BEGIN
    NEW."updatedAt" := now();
    RETURN NEW;
END;
$fn$;

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

CREATE OR REPLACE FUNCTION "auditCanonicalPayload"(
    "pClinicID"      uuid,
    "pSequenceNo"    bigint,
    "pOccurredAt"    timestamptz,
    "pUserID"        uuid,
    "pRolePK"        text,
    "pAuditActionPK" text,
    "pEntityType"    text,
    "pEntityID"      uuid,
    "pPatientID"     uuid,
    "pRequestID"     uuid,
    "pMetadata"      jsonb
)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $fn$
    SELECT jsonb_build_object(
        'clinicID',      "pClinicID",
        'sequenceNo',    "pSequenceNo",
        'occurredAt',    to_char("pOccurredAt" AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
        'userID',        "pUserID",
        'rolePK',        "pRolePK",
        'auditActionPK', "pAuditActionPK",
        'entityType',    "pEntityType",
        'entityID',      "pEntityID",
        'patientID',     "pPatientID",
        'requestID',     "pRequestID",
        'metadata',      "pMetadata"
    )::text
$fn$;

CREATE OR REPLACE FUNCTION "auditRowHash"(
    "pCanonicalPayload" text,
    "pPreviousHash"     bytea
)
RETURNS bytea
LANGUAGE sql
IMMUTABLE
AS $fn$
    SELECT digest(convert_to("pCanonicalPayload", 'UTF8') || "pPreviousHash", 'sha256')
$fn$;

CREATE OR REPLACE FUNCTION "auditGenesisHash"("pClinicID" uuid)
RETURNS bytea
LANGUAGE sql
IMMUTABLE
AS $fn$
    SELECT digest(
        convert_to('medicitasAuditGenesis:' || "pClinicID"::text, 'UTF8'),
        'sha256'
    )
$fn$;

CREATE OR REPLACE FUNCTION "auditLogsAppendToChain"()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $fn$
DECLARE
    vLastSequenceNo bigint;
    vPreviousHash   bytea;
BEGIN
    SELECT h."lastSequenceNo", h."lastHash"
      INTO vLastSequenceNo, vPreviousHash
      FROM "auditChainHeads" h
     WHERE h."clinicID" = NEW."clinicID"
       FOR UPDATE;

    IF NOT FOUND THEN
        vLastSequenceNo := 0;
        vPreviousHash   := "auditGenesisHash"(NEW."clinicID");

        INSERT INTO "auditChainHeads" ("clinicID", "lastSequenceNo", "lastHash")
        VALUES (NEW."clinicID", 0, vPreviousHash)
        ON CONFLICT ("clinicID") DO NOTHING;

        SELECT h."lastSequenceNo", h."lastHash"
          INTO vLastSequenceNo, vPreviousHash
          FROM "auditChainHeads" h
         WHERE h."clinicID" = NEW."clinicID"
           FOR UPDATE;
    END IF;

    NEW."sequenceNo"   := vLastSequenceNo + 1;
    NEW."previousHash" := vPreviousHash;
    NEW."rowHash"      := "auditRowHash"(
        "auditCanonicalPayload"(
            NEW."clinicID",
            NEW."sequenceNo",
            NEW."occurredAt",
            NEW."userID",
            NEW."rolePK",
            NEW."auditActionPK",
            NEW."entityType",
            NEW."entityID",
            NEW."patientID",
            NEW."requestID",
            NEW."metadata"
        ),
        vPreviousHash
    );

    UPDATE "auditChainHeads"
       SET "lastSequenceNo" = NEW."sequenceNo",
           "lastHash"       = NEW."rowHash",
           "updatedAt"      = now()
     WHERE "clinicID" = NEW."clinicID";

    RETURN NEW;
END;
$fn$;

CREATE TRIGGER "auditLogsBi10AppendToChain"
    BEFORE INSERT ON "auditLogs"
    FOR EACH ROW EXECUTE FUNCTION "auditLogsAppendToChain"();

CREATE OR REPLACE FUNCTION "verifyAuditChain"("pClinicID" uuid)
RETURNS TABLE (
    "sequenceNo" bigint,
    "auditLogPK" bigint,
    "anomaly"    text,
    "detail"     text
)
LANGUAGE plpgsql
STABLE
AS $fn$
DECLARE
    vExpectedSequenceNo bigint := 1;
    vExpectedPrevHash   bytea  := "auditGenesisHash"("pClinicID");
    vRecomputedHash     bytea;
    vLastRowHash        bytea  := "auditGenesisHash"("pClinicID");
    vLastSequenceNo     bigint := 0;
    vHead               record;
    vRow                record;
BEGIN
    FOR vRow IN
        SELECT a.*
          FROM "auditLogs" a
         WHERE a."clinicID" = "pClinicID"
         ORDER BY a."sequenceNo"
    LOOP
        IF vRow."sequenceNo" <> vExpectedSequenceNo THEN
            RETURN QUERY SELECT
                vExpectedSequenceNo,
                vRow."auditLogPK",
                'missingSequence'::text,
                format('se esperaba sequenceNo %s y se encontro %s: faltan %s registro(s)',
                       vExpectedSequenceNo, vRow."sequenceNo",
                       vRow."sequenceNo" - vExpectedSequenceNo);
        END IF;

        IF vRow."previousHash" <> vExpectedPrevHash THEN
            RETURN QUERY SELECT
                vRow."sequenceNo",
                vRow."auditLogPK",
                'brokenLink'::text,
                'previousHash no coincide con el rowHash del registro anterior';
        END IF;

        vRecomputedHash := "auditRowHash"(
            "auditCanonicalPayload"(
                vRow."clinicID", vRow."sequenceNo", vRow."occurredAt",
                vRow."userID", vRow."rolePK", vRow."auditActionPK",
                vRow."entityType", vRow."entityID", vRow."patientID",
                vRow."requestID", vRow."metadata"
            ),
            vRow."previousHash"
        );

        IF vRecomputedHash <> vRow."rowHash" THEN
            RETURN QUERY SELECT
                vRow."sequenceNo",
                vRow."auditLogPK",
                'tamperedRow'::text,
                'el contenido del registro no reproduce su propio rowHash';
        END IF;

        vExpectedPrevHash   := vRow."rowHash";
        vExpectedSequenceNo := vRow."sequenceNo" + 1;
        vLastRowHash        := vRow."rowHash";
        vLastSequenceNo     := vRow."sequenceNo";
    END LOOP;

    SELECT h."lastSequenceNo", h."lastHash"
      INTO vHead
      FROM "auditChainHeads" h
     WHERE h."clinicID" = "pClinicID";

    IF FOUND AND (vHead."lastSequenceNo" <> vLastSequenceNo OR vHead."lastHash" <> vLastRowHash) THEN
        RETURN QUERY SELECT
            vLastSequenceNo,
            NULL::bigint,
            'headMismatch'::text,
            format('la cabeza de cadena apunta a sequenceNo %s pero el ultimo registro es %s',
                   vHead."lastSequenceNo", vLastSequenceNo);
    END IF;

    RETURN;
END;
$fn$;

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

ALTER TABLE "clinics" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "clinicsPlatformAll" ON "clinics"
    FOR ALL
    USING ("isPlatformAdmin"())
    WITH CHECK ("isPlatformAdmin"());

CREATE POLICY "clinicsTenantSelect" ON "clinics"
    FOR SELECT
    USING ("clinicID" = "currentClinicID"());

ALTER TABLE "users" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "usersPlatformAll" ON "users"
    FOR ALL
    USING ("isPlatformAdmin"())
    WITH CHECK ("isPlatformAdmin"());

CREATE POLICY "usersTenantAll" ON "users"
    FOR ALL
    USING ("clinicID" = "currentClinicID"())
    WITH CHECK ("clinicID" = "currentClinicID"());

ALTER TABLE "professionals"        ENABLE ROW LEVEL SECURITY;
ALTER TABLE "services"             ENABLE ROW LEVEL SECURITY;
ALTER TABLE "professionalServices" ENABLE ROW LEVEL SECURITY;
ALTER TABLE "workingHours"         ENABLE ROW LEVEL SECURITY;
ALTER TABLE "scheduleBlocks"       ENABLE ROW LEVEL SECURITY;
ALTER TABLE "patients"             ENABLE ROW LEVEL SECURITY;
ALTER TABLE "appointments"         ENABLE ROW LEVEL SECURITY;
ALTER TABLE "auditChainHeads"      ENABLE ROW LEVEL SECURITY;

CREATE POLICY "professionalsTenantIsolation" ON "professionals"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "servicesTenantIsolation" ON "services"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "professionalServicesTenantIsolation" ON "professionalServices"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "patientsTenantIsolation" ON "patients"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "appointmentsTenantIsolation" ON "appointments"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "auditChainHeadsTenantIsolation" ON "auditChainHeads"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());

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

ALTER TABLE "clinicalNotes" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "clinicalNotesOwnByProfessional" ON "clinicalNotes"
    FOR ALL
    TO "medicitasProfessional"
    USING ("clinicID" = "currentClinicID"()
       AND "professionalID" = "currentProfessionalID"())
    WITH CHECK ("clinicID" = "currentClinicID"()
            AND "professionalID" = "currentProfessionalID"());

ALTER TABLE "auditLogs" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "auditLogsTenantInsert" ON "auditLogs"
    FOR INSERT
    WITH CHECK ("clinicID" = "currentClinicID"());

CREATE POLICY "auditLogsClinicAdminSelect" ON "auditLogs"
    FOR SELECT
    TO "medicitasClinicAdmin"
    USING ("clinicID" = "currentClinicID"());

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

GRANT SELECT ON "roles" TO "medicitasPlatform";

GRANT SELECT ON
    "roles", "specialties", "appointmentStatuses",
    "appointmentStatusTransitions", "auditActions"
TO "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";

GRANT SELECT, INSERT, UPDATE ON "clinics" TO "medicitasPlatform";
GRANT SELECT                 ON "clinics" TO
    "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";

GRANT SELECT, INSERT, UPDATE ON "users" TO "medicitasPlatform";
GRANT SELECT, INSERT, UPDATE ON "users" TO "medicitasClinicAdmin";

GRANT SELECT, INSERT, UPDATE         ON "professionals"        TO "medicitasClinicAdmin";
GRANT SELECT, INSERT, UPDATE         ON "services"             TO "medicitasClinicAdmin";
GRANT SELECT, INSERT,         DELETE ON "professionalServices" TO "medicitasClinicAdmin";

GRANT SELECT ON "professionals", "services", "professionalServices"
TO "medicitasReception", "medicitasProfessional";

GRANT SELECT, INSERT, UPDATE, DELETE ON "workingHours"   TO "medicitasClinicAdmin", "medicitasProfessional";
GRANT SELECT, INSERT,         DELETE ON "scheduleBlocks" TO "medicitasClinicAdmin", "medicitasProfessional";
GRANT SELECT                         ON "workingHours", "scheduleBlocks" TO "medicitasReception";

GRANT SELECT, INSERT, UPDATE ON "patients" TO "medicitasClinicAdmin", "medicitasReception";
GRANT SELECT                 ON "patients" TO "medicitasProfessional";

GRANT SELECT, INSERT, UPDATE ON "appointments" TO "medicitasClinicAdmin", "medicitasReception";

GRANT SELECT ON "appointments" TO "medicitasProfessional";
GRANT UPDATE ("appointmentStatusPK", "outcomeRecordedAt", "outcomeRecordedByUserID")
    ON "appointments" TO "medicitasProfessional";

GRANT SELECT, INSERT, UPDATE ON "clinicalNotes" TO "medicitasProfessional";

GRANT INSERT ON "auditLogs" TO
    "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT SELECT ON "auditLogs" TO "medicitasClinicAdmin";

REVOKE UPDATE, DELETE, TRUNCATE ON "auditLogs" FROM
    "medicitasPlatform", "medicitasClinicAdmin",
    "medicitasReception", "medicitasProfessional";

GRANT SELECT ON "auditChainHeads" TO "medicitasClinicAdmin";

GRANT EXECUTE ON FUNCTION "currentClinicID"()       TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT EXECUTE ON FUNCTION "currentRoleCode"()       TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT EXECUTE ON FUNCTION "currentUserID"()         TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT EXECUTE ON FUNCTION "currentProfessionalID"() TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";
GRANT EXECUTE ON FUNCTION "isPlatformAdmin"()       TO "medicitasPlatform", "medicitasClinicAdmin", "medicitasReception", "medicitasProfessional";

GRANT EXECUTE ON FUNCTION "resolveIdentity"(text) TO
    "medicitasPlatform", "medicitasClinicAdmin",
    "medicitasReception", "medicitasProfessional";

GRANT EXECUTE ON FUNCTION "verifyAuditChain"(uuid)      TO "medicitasClinicAdmin";
GRANT EXECUTE ON FUNCTION "auditGenesisHash"(uuid)      TO "medicitasClinicAdmin";
GRANT EXECUTE ON FUNCTION "auditRowHash"(text, bytea)   TO "medicitasClinicAdmin";
GRANT EXECUTE ON FUNCTION "auditCanonicalPayload"(uuid, bigint, timestamptz, uuid, text, text, text, uuid, uuid, uuid, jsonb)
                                                        TO "medicitasClinicAdmin";

ALTER ROLE "medicitasOwner"        WITH LOGIN PASSWORD 'ownerPassword';

ALTER ROLE "medicitasPlatform"     WITH LOGIN PASSWORD 'platformPassword';
ALTER ROLE "medicitasClinicAdmin"  WITH LOGIN PASSWORD 'clinicAdminPassword';
ALTER ROLE "medicitasReception"    WITH LOGIN PASSWORD 'receptionPassword';
ALTER ROLE "medicitasProfessional" WITH LOGIN PASSWORD 'professionalPassword';

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

