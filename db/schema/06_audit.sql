-- =============================================================================
-- MediCitas · 06 · Bitacora de auditoria (RF18, RF19, I6)
-- =============================================================================
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

-- -----------------------------------------------------------------------------
-- INDICES · los tres filtros que RF19 exige
-- -----------------------------------------------------------------------------
-- RF19
CREATE INDEX "auditLogsClinicOccurredAtIdx" ON "auditLogs" ("clinicID", "occurredAt" DESC);

-- RF19
CREATE INDEX "auditLogsClinicUserIdx"       ON "auditLogs" ("clinicID", "userID", "occurredAt" DESC);

-- RF19
CREATE INDEX "auditLogsClinicPatientIdx"    ON "auditLogs" ("clinicID", "patientID", "occurredAt" DESC)
    WHERE "patientID" IS NOT NULL;

-- -----------------------------------------------------------------------------
-- auditChainHeads · cabeza de la cadena de huellas, una fila por clinica
-- -----------------------------------------------------------------------------
CREATE TABLE "auditChainHeads" (
    "clinicID"       uuid        PRIMARY KEY REFERENCES "clinics" ("clinicID"),
    "lastSequenceNo" bigint      NOT NULL DEFAULT 0,
    "lastHash"       bytea       NOT NULL,
    "updatedAt"      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT "auditChainHeadsSequenceNonNegative" CHECK ("lastSequenceNo" >= 0),
    CONSTRAINT "auditChainHeadsHashLength"          CHECK (length("lastHash") = 32)
);
