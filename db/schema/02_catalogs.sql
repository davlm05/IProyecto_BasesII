-- =============================================================================
-- MediCitas · 02 · Catalogos globales
-- =============================================================================

-- -----------------------------------------------------------------------------
-- roles · los cuatro actores de la matriz de permisos (RF17)
-- -----------------------------------------------------------------------------
-- "rolePK" es exactamente el nombre del rol de realm en Keycloak, de modo que
-- la traduccion token -> dominio que pide RF17 es directa y verificable.
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- specialties · catalogo de especialidades medicas
-- -----------------------------------------------------------------------------
-- RF3 (el servicio lleva la especialidad que requiere) y RF4 (el profesional se
-- registra con su especialidad) obligan a comparar dos especialidades entre si.
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- appointmentStatuses · los cinco estados de RF13
-- -----------------------------------------------------------------------------
--   "isFinal"      -> RF13: los cuatro estados finales no admiten salida.
--   "occupiesSlot" -> la cita sigue ocupando su espacio en la agenda.
-- -----------------------------------------------------------------------------
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

-- -----------------------------------------------------------------------------
-- appointmentStatusTransitions · la maquina de estados de RF13 como DATO
-- -----------------------------------------------------------------------------
-- RF13 pide "rechazar cualquier transicion que no este permitida". La maquina
-- se declara en filas, no en codigo: el trigger
-- "appointmentsValidateStatusTransition" (07_functionsTriggers.sql) la CONSULTA
-- en lugar de conocerla. Consecuencia buscada: cambiar el ciclo de vida de la
-- cita es un INSERT o un DELETE de datos, no una migracion de esquema ni un
-- despliegue de la aplicacion.
--
-- Al ser un trigger del motor, la transicion se rechaza aunque la escritura no
-- pase por la API, que es lo que la defensa pregunta de los invariantes.
-- -----------------------------------------------------------------------------
CREATE TABLE "appointmentStatusTransitions" (
    "fromAppointmentStatusPK" text NOT NULL REFERENCES "appointmentStatuses" ("appointmentStatusPK"),
    "toAppointmentStatusPK"   text NOT NULL REFERENCES "appointmentStatuses" ("appointmentStatusPK"),
    CONSTRAINT "appointmentStatusTransitionsPk"
        PRIMARY KEY ("fromAppointmentStatusPK", "toAppointmentStatusPK"),
    CONSTRAINT "appointmentStatusTransitionsNotReflexive"
        CHECK ("fromAppointmentStatusPK" <> "toAppointmentStatusPK")
);

-- RF13 literal: desde 'reserved' se pasa a los cuatro estados finales, y
-- ninguno de los cuatro tiene salida. "No admiten salida" se expresa por
-- AUSENCIA de filas, no con una bandera: lo que no esta declarado, no se puede.
INSERT INTO "appointmentStatusTransitions" ("fromAppointmentStatusPK", "toAppointmentStatusPK") VALUES
    ('reserved', 'attended'),
    ('reserved', 'absent'),
    ('reserved', 'cancelled'),
    ('reserved', 'rescheduled');

-- -----------------------------------------------------------------------------
-- auditActions · las acciones que RF18 obliga a registrar
-- -----------------------------------------------------------------------------
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
