-- =============================================================================
-- MediCitas · Semilla de datos
-- =============================================================================

-- =============================================================================
-- 1 · clinics · RF1
-- =============================================================================
-- Tres clinicas en tres provincias distintas.
INSERT INTO "clinics" ("clinicID", "code", "name", "timeZone") VALUES
    ('11111111-0001-0000-0000-000000000001', 'santa-lucia', 'Clínica Santa Lucía',      'America/Costa_Rica'),
    ('22222222-0001-0000-0000-000000000001', 'monteverde',  'Clínica Monteverde',       'America/Costa_Rica'),
    ('33333333-0001-0000-0000-000000000001', 'guanacaste',  'Centro Médico Guanacaste', 'America/Costa_Rica');

-- =============================================================================
-- 2 · users · RF2, RF17
-- =============================================================================
INSERT INTO "users" ("userID", "clinicID", "identityProviderSubject", "rolePK") VALUES
    -- Plataforma: sin clinica, no accede a datos clinicos de ninguna
    ('00000000-0010-0000-0000-000000000001', NULL,                                   '00000000-0010-0000-0000-000000000001', 'platformAdmin'),

    -- Clínica Santa Lucía
    ('11111111-0010-0000-0000-000000000001', '11111111-0001-0000-0000-000000000001', '11111111-0010-0000-0000-000000000001', 'clinicAdmin'),
    ('11111111-0010-0000-0000-000000000002', '11111111-0001-0000-0000-000000000001', '11111111-0010-0000-0000-000000000002', 'reception'),
    ('11111111-0010-0000-0000-000000000003', '11111111-0001-0000-0000-000000000001', '11111111-0010-0000-0000-000000000003', 'professional'),
    ('11111111-0010-0000-0000-000000000004', '11111111-0001-0000-0000-000000000001', '11111111-0010-0000-0000-000000000004', 'professional'),

    -- Clínica Monteverde
    ('22222222-0010-0000-0000-000000000001', '22222222-0001-0000-0000-000000000001', '22222222-0010-0000-0000-000000000001', 'clinicAdmin'),
    ('22222222-0010-0000-0000-000000000002', '22222222-0001-0000-0000-000000000001', '22222222-0010-0000-0000-000000000002', 'reception'),
    ('22222222-0010-0000-0000-000000000003', '22222222-0001-0000-0000-000000000001', '22222222-0010-0000-0000-000000000003', 'professional'),
    ('22222222-0010-0000-0000-000000000004', '22222222-0001-0000-0000-000000000001', '22222222-0010-0000-0000-000000000004', 'professional'),

    -- Centro Médico Guanacaste
    ('33333333-0010-0000-0000-000000000001', '33333333-0001-0000-0000-000000000001', '33333333-0010-0000-0000-000000000001', 'clinicAdmin'),
    ('33333333-0010-0000-0000-000000000002', '33333333-0001-0000-0000-000000000001', '33333333-0010-0000-0000-000000000002', 'reception'),
    ('33333333-0010-0000-0000-000000000003', '33333333-0001-0000-0000-000000000001', '33333333-0010-0000-0000-000000000003', 'professional'),
    ('33333333-0010-0000-0000-000000000004', '33333333-0001-0000-0000-000000000001', '33333333-0010-0000-0000-000000000004', 'professional');

-- =============================================================================
-- 3 · professionals · RF4
-- =============================================================================
INSERT INTO "professionals" ("professionalID", "clinicID", "userID", "specialtyID", "fullName", "licenseCode") VALUES
    -- Clínica Santa Lucía
    ('11111111-0020-0000-0000-000000000001', '11111111-0001-0000-0000-000000000001', '11111111-0010-0000-0000-000000000003',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine'), 'María José Vargas Ureña',   'CM-10234'),
    ('11111111-0020-0000-0000-000000000002', '11111111-0001-0000-0000-000000000001', '11111111-0010-0000-0000-000000000004',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'pediatrics'),      'Andrés Solano Picado',      'CM-11587'),

    -- Clínica Monteverde
    ('22222222-0020-0000-0000-000000000001', '22222222-0001-0000-0000-000000000001', '22222222-0010-0000-0000-000000000003',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine'), 'Carlos Jiménez Chaves',     'CM-09812'),
    ('22222222-0020-0000-0000-000000000002', '22222222-0001-0000-0000-000000000001', '22222222-0010-0000-0000-000000000004',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'dermatology'),     'Daniela Rojas Montero',     'CM-12476'),

    -- Centro Médico Guanacaste
    ('33333333-0020-0000-0000-000000000001', '33333333-0001-0000-0000-000000000001', '33333333-0010-0000-0000-000000000003',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine'), 'Silvia Hernández Leiva',    'CM-08945'),
    ('33333333-0020-0000-0000-000000000002', '33333333-0001-0000-0000-000000000001', '33333333-0010-0000-0000-000000000004',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'nutrition'),       'José Pablo Murillo Castro', 'CM-13302');

