# Modelo de datos

El esquema vive en `db/schema/`, donde el prefijo numérico es el orden de aplicación.
Son 17 tablas repartidas en tres grupos que no se mezclan:

| Grupo | Tablas | Propiedad |
|---|---|---|
| Catálogos globales | `roles`, `specialties`, `appointmentStatuses`, `appointmentStatusTransitions`, `auditActions` | No llevan `clinicID`: son los mismos para todas las clínicas |
| Núcleo de negocio | `clinics`, `users`, `professionals`, `services`, `professionalServices`, `patients`, `workingHours`, `scheduleBlocks`, `appointments`, `clinicalNotes` | Toda fila pertenece a exactamente una clínica |
| Auditoría | `auditLogs`, `auditChainHeads` | De *tenant*, pero con reglas propias: solo admiten inserción |

## 1. Diagrama entidad-relación

```mermaid
erDiagram
    clinics ||--o{ users : "pertenece a (RF2)"
    clinics ||--o{ professionals : ""
    clinics ||--o{ services : ""
    clinics ||--o{ patients : ""
    clinics ||--o{ appointments : ""
    clinics ||--o{ auditLogs : ""
    clinics ||--|| auditChainHeads : "una cadena por clinica"

    roles ||--o{ users : "rol dentro de la clinica"
    roles ||--o{ auditLogs : "rol que actuo"

    users ||--o| professionals : "identidad del profesional"
    users ||--o{ appointments : "creo / cancelo / cerro"
    users ||--o{ scheduleBlocks : "registro el bloqueo"
    users ||--o{ auditLogs : "quien (RF18)"

    specialties ||--o{ professionals : "especialidad (RF4)"
    specialties ||--o{ services : "especialidad requerida (RF3)"

    professionals ||--o{ professionalServices : ""
    services ||--o{ professionalServices : "habilitacion (RF4)"

    professionals ||--o{ workingHours : "horario semanal (RF5)"
    professionals ||--o{ scheduleBlocks : "bloqueos (RF6)"
    professionals ||--o{ appointments : "atiende"

    patients ||--o{ appointments : "historial (RF16)"
    patients ||--o{ auditLogs : "sobre cual paciente (RF18)"

    services ||--o{ appointments : "determina la duracion (I4)"

    appointmentStatuses ||--o{ appointments : "estado (RF13)"
    appointmentStatuses ||--o{ appointmentStatusTransitions : "origen y destino"

    appointments ||--o| appointments : "rescheduledTo (RF10)"
    appointments ||--o| clinicalNotes : "a lo sumo una nota (RF15)"

    auditActions ||--o{ auditLogs : "que accion (RF18)"

    clinics {
        uuid clinicID PK
        text code UK
        text name
        text timeZone "zona IANA, validada por trigger"
        boolean isActive
    }
    users {
        uuid userID PK
        uuid clinicID FK "NULL solo para platformAdmin"
        text identityProviderSubject UK "el sub de Keycloak"
        text rolePK FK
        boolean isActive "baja logica (RF2)"
    }
    professionals {
        uuid professionalID PK
        uuid clinicID FK
        uuid userID UK
        uuid specialtyID FK
        text fullName
        text licenseCode "unico por clinica"
    }
    services {
        uuid serviceID PK
        uuid clinicID FK
        text name
        smallint durationMinutes "5..480, multiplo de 5"
        uuid specialtyID FK
    }
    professionalServices {
        uuid clinicID PK
        uuid professionalID PK
        uuid serviceID PK
        uuid specialtyID "redundante a proposito: fuerza la coincidencia"
    }
    patients {
        uuid patientID PK
        uuid clinicID FK
        text nationalID "unico por clinica"
        text firstName
        text lastName
        date birthDate
        text phone "dato auditado (RF18)"
        text email "dato auditado (RF18)"
    }
    workingHours {
        uuid workingHourID PK
        uuid clinicID FK
        uuid professionalID FK
        smallint weekday "1..7 ISO"
        time startTimeLocal "regla, no instante"
        time endTimeLocal
    }
    scheduleBlocks {
        uuid scheduleBlockID PK
        uuid clinicID FK
        uuid professionalID FK
        timestamptz startAt
        timestamptz endAt
        text reason
        uuid userID FK
    }
    appointments {
        uuid appointmentID PK
        uuid clinicID FK
        uuid patientID FK
        uuid professionalID FK
        uuid serviceID FK
        timestamptz startAt
        smallint durationMinutes "copiada del servicio y congelada (I4)"
        timestamptz endAt "derivada, la calcula el trigger"
        text appointmentStatusPK FK
        uuid rescheduledToAppointmentID FK "RF10"
    }
    clinicalNotes {
        uuid clinicalNoteID PK
        uuid clinicID FK
        uuid appointmentID UK
        uuid professionalID "FK compuesta: obliga a que sea quien atendio"
        text content "el dato mas sensible del sistema"
    }
    auditLogs {
        bigint auditLogPK PK
        uuid clinicID FK
        bigint sequenceNo "unico por clinica"
        timestamptz occurredAt
        uuid userID FK
        text rolePK FK
        text auditActionPK FK
        uuid patientID FK
        jsonb metadata "que paso, nunca el dato"
        bytea previousHash
        bytea rowHash
    }
    auditChainHeads {
        uuid clinicID PK
        bigint lastSequenceNo
        bytea lastHash
    }
    roles {
        text rolePK PK "identico al rol de realm en Keycloak"
        text name
        text description
    }
    specialties {
        uuid specialtyID PK
        text code UK
        text name
    }
    appointmentStatuses {
        text appointmentStatusPK PK
        boolean isFinal "RF13"
        boolean occupiesSlot "I7"
    }
    appointmentStatusTransitions {
        text fromAppointmentStatusPK PK
        text toAppointmentStatusPK PK
    }
    auditActions {
        text auditActionPK PK
        boolean isWrite
    }
```


