-- =============================================================================
-- MediCitas · 03 · Nucleo del negocio
--                  clinicas, usuarios, profesionales, servicios, pacientes
-- =============================================================================
-- PATRON DE INTEGRIDAD MULTI-TENANT
-- ---------------------------------
-- Toda tabla de tenant declara  UNIQUE ("clinicID", <su PK>)  y toda referencia
-- entre tablas de tenant es una CLAVE AJENA COMPUESTA que incluye "clinicID":
--
--     FOREIGN KEY ("clinicID", "professionalID")
--         REFERENCES "professionals" ("clinicID", "professionalID")
--
-- Con eso una fila de la clinica A no puede apuntar a una de la clinica B ni
-- por error de la aplicacion ni por escritura directa con psql: el motor lo
-- rechaza. Es la primera de las TRES capas que sostienen I5 (las otras dos son
-- RLS en 10_rls.sql y el filtro explicito del repositorio). El nucleo
-- obligatorio §2 pide demostrar I5 con intentos deliberados de fuga, y esta es
-- la capa que hace que la fuga no sea representable en el modelo, no solo
-- improbable.
--
-- Esas superclaves UNIQUE ("clinicID", <PK>, ...) existen UNICAMENTE para ser
-- destino de estas claves ajenas. No son redundancia: borrarlas destruye las
-- tres reglas declarativas del esquema.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- clinics · el tenant (RF1)
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- users · la identidad dentro del dominio (RF2, RF17)
-- -----------------------------------------------------------------------------
-- Las credenciales no viven en este modelo la entidad usuario guarda unicamente 
-- el identificador que ese proveedor emite, la clinica a la que pertenece y su rol dentro de ella". 
-- Por eso aqui NO hay correo, ni nombre, ni hash de contrasena: viven en Keycloak (RF17).
--
-- El costo asumido es que la bitacora de RF19 muestra uuid y la API resuelve el
-- nombre contra el proveedor cuando hace falta. Se acepta porque minimiza el
-- dato personal almacenado y porque deja una sola autoridad sobre la identidad.
-- -----------------------------------------------------------------------------
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

    -- RF2
    CONSTRAINT "usersTenancyByRole" CHECK (
        ("rolePK" =  'platformAdmin' AND "clinicID" IS NULL)
     OR ("rolePK" <> 'platformAdmin' AND "clinicID" IS NOT NULL)
    ),

    -- RF2 pide baja logica.
    CONSTRAINT "usersDeactivationConsistent" CHECK (
        ("isActive" AND "deactivatedAt" IS NULL)
     OR (NOT "isActive" AND "deactivatedAt" IS NOT NULL)
    )
);

-- -----------------------------------------------------------------------------
-- professionals · RF4
-- -----------------------------------------------------------------------------
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
    
    -- El usuario del profesional tiene que ser de SU MISMA clinica (I5).
    CONSTRAINT "professionalsUserSameClinic"  FOREIGN KEY ("clinicID", "userID")
        REFERENCES "users" ("clinicID", "userID"), 
    CONSTRAINT "professionalsLicenseUnique"   UNIQUE ("clinicID", "licenseCode"),
    CONSTRAINT "professionalsNameNotBlank"    CHECK (length(btrim("fullName")) > 0)
);

-- -----------------------------------------------------------------------------
-- services · RF3
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- professionalServices · RF4, los servicios que esta habilitado a atender
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- patients · RF14
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- INDICE · busqueda de pacientes de la pantalla de recepcion
-- -----------------------------------------------------------------------------
CREATE INDEX "patientsClinicLastNameIdx"
    ON "patients" ("clinicID", lower("lastName"), lower("firstName"))
    WHERE "isActive";