-- =============================================================================
-- 4 · services · RF3
-- =============================================================================
INSERT INTO "services" ("serviceID", "clinicID", "name", "description", "durationMinutes", "specialtyID") VALUES
    -- Clínica Santa Lucía
    ('11111111-0030-0000-0000-000000000001', '11111111-0001-0000-0000-000000000001', 'Consulta de medicina general',
     'Valoración médica general para personas adultas.', 30,
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine')),
    ('11111111-0030-0000-0000-000000000002', '11111111-0001-0000-0000-000000000001', 'Consulta pediátrica',
     'Control de crecimiento y desarrollo para menores de edad.', 45,
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'pediatrics')),

    -- Clínica Monteverde
    ('22222222-0030-0000-0000-000000000001', '22222222-0001-0000-0000-000000000001', 'Consulta de medicina general',
     'Valoración médica general para personas adultas.', 30,
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine')),
    ('22222222-0030-0000-0000-000000000002', '22222222-0001-0000-0000-000000000001', 'Valoración dermatológica',
     'Revisión de lesiones en piel y control de lunares.', 20,
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'dermatology')),

    -- Centro Médico Guanacaste
    ('33333333-0030-0000-0000-000000000001', '33333333-0001-0000-0000-000000000001', 'Consulta de medicina general',
     'Valoración médica general para personas adultas.', 30,
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine')),
    ('33333333-0030-0000-0000-000000000002', '33333333-0001-0000-0000-000000000001', 'Consulta nutricional',
     'Plan de alimentación y seguimiento de medidas antropométricas.', 60,
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'nutrition'));

-- =============================================================================
-- 5 · professionalServices · RF4
-- =============================================================================
INSERT INTO "professionalServices" ("clinicID", "professionalID", "serviceID", "specialtyID") VALUES
    ('11111111-0001-0000-0000-000000000001', '11111111-0020-0000-0000-000000000001', '11111111-0030-0000-0000-000000000001',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine')),
    ('11111111-0001-0000-0000-000000000001', '11111111-0020-0000-0000-000000000002', '11111111-0030-0000-0000-000000000002',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'pediatrics')),

    ('22222222-0001-0000-0000-000000000001', '22222222-0020-0000-0000-000000000001', '22222222-0030-0000-0000-000000000001',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine')),
    ('22222222-0001-0000-0000-000000000001', '22222222-0020-0000-0000-000000000002', '22222222-0030-0000-0000-000000000002',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'dermatology')),

    ('33333333-0001-0000-0000-000000000001', '33333333-0020-0000-0000-000000000001', '33333333-0030-0000-0000-000000000001',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'generalMedicine')),
    ('33333333-0001-0000-0000-000000000001', '33333333-0020-0000-0000-000000000002', '33333333-0030-0000-0000-000000000002',
     (SELECT "specialtyID" FROM "specialties" WHERE "code" = 'nutrition'));