## 2. Decisiones 

### La máquina de estados de RF13 es dato, no código

`appointmentStatusTransitions` declara en filas qué transiciones existen, y el trigger `appointmentsBu20ValidateStatusTransition` la consulta en lugar de conocerla.

- Cambiar el ciclo de vida de la cita es un `INSERT` o un `DELETE`
- Los cuatro estados finales no admiten salida se expresa por ausencia de filas, no con
  una bandera: lo que no está declarado, no se puede.
- Al ser un trigger del motor, la transición se rechaza aunque la escritura no pase por la API,
  que es lo que la defensa pregunta de los invariantes.

### Reprogramar (RF10) no mueve la fila

La cita original pasa a `rescheduled` (estado final) y apunta a su sustituta vía
`rescheduledToAppointmentID`. Los triggers rechazan mover `startAt`, `patientID`,
`professionalID` o `serviceID` de una cita existente (`MC004`).

Se eligió así porque el historial del paciente (RF16) debe poder reconstruir la cadena completa
de reprogramaciones, y porque una cita es un hecho que se agendó, no deja de
haber ocurrido porque luego se moviera. `UNIQUE ("rescheduledToAppointmentID")` garantiza que
una cita sustituye a lo sumo a una,.

### `users` no guarda correo, ni nombre, ni hash de contraseña

Solo `identityProviderSubject`, `clinicID` y `rolePK`. Keycloak es autoridad sobre quien;
PostgreSQL sobre **a qué clínica y con qué rol**. El costo asumido: la bitácora de RF19 muestra
uuid, y la API tendría que resolver el nombre contra el proveedor si hiciera falta. Se acepta
porque minimiza el dato personal almacenado y porque deja una sola autoridad sobre la identidad.

`roles."rolePK"` es exactamente el nombre del rol de realm en Keycloak, para que la
traducción token → dominio sea directa y verificable.

### El horario es una regla; la cita, un hecho

`workingHours` usa `time` + día de semana ISO. `appointments` usa `timestamptz`. Convertir entre
ambos exige la `timeZone` de la clínica, y esa conversión se hace en SQL

Guardar el horario como instante sería un error de modelado: «los lunes de 8 a 12» no es un instante, y ante un cambio de horario de verano el instante correcto cambia mientras la regla no.

### La autoría de la nota clínica es estructural, no comprobada

`clinicalNotes` no guarda quién la escribió como dato suelto: su clave ajena es compuesta contra la cita.

```sql
FOREIGN KEY ("clinicID", "appointmentID", "professionalID")
    REFERENCES "appointments" ("clinicID", "appointmentID", "professionalID")
```

De modo que el `professionalID` de la nota solo puede ser el del profesional que figura en esa
cita.

### Los catálogos no llevan `clinicID`

Una especialidad médica no es propiedad de una clínica, y hacer los catálogos de tenant obligaría a sembrarlos tres veces e impediría comparar entre clínicas en la Etapa 2. El costo: una clínica no puede inventar su propia especialidad sin que la plataforma la añada. 

## 5. Datos semilla

`db/seed/01_seed.sql`, aplicado por `initdb.sh` cuando el volumen está vacío. 

| Contenido | Cantidad |
|---|---|
| Clínicas | 3: `santa-lucia`, `monteverde`, `guanacaste`, todas en `America/Costa_Rica` |
| Usuarios | 1 de plataforma + 4 por clínica (administrador, recepción y dos profesionales) |
| Profesionales | 2 por clínica, con especialidades distintas entre sí |
| Servicios, horarios, bloqueos, pacientes, citas, notas y bitácora | repartidos por las tres clínicas |
