-- =============================================================================
-- MediCitas · 04 · Agenda: horario de atencion y bloqueos (RF5, RF6)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- workingHours · horario de atencion semanal (RF5)
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- scheduleBlocks · bloqueos por vacaciones o permisos (RF6)
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- INDICE · intervalo del bloqueo
-- -----------------------------------------------------------------------------
CREATE INDEX "scheduleBlocksPeriodIdx"
    ON "scheduleBlocks" USING gist (
        "professionalID",
        tstzrange("startAt", "endAt", '[)')
    );
