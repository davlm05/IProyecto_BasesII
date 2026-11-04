-- =============================================================================
-- MediCitas · 08 · Cadena de huellas de la bitacora
-- =============================================================================

-- -----------------------------------------------------------------------------
-- auditCanonicalPayload · representacion canonica de un registro
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- auditRowHash - sha256( payload canonico || huella anterior )
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- auditGenesisHash - primer eslabon de la cadena de una clinica
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- auditLogsAppendToChain - trigger BEFORE INSERT sobre "auditLogs"
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- verifyAuditChain - el verificador (RF19)
-- -----------------------------------------------------------------------------
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
