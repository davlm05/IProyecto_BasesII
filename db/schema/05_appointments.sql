-- =============================================================================
-- MediCitas · 05 · Citas y notas clinicas (RF9 a RF13, RF15, RF16, RF20, RF21)
-- =============================================================================

CREATE TABLE "appointments" (
    "appointmentID"       uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    "clinicID"            uuid        NOT NULL REFERENCES "clinics" ("clinicID"),

    -- RF9
    "patientID"           uuid        NOT NULL,
    "professionalID"      uuid        NOT NULL,
    "serviceID"           uuid        NOT NULL,
    "startAt"             timestamptz NOT NULL,
    -- I4: copia congelada de services."durationMinutes" en el momento de
    -- reservar. La asigna e inmutabiliza un trigger, no la aplicacion.
    "durationMinutes"     smallint    NOT NULL,
    "endAt"               timestamptz NOT NULL,
    -- RF13
    "appointmentStatusPK" text        NOT NULL DEFAULT 'reserved'
        REFERENCES "appointmentStatuses" ("appointmentStatusPK"),

    "createdByUserID" uuid        NOT NULL,
    "createdAt"       timestamptz NOT NULL DEFAULT now(),
    "updatedAt"       timestamptz NOT NULL DEFAULT now(),

    -- RF11
    "cancelledAt"        timestamptz,
    "cancelledByUserID"  uuid,
    "cancellationReason" text,

    -- RF12
    "outcomeRecordedAt"       timestamptz,
    "outcomeRecordedByUserID" uuid,

    -- RF10: reprogramar NO mueve la fila. 'rescheduled' es un estado final
    -- (RF13), de modo que la cita original queda cerrada apuntando a la nueva.
    "rescheduledToAppointmentID" uuid,

    CONSTRAINT "appointmentsClinicUnique"       UNIQUE ("clinicID", "appointmentID"),
    CONSTRAINT "appointmentsProfessionalUnique" UNIQUE ("clinicID", "appointmentID", "professionalID"),
    CONSTRAINT "appointmentsPatientUnique"      UNIQUE ("clinicID", "appointmentID", "patientID"),

    -- Las seis claves ajenas siguientes incluyen "clinicID": ninguna cita puede
    -- referenciar un paciente, un profesional, un servicio ni un usuario de
    -- otra clinica (I5).
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

    -- RF10
    CONSTRAINT "appointmentsRescheduledToFk"
        FOREIGN KEY ("clinicID", "rescheduledToAppointmentID", "patientID")
        REFERENCES "appointments" ("clinicID", "appointmentID", "patientID"),

    -- Una cita sustituye a lo sumo a una
    CONSTRAINT "appointmentsRescheduledToUnique" UNIQUE ("rescheduledToAppointmentID"),
    CONSTRAINT "appointmentsNotSelfReschedule"
        CHECK ("rescheduledToAppointmentID" IS NULL OR "rescheduledToAppointmentID" <> "appointmentID"),

    CONSTRAINT "appointmentsDurationRange" CHECK ("durationMinutes" BETWEEN 5 AND 480),
    -- Red de seguridad sobre la columna que el trigger calcula. Aunque "endAt"
    -- no deba escribirse desde la aplicacion, el motor exige que sea posterior
    -- al inicio: sin esto, un rango vacio no solaparia con nada y las dos
    -- EXCLUDE dejarian de proteger I1 e I2 sin que nada fallara.
    CONSTRAINT "appointmentsEndAfterStart" CHECK ("endAt" > "startAt"),

    -- Coherencia entre el estado y las columnas que ese estado obliga a llenar.
    -- Se escriben como IGUALDAD de predicados, no como implicacion, para cubrir
    -- los dos sentidos: ni un estado sin sus datos, ni datos sin su estado.
    --
    -- Ademas cierran el hueco que deja el privilegio por columna de la matriz:
    -- el profesional tiene UPDATE solo sobre "appointmentStatusPK" y las dos
    -- columnas del desenlace, de modo que no puede cancelar (RF11) porque no
    -- puede llenar las columnas que este CHECK le exigiria. El limite lo aplica
    -- el motor combinando privilegio de columna y CHECK, no la API.
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

    -- RF12
    CONSTRAINT "appointmentsOutcomeAfterStart" CHECK (
        "outcomeRecordedAt" IS NULL OR "outcomeRecordedAt" >= "startAt"
    ),
    -- RF11
    CONSTRAINT "appointmentsCancellationReasonNotBlank" CHECK (
        "cancellationReason" IS NULL OR length(btrim("cancellationReason")) > 0
    ),

    -- =========================================================================
    -- I1 · Un profesional nunca tiene dos citas vigentes solapadas
    -- =========================================================================
    CONSTRAINT "appointmentsProfessionalNoOverlap" EXCLUDE USING gist (
        "professionalID" WITH =,
        tstzrange("startAt", "endAt", '[)') WITH &&
    ) WHERE ("appointmentStatusPK" NOT IN ('cancelled', 'rescheduled')),

    -- =========================================================================
    -- I2 · Un paciente nunca tiene dos citas vigentes solapadas en su clinica
    -- =========================================================================
    CONSTRAINT "appointmentsPatientNoOverlap" EXCLUDE USING gist (
        "clinicID"  WITH =,
        "patientID" WITH =,
        tstzrange("startAt", "endAt", '[)') WITH &&
    ) WHERE ("appointmentStatusPK" NOT IN ('cancelled', 'rescheduled'))
);

-- =============================================================================
-- INDICES DE CONSULTA
-- =============================================================================

-- RF20
CREATE INDEX "appointmentsClinicProfessionalStartIdx"
    ON "appointments" ("clinicID", "professionalID", "startAt")
    WHERE "appointmentStatusPK" NOT IN ('cancelled', 'rescheduled');

-- RF20
CREATE INDEX "appointmentsClinicStartIdx"
    ON "appointments" ("clinicID", "startAt")
    WHERE "appointmentStatusPK" NOT IN ('cancelled', 'rescheduled');

-- RF16
CREATE INDEX "appointmentsClinicPatientStartIdx"
    ON "appointments" ("clinicID", "patientID", "startAt" DESC);

-- RF21
CREATE INDEX "appointmentsClinicStatusStartIdx"
    ON "appointments" ("clinicID", "appointmentStatusPK", "startAt");

-- =============================================================================
-- clinicalNotes · RF15
-- =============================================================================
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