-- =============================================================================
-- 6 · workingHours · RF5
-- =============================================================================
INSERT INTO "workingHours" ("clinicID", "professionalID", "weekday", "startTimeLocal", "endTimeLocal")
SELECT v."clinicID", v."professionalID", "weekday", v."startTimeLocal", v."endTimeLocal"
  FROM (VALUES
      ('11111111-0001-0000-0000-000000000001'::uuid, '11111111-0020-0000-0000-000000000001'::uuid, time '08:00', time '16:00'),
      ('11111111-0001-0000-0000-000000000001'::uuid, '11111111-0020-0000-0000-000000000002'::uuid, time '08:00', time '16:00'),
      ('22222222-0001-0000-0000-000000000001'::uuid, '22222222-0020-0000-0000-000000000001'::uuid, time '08:00', time '16:00'),
      ('22222222-0001-0000-0000-000000000001'::uuid, '22222222-0020-0000-0000-000000000002'::uuid, time '08:00', time '16:00'),
      ('33333333-0001-0000-0000-000000000001'::uuid, '33333333-0020-0000-0000-000000000001'::uuid, time '08:00', time '16:00'),
      ('33333333-0001-0000-0000-000000000001'::uuid, '33333333-0020-0000-0000-000000000002'::uuid, time '08:00', time '16:00')
  ) AS v("clinicID", "professionalID", "startTimeLocal", "endTimeLocal")
 CROSS JOIN generate_series(1, 5) AS "weekday";

-- =============================================================================
-- 7 · scheduleBlocks · RF6
-- =============================================================================rranque.
WITH "anchor" AS (
    SELECT date_trunc('week', CURRENT_DATE)::date AS "thisMonday"
)
INSERT INTO "scheduleBlocks" ("clinicID", "professionalID", "startAt", "endAt", "reason", "userID")
SELECT v."clinicID",
       v."professionalID",
       (a."thisMonday" + 9  + time '00:00') AT TIME ZONE 'America/Costa_Rica',
       (a."thisMonday" + 10 + time '00:00') AT TIME ZONE 'America/Costa_Rica',
       v."reason",
       v."userID"
  FROM (VALUES
      ('11111111-0001-0000-0000-000000000001'::uuid, '11111111-0020-0000-0000-000000000002'::uuid,
       'Vacaciones',                          '11111111-0010-0000-0000-000000000001'::uuid),
      ('22222222-0001-0000-0000-000000000001'::uuid, '22222222-0020-0000-0000-000000000002'::uuid,
       'Capacitación del Colegio de Médicos', '22222222-0010-0000-0000-000000000001'::uuid),
      ('33333333-0001-0000-0000-000000000001'::uuid, '33333333-0020-0000-0000-000000000002'::uuid,
       'Permiso personal',                    '33333333-0010-0000-0000-000000000001'::uuid)
  ) AS v("clinicID", "professionalID", "reason", "userID")
 CROSS JOIN "anchor" a;

-- =============================================================================
-- 8 · patients · RF14
-- =============================================================================

INSERT INTO "patients" ("patientID", "clinicID", "nationalID", "firstName", "lastName", "birthDate", "phone", "email") VALUES
    -- Clínica Santa Lucía
    ('11111111-0040-0000-0000-000000000001', '11111111-0001-0000-0000-000000000001', '1-0845-0623',
     'Lucía',     'Brenes Mora',        DATE '1990-03-14', '8712-0945', 'lucia.brenes@gmail.com'),
    ('11111111-0040-0000-0000-000000000002', '11111111-0001-0000-0000-000000000001', '1-1032-0458',
     'Esteban',   'Quesada Alfaro',     DATE '1985-11-02', '8864-2210', 'esteban.quesada@gmail.com'),
    ('11111111-0040-0000-0000-000000000003', '11111111-0001-0000-0000-000000000001', '1-1988-0377',
     'Sofía',     'Camacho Zúñiga',     DATE '2018-06-21', '2253-4178', NULL),

    -- Clínica Monteverde
    ('22222222-0040-0000-0000-000000000001', '22222222-0001-0000-0000-000000000001', '6-0412-0789',
     'Mauricio',  'Araya Hidalgo',      DATE '1978-07-30', '8355-6102', 'mauricio.araya@gmail.com'),
    ('22222222-0040-0000-0000-000000000002', '22222222-0001-0000-0000-000000000001', '1-0845-0623',
     'Gabriela',  'Fonseca Soto',       DATE '1996-01-09', '7048-3391', 'gabriela.fonseca@gmail.com'),
    ('22222222-0040-0000-0000-000000000003', '22222222-0001-0000-0000-000000000001', '6-0501-0244',
     'Randall',   'Chacón Vega',        DATE '2012-09-17', '2645-7730', NULL),

    -- Centro Médico Guanacaste
    ('33333333-0040-0000-0000-000000000001', '33333333-0001-0000-0000-000000000001', '5-0298-0611',
     'Marianela', 'Obando Sánchez',     DATE '1982-12-05', '8601-4472', 'marianela.obando@gmail.com'),
    ('33333333-0040-0000-0000-000000000002', '33333333-0001-0000-0000-000000000001', '5-0376-0190',
     'Kevin',     'Villalobos Bonilla', DATE '1999-04-23', '7219-8865', 'kevin.villalobos@gmail.com'),
    ('33333333-0040-0000-0000-000000000003', '33333333-0001-0000-0000-000000000001', '5-0455-0038',
     'Ana Lucía', 'Pérez Delgado',      DATE '2015-02-11', '2666-1903', NULL);

