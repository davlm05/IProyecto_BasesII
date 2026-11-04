-- =============================================================================
-- MediCitas · 00 · Extensiones y tipos propios
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- pgcrypto aporta digest() para el sha256 de la cadena de huellas de la
-- bitacora
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'timeRange') THEN
        CREATE TYPE "timeRange" AS RANGE (subtype = time);
    END IF;
END
$$;