-- =============================================================================
-- 9 · appointments · RF9 a RF13
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 9.1 · Citas atendidas · RF12
-- -----------------------------------------------------------------------------

WITH "anchor" AS (
    SELECT date_trunc('week', CURRENT_DATE)::date AS "thisMonday"
)
INSERT INTO "appointments" (
    "appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
    "startAt", "appointmentStatusPK", "createdByUserID",
    "outcomeRecordedAt", "outcomeRecordedByUserID")
SELECT v."appointmentID", v."clinicID", v."patientID", v."professionalID", v."serviceID",
       (a."thisMonday" - 6 + time '09:00') AT TIME ZONE 'America/Costa_Rica',
       'attended',
       v."createdByUserID",
       (a."thisMonday" - 6 + time '10:00') AT TIME ZONE 'America/Costa_Rica',
       v."outcomeRecordedByUserID"
  FROM (VALUES
      ('11111111-0050-0000-0000-000000000001'::uuid, '11111111-0001-0000-0000-000000000001'::uuid,
       '11111111-0040-0000-0000-000000000001'::uuid, '11111111-0020-0000-0000-000000000001'::uuid,
       '11111111-0030-0000-0000-000000000001'::uuid,
       '11111111-0010-0000-0000-000000000002'::uuid, '11111111-0010-0000-0000-000000000003'::uuid),
      ('22222222-0050-0000-0000-000000000001'::uuid, '22222222-0001-0000-0000-000000000001'::uuid,
       '22222222-0040-0000-0000-000000000001'::uuid, '22222222-0020-0000-0000-000000000001'::uuid,
       '22222222-0030-0000-0000-000000000001'::uuid,
       '22222222-0010-0000-0000-000000000002'::uuid, '22222222-0010-0000-0000-000000000003'::uuid),
      ('33333333-0050-0000-0000-000000000001'::uuid, '33333333-0001-0000-0000-000000000001'::uuid,
       '33333333-0040-0000-0000-000000000001'::uuid, '33333333-0020-0000-0000-000000000001'::uuid,
       '33333333-0030-0000-0000-000000000001'::uuid,
       '33333333-0010-0000-0000-000000000002'::uuid, '33333333-0010-0000-0000-000000000003'::uuid)
  ) AS v("appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
         "createdByUserID", "outcomeRecordedByUserID")
 CROSS JOIN "anchor" a;

-- -----------------------------------------------------------------------------
-- 9.2 · Citas con ausencia · RF12
-- -----------------------------------------------------------------------------
WITH "anchor" AS (
    SELECT date_trunc('week', CURRENT_DATE)::date AS "thisMonday"
)
INSERT INTO "appointments" (
    "appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
    "startAt", "appointmentStatusPK", "createdByUserID",
    "outcomeRecordedAt", "outcomeRecordedByUserID")
SELECT v."appointmentID", v."clinicID", v."patientID", v."professionalID", v."serviceID",
       (a."thisMonday" - 5 + time '10:00') AT TIME ZONE 'America/Costa_Rica',
       'absent',
       v."createdByUserID",
       (a."thisMonday" - 5 + time '11:00') AT TIME ZONE 'America/Costa_Rica',
       v."outcomeRecordedByUserID"
  FROM (VALUES
      ('11111111-0050-0000-0000-000000000002'::uuid, '11111111-0001-0000-0000-000000000001'::uuid,
       '11111111-0040-0000-0000-000000000002'::uuid, '11111111-0020-0000-0000-000000000001'::uuid,
       '11111111-0030-0000-0000-000000000001'::uuid,
       '11111111-0010-0000-0000-000000000002'::uuid, '11111111-0010-0000-0000-000000000003'::uuid),
      ('22222222-0050-0000-0000-000000000002'::uuid, '22222222-0001-0000-0000-000000000001'::uuid,
       '22222222-0040-0000-0000-000000000002'::uuid, '22222222-0020-0000-0000-000000000001'::uuid,
       '22222222-0030-0000-0000-000000000001'::uuid,
       '22222222-0010-0000-0000-000000000002'::uuid, '22222222-0010-0000-0000-000000000003'::uuid),
      ('33333333-0050-0000-0000-000000000002'::uuid, '33333333-0001-0000-0000-000000000001'::uuid,
       '33333333-0040-0000-0000-000000000002'::uuid, '33333333-0020-0000-0000-000000000001'::uuid,
       '33333333-0030-0000-0000-000000000001'::uuid,
       '33333333-0010-0000-0000-000000000002'::uuid, '33333333-0010-0000-0000-000000000003'::uuid)
  ) AS v("appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
         "createdByUserID", "outcomeRecordedByUserID")
 CROSS JOIN "anchor" a;

-- -----------------------------------------------------------------------------
-- 9.3 · Citas canceladas · RF11
-- -----------------------------------------------------------------------------
WITH "anchor" AS (
    SELECT date_trunc('week', CURRENT_DATE)::date AS "thisMonday"
)
INSERT INTO "appointments" (
    "appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
    "startAt", "appointmentStatusPK", "createdByUserID",
    "cancelledAt", "cancelledByUserID", "cancellationReason")
SELECT v."appointmentID", v."clinicID", v."patientID", v."professionalID", v."serviceID",
       (a."thisMonday" - 4 + time '11:00')  AT TIME ZONE 'America/Costa_Rica',
       'cancelled',
       v."createdByUserID",
       (a."thisMonday" - 5 + time '15:30')  AT TIME ZONE 'America/Costa_Rica',
       v."cancelledByUserID",
       v."cancellationReason"
  FROM (VALUES
      ('11111111-0050-0000-0000-000000000003'::uuid, '11111111-0001-0000-0000-000000000001'::uuid,
       '11111111-0040-0000-0000-000000000003'::uuid, '11111111-0020-0000-0000-000000000002'::uuid,
       '11111111-0030-0000-0000-000000000002'::uuid, '11111111-0010-0000-0000-000000000002'::uuid,
       '11111111-0010-0000-0000-000000000002'::uuid,
       'La persona encargada solicitó cancelar por un viaje imprevisto.'),
      ('22222222-0050-0000-0000-000000000003'::uuid, '22222222-0001-0000-0000-000000000001'::uuid,
       '22222222-0040-0000-0000-000000000003'::uuid, '22222222-0020-0000-0000-000000000002'::uuid,
       '22222222-0030-0000-0000-000000000002'::uuid, '22222222-0010-0000-0000-000000000002'::uuid,
       '22222222-0010-0000-0000-000000000002'::uuid,
       'El paciente canceló por incapacidad laboral.'),
      ('33333333-0050-0000-0000-000000000003'::uuid, '33333333-0001-0000-0000-000000000001'::uuid,
       '33333333-0040-0000-0000-000000000003'::uuid, '33333333-0020-0000-0000-000000000002'::uuid,
       '33333333-0030-0000-0000-000000000002'::uuid, '33333333-0010-0000-0000-000000000002'::uuid,
       '33333333-0010-0000-0000-000000000002'::uuid,
       'Cancelada a solicitud de la familia por traslado fuera de la provincia.')
  ) AS v("appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
         "createdByUserID", "cancelledByUserID", "cancellationReason")
 CROSS JOIN "anchor" a;

-- -----------------------------------------------------------------------------
-- 9.4 · Citas futuras reservadas · RF9
-- -----------------------------------------------------------------------------
WITH "anchor" AS (
    SELECT date_trunc('week', CURRENT_DATE)::date AS "thisMonday"
)
INSERT INTO "appointments" (
    "appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
    "startAt", "appointmentStatusPK", "createdByUserID")
SELECT v."appointmentID", v."clinicID", v."patientID", v."professionalID", v."serviceID",
       (a."thisMonday" + 8 + time '09:00') AT TIME ZONE 'America/Costa_Rica',
       'reserved',
       v."createdByUserID"
  FROM (VALUES
      ('11111111-0050-0000-0000-000000000004'::uuid, '11111111-0001-0000-0000-000000000001'::uuid,
       '11111111-0040-0000-0000-000000000001'::uuid, '11111111-0020-0000-0000-000000000001'::uuid,
       '11111111-0030-0000-0000-000000000001'::uuid, '11111111-0010-0000-0000-000000000002'::uuid),
      ('22222222-0050-0000-0000-000000000004'::uuid, '22222222-0001-0000-0000-000000000001'::uuid,
       '22222222-0040-0000-0000-000000000001'::uuid, '22222222-0020-0000-0000-000000000001'::uuid,
       '22222222-0030-0000-0000-000000000001'::uuid, '22222222-0010-0000-0000-000000000002'::uuid),
      ('33333333-0050-0000-0000-000000000004'::uuid, '33333333-0001-0000-0000-000000000001'::uuid,
       '33333333-0040-0000-0000-000000000001'::uuid, '33333333-0020-0000-0000-000000000001'::uuid,
       '33333333-0030-0000-0000-000000000001'::uuid, '33333333-0010-0000-0000-000000000002'::uuid)
  ) AS v("appointmentID", "clinicID", "patientID", "professionalID", "serviceID", "createdByUserID")
 CROSS JOIN "anchor" a;

-- -----------------------------------------------------------------------------
-- 9.5 · Citas reprogramadas · RF10
-- -----------------------------------------------------------------------------
WITH "anchor" AS (
    SELECT date_trunc('week', CURRENT_DATE)::date AS "thisMonday"
)
INSERT INTO "appointments" (
    "appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
    "startAt", "appointmentStatusPK", "createdByUserID",
    "rescheduledToAppointmentID")
SELECT v."appointmentID", v."clinicID", v."patientID", v."professionalID", v."serviceID",
       (a."thisMonday" - 3 + time '09:00') AT TIME ZONE 'America/Costa_Rica',
       'rescheduled',
       v."createdByUserID",
       v."rescheduledToAppointmentID"
  FROM (VALUES
      ('11111111-0050-0000-0000-000000000005'::uuid, '11111111-0001-0000-0000-000000000001'::uuid,
       '11111111-0040-0000-0000-000000000001'::uuid, '11111111-0020-0000-0000-000000000001'::uuid,
       '11111111-0030-0000-0000-000000000001'::uuid, '11111111-0010-0000-0000-000000000002'::uuid,
       '11111111-0050-0000-0000-000000000004'::uuid),
      ('22222222-0050-0000-0000-000000000005'::uuid, '22222222-0001-0000-0000-000000000001'::uuid,
       '22222222-0040-0000-0000-000000000001'::uuid, '22222222-0020-0000-0000-000000000001'::uuid,
       '22222222-0030-0000-0000-000000000001'::uuid, '22222222-0010-0000-0000-000000000002'::uuid,
       '22222222-0050-0000-0000-000000000004'::uuid),
      ('33333333-0050-0000-0000-000000000005'::uuid, '33333333-0001-0000-0000-000000000001'::uuid,
       '33333333-0040-0000-0000-000000000001'::uuid, '33333333-0020-0000-0000-000000000001'::uuid,
       '33333333-0030-0000-0000-000000000001'::uuid, '33333333-0010-0000-0000-000000000002'::uuid,
       '33333333-0050-0000-0000-000000000004'::uuid)
  ) AS v("appointmentID", "clinicID", "patientID", "professionalID", "serviceID",
         "createdByUserID", "rescheduledToAppointmentID")
 CROSS JOIN "anchor" a;

-- =============================================================================
-- 10 · clinicalNotes · RF15
-- =============================================================================
INSERT INTO "clinicalNotes" ("clinicalNoteID", "clinicID", "appointmentID", "professionalID", "content") VALUES
    ('11111111-0060-0000-0000-000000000001', '11111111-0001-0000-0000-000000000001',
     '11111111-0050-0000-0000-000000000001', '11111111-0020-0000-0000-000000000001',
     'Paciente refiere cefalea tensional de dos semanas de evolución. Signos vitales normales. Se indica analgésico y control en un mes.'),
    ('22222222-0060-0000-0000-000000000001', '22222222-0001-0000-0000-000000000001',
     '22222222-0050-0000-0000-000000000001', '22222222-0020-0000-0000-000000000001',
     'Control de presión arterial. Valores dentro del rango esperado. Se mantiene el tratamiento actual y se cita en tres meses.'),
    ('33333333-0060-0000-0000-000000000001', '33333333-0001-0000-0000-000000000001',
     '33333333-0050-0000-0000-000000000001', '33333333-0020-0000-0000-000000000001',
     'Consulta por dolor lumbar mecánico. Se descarta compromiso neurológico. Se indica reposo relativo y fisioterapia.');

-- =============================================================================
-- 11 · auditLogs · RF18, RF19 y el modulo de grupo de tres
-- =============================================================================
WITH "anchor" AS (
    SELECT date_trunc('week', CURRENT_DATE)::date AS "thisMonday"
)
INSERT INTO "auditLogs" (
    "clinicID", "occurredAt", "userID", "rolePK", "auditActionPK",
    "entityType", "entityID", "patientID", "metadata")
SELECT v."clinicID",
       (a."thisMonday" - 6 + v."localTime") AT TIME ZONE 'America/Costa_Rica',
       v."userID", v."rolePK", v."auditActionPK",
       v."entityType", v."entityID", v."patientID", v."metadata"
  FROM (VALUES
      -- Recepcion consulta los datos de contacto antes de confirmar la cita
      ('11111111-0001-0000-0000-000000000001'::uuid, time '08:45', '11111111-0010-0000-0000-000000000002'::uuid,
       'reception',    'readPatientContact', 'patients',
       '11111111-0040-0000-0000-000000000001'::uuid, '11111111-0040-0000-0000-000000000001'::uuid,
       '{"reason": "confirmacionDeCita"}'::jsonb),
      -- El profesional redacta la nota clinica de la cita que atendio
      ('11111111-0001-0000-0000-000000000001'::uuid, time '10:05', '11111111-0010-0000-0000-000000000003'::uuid,
       'professional', 'writeClinicalNote',  'clinicalNotes',
       '11111111-0060-0000-0000-000000000001'::uuid, '11111111-0040-0000-0000-000000000001'::uuid,
       '{"appointmentID": "11111111-0050-0000-0000-000000000001"}'::jsonb),

      ('22222222-0001-0000-0000-000000000001'::uuid, time '08:45', '22222222-0010-0000-0000-000000000002'::uuid,
       'reception',    'readPatientContact', 'patients',
       '22222222-0040-0000-0000-000000000001'::uuid, '22222222-0040-0000-0000-000000000001'::uuid,
       '{"reason": "confirmacionDeCita"}'::jsonb),
      ('22222222-0001-0000-0000-000000000001'::uuid, time '10:05', '22222222-0010-0000-0000-000000000003'::uuid,
       'professional', 'writeClinicalNote',  'clinicalNotes',
       '22222222-0060-0000-0000-000000000001'::uuid, '22222222-0040-0000-0000-000000000001'::uuid,
       '{"appointmentID": "22222222-0050-0000-0000-000000000001"}'::jsonb),

      ('33333333-0001-0000-0000-000000000001'::uuid, time '08:45', '33333333-0010-0000-0000-000000000002'::uuid,
       'reception',    'readPatientContact', 'patients',
       '33333333-0040-0000-0000-000000000001'::uuid, '33333333-0040-0000-0000-000000000001'::uuid,
       '{"reason": "confirmacionDeCita"}'::jsonb),
      ('33333333-0001-0000-0000-000000000001'::uuid, time '10:05', '33333333-0010-0000-0000-000000000003'::uuid,
       'professional', 'writeClinicalNote',  'clinicalNotes',
       '33333333-0060-0000-0000-000000000001'::uuid, '33333333-0040-0000-0000-000000000001'::uuid,
       '{"appointmentID": "33333333-0050-0000-0000-000000000001"}'::jsonb)
  ) AS v("clinicID", "localTime", "userID", "rolePK", "auditActionPK",
         "entityType", "entityID", "patientID", "metadata")
 CROSS JOIN "anchor" a;