ontrato de las rutas de la API

Este documento es el contrato completo de las 45 rutas que expone el servicio de API

---

## 1. Reglas transversales del contrato

### 1.1 Autenticación — RF17

Toda ruta salvo `GET /health` exige el encabezado:

```
Authorization: Bearer <access token de Keycloak>
```

| Situación | `errorCode` | HTTP |
|---|---|---|
| Sin encabezado `Authorization`, o sin la forma `Bearer <token>` | `missingToken` | 401 |
| Token vencido, firma inválida, `aud` o `iss` distintos, o sin claim `sub` | `invalidToken` | 401 |


### 1.2 `clinicID` nunca se acepta como entrada — I5

Ninguna ruta, ningún parámetro de ruta, ningún parámetro de consulta y ningún campo de
cuerpo de este contrato lleva un identificador de clínica. El tenant se deriva solo del
claim `sub`

| Situación | `errorCode` | HTTP |
|---|---|---|
| El `sub` del token no corresponde a ninguna fila de `users` | `unknownIdentity` | 403 |
| El usuario existe pero `isActive` es falso | `inactiveUser` | 403 |
| El token declara una clínica distinta de la de la base | `tenantClaimMismatch` | 403 |

### 1.3 Encabezados

| Encabezado | Dónde | Valor |
|---|---|---|
| `Authorization` | petición, obligatorio salvo `/health` | `Bearer <token>` |
| `Content-Type` | petición con cuerpo | `application/json` |
| `Content-Type` | respuesta correcta | `application/json` |
| `Content-Type` | respuesta de error | `application/problem+json` |

### 1.5 Formato de error uniforme

```json
{
  "type":      "/errors/slotTaken",
  "title":     "Espacio ya tomado",
  "status":    409,
  "detail":    "El espacio solicitado ya esta ocupado por otra cita vigente.",
  "instance":  "/appointments",
  "errorCode": "slotTaken"
}
```

`errorCode` es el miembro estable y en inglés: se programa contra él, no contra `title` ni
`detail`, que son texto en español.

Los fallos de validación de Pydantic añaden un miembro más:

```json
{
  "type": "/errors/invalidRequest",
  "title": "Solicitud invalida",
  "status": 422,
  "detail": "Alguno de los campos enviados no es valido. Revise 'validationErrors'.",
  "instance": "/appointments",
  "errorCode": "invalidRequest",
  "validationErrors": [
    { "field": "body.patientID", "message": "Input should be a valid UUID" }
  ]
}
```

### 
### 1.6 Tipos y formatos

- Todo identificador de entidad es `UUID`; un UUID mal formado en la ruta o en el cuerpo da
  **422** sin llegar al motor. 
- `startAt`, `endAt`, `createdAt`, `occurredAt` y demás instantes son `timestamptz` en ISO
  8601 con zona (`2026-03-02T14:00:00Z`).
- `birthDate`, `targetDate`, `fromDate` y `toDate` son fechas `date`, y las
  de consulta se interpretan en la zona horaria de la clínica.
- `startTimeLocal` y `endTimeLocal` son horas locales `time` (`08:00:00`), sin zona: el
  horario es una regla, no un instante.

---

## 2. Índice de rutas

| Método | Ruta | Roles autorizados | RF |
|---|---|---|---|
| GET | `/health` | sin token | — (criterio de aceptación 1) |
| POST | `/clinics` | `platformAdmin` | RF1 |
| GET | `/clinics` | `platformAdmin` | RF1 |
| GET | `/clinics/current` | `clinicAdmin`, `reception`, `professional` | RF1 |
| POST | `/users` | `clinicAdmin` | RF2 |
| GET | `/users` | `clinicAdmin` | RF2 |
| PATCH | `/users/{userID}/role` | `clinicAdmin` | RF2 |
| PATCH | `/users/{userID}/activeState` | `clinicAdmin` | RF2 |
| GET | `/specialties` | cualquier rol autenticado | RF3, RF4 |
| GET | `/roles` | cualquier rol autenticado | RF2 |
| GET | `/appointmentStatuses` | cualquier rol autenticado | RF13 |
| GET | `/appointmentStatuses/transitions` | cualquier rol autenticado | RF13 |
| POST | `/services` | `clinicAdmin` | RF3 |
| GET | `/services` | `clinicAdmin`, `reception`, `professional` | RF3 |
| PUT | `/services/{serviceID}` | `clinicAdmin` | RF3 |
| POST | `/professionals` | `clinicAdmin` | RF4 |
| GET | `/professionals` | `clinicAdmin`, `reception`, `professional` | RF4 |
| GET | `/professionals/{professionalID}/services` | `clinicAdmin`, `reception`, `professional` | RF4 |
| PUT | `/professionals/{professionalID}/services` | `clinicAdmin` | RF4 |
| PATCH | `/professionals/{professionalID}/activeState` | `clinicAdmin` | RF4 |
| POST | `/professionals/{professionalID}/workingHours` | `clinicAdmin`, `professional` (solo el propio) | RF5 |
| GET | `/professionals/{professionalID}/workingHours` | `clinicAdmin`, `reception`, `professional` | RF5 |
| DELETE | `/workingHours/{workingHourID}` | `clinicAdmin`, `professional` (solo el propio, vía RLS) | RF5 |
| POST | `/scheduleBlocks` | `clinicAdmin`, `professional` (solo el propio) | RF6 |
| GET | `/scheduleBlocks` | `clinicAdmin`, `reception`, `professional` | RF6 |
| GET | `/scheduleBlocks/{scheduleBlockID}/conflicts` | `clinicAdmin`, `reception`, `professional` | RF6 |
| DELETE | `/scheduleBlocks/{scheduleBlockID}` | `clinicAdmin`, `professional` (solo el propio) | RF6 |
| GET | `/availability/professional` | `clinicAdmin`, `reception`, `professional` | RF7 |
| GET | `/availability/service` | `clinicAdmin`, `reception`, `professional` | RF8 |
| POST | `/appointments` | `clinicAdmin`, `reception` | RF9 |
| POST | `/appointments/{appointmentID}/reschedule` | `clinicAdmin`, `reception` | RF10 |
| POST | `/appointments/{appointmentID}/cancel` | `clinicAdmin`, `reception` | RF11 |
| POST | `/appointments/{appointmentID}/outcome` | `clinicAdmin`, `reception`, `professional` (solo sus citas) | RF12, RF13 |
| GET | `/appointments/day` | `clinicAdmin`, `reception`, `professional` (solo la suya) | RF20 |
| GET | `/appointments/countsByStatus` | `clinicAdmin`, `reception` | RF21 |
| GET | `/appointments/{appointmentID}` | `clinicAdmin`, `reception`, `professional` | RF9, RF20 |
| PUT | `/appointments/{appointmentID}/clinicalNote` | `professional` (solo sus citas) | RF15, RF18 |
| GET | `/appointments/{appointmentID}/clinicalNote` | `professional` | RF15, RF18 |
| POST | `/patients` | `clinicAdmin`, `reception` | RF14, RF18 |
| GET | `/patients` | `clinicAdmin`, `reception`, `professional` | RF14 |
| GET | `/patients/{patientID}` | `clinicAdmin`, `reception`, `professional` | RF14, RF18 |
| PUT | `/patients/{patientID}` | `clinicAdmin`, `reception` | RF14, RF18 |
| GET | `/patients/{patientID}/appointments` | `clinicAdmin`, `reception`, `professional` | RF16, RF18 |
| GET | `/auditLogs` | `clinicAdmin` | RF19, RF18 |
| GET | `/auditLogs/verification` | `clinicAdmin` | módulo adicional (auditoría verificable) |

## 3. Rutas por router

### 3.0 Operación — `app/main.py`

#### `GET /health`

Sonda de vida. Es la única ruta sin token: el criterio de aceptación 1 pide poder comprobar
que la pila levantó sin credenciales.

- Parámetros: ninguno. Cuerpo de petición: ninguno.
- Respuesta **200**: `{"status": "ok", "service": "medicitas"}`

---

### 3.1 Administración — `app/routers/adminRouter.py`

#### `POST /clinics` — RF1

Da de alta una clínica y, en la misma transacción, su primer usuario administrador.

Roles: `platformAdmin`.

Cuerpo (`CreateClinicRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `code` | string | sí | 3–32 caracteres, patrón `^[a-z0-9][a-z0-9-]{1,30}[a-z0-9]$` |
| `name` | string | sí | 1–200 caracteres |
| `timeZone` | string | sí | 3–64 caracteres; que sea una zona IANA real lo valida el motor |
| `firstAdminIdentityProviderSubject` | string | sí | 1–255 caracteres; es el `sub` del usuario en Keycloak |

Respuesta **201** (`CreateClinicResponse`):

| Campo | Tipo |
|---|---|
| `clinic` | `ClinicResponse`: `clinicID` (UUID), `code`, `name`, `timeZone`, `isActive` (bool), `createdAt` (timestamptz) |
| `firstAdminUserID` | UUID |

| Código | `errorCode` | Causa |
|---|---|---|
| 201 | — | Clínica y primer administrador creados |
| 409 | `duplicateResource` | `23505`: ya existe una clínica con ese `code`, o ese `identityProviderSubject` ya está registrado |
| 422 | `unknownTimeZone` | `MC008`: `timeZone` no es una zona IANA válida |
| 422 | `constraintViolated` | `23514`: un `CHECK` del modelo rechaza los datos |

#### `GET /clinics` — RF1

Lista las clínicas de la plataforma. Roles: `platformAdmin`.

- Sin parámetros. Respuesta **200**: arreglo de `ClinicResponse`.

#### `GET /clinics/current` — RF1

Devuelve la clínica del usuario autenticado, derivada del token.

Roles: `clinicAdmin`, `reception`, `professional`.

- Sin parámetros. Respuesta **200**: `ClinicResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | La clínica derivada del token no existe |
| 422 | `invalidRequest` | El contexto no tiene clínica (caso de `platformAdmin`, que de todos modos no pasa el filtro de rol) |

#### `POST /users` — RF2

Da de alta un usuario de la clínica del solicitante. No se envía correo, nombre ni
contraseña: `users` solo guarda `identityProviderSubject`, `clinicID` y `rolePK`, porque
Keycloak es autoridad sobre *quién*.

Roles: `clinicAdmin`.

Cuerpo (`CreateUserRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `identityProviderSubject` | string | sí | 1–255 caracteres |
| `rolePK` | string | sí | patrón `^(clinicAdmin\|reception\|professional)$` |

Respuesta **201** (`UserResponse`): `userID` (UUID), `clinicID` (UUID o null),
`identityProviderSubject`, `rolePK`, `isActive` (bool), `deactivatedAt` (timestamptz o
null), `createdAt`.

| Código | `errorCode` | Causa |
|---|---|---|
| 409 | `duplicateResource` | `23505`: ese `identityProviderSubject` ya existe |
| 422 | `relatedResourceNotFound` | `23503`: el `rolePK` no existe en el catálogo |

#### `GET /users` — RF2

Lista los usuarios de la clínica. Roles: `clinicAdmin`.

- Sin parámetros. Respuesta **200**: arreglo de `UserResponse`.

#### `PATCH /users/{userID}/role` — RF2

Roles: `clinicAdmin`.

- Parámetro de ruta: `userID` (UUID).
- Cuerpo (`UpdateUserRoleRequest`): `rolePK` (string, obligatorio, patrón
  `^(clinicAdmin|reception|professional)$`).
- Respuesta **200**: `UserResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El usuario no existe en su clínica (RLS no devolvió la fila) |

#### `PATCH /users/{userID}/activeState` — RF2

Baja lógica o reactivación. Roles: `clinicAdmin`.

- Parámetro de ruta: `userID` (UUID).
- Cuerpo (`UpdateUserActiveStateRequest`): `isActive` (bool, obligatorio).
- Respuesta **200**: `UserResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El usuario no existe en su clínica |

#### `GET /specialties`

Catálogo global de especialidades. Roles: cualquiera autenticado.

Respuesta **200**: arreglo de `SpecialtyResponse` — `specialtyID` (UUID), `code`, `name`.

#### `GET /roles` — RF2

Catálogo de roles del sistema. Roles: cualquiera autenticado.

Respuesta **200**: arreglo de `RoleResponse` — `rolePK`, `name`, `description`.

#### `GET /appointmentStatuses` — RF13

Roles: cualquiera autenticado.

Respuesta **200**: arreglo de `AppointmentStatusResponse` — `appointmentStatusPK`, `name`,
`isFinal` (bool), `occupiesSlot` (bool).

#### `GET /appointmentStatuses/transitions` — RF13

La máquina de estados es dato, no código: esta ruta expone las filas de
`appointmentStatusTransitions` que el trigger consulta. «No admiten salida» se expresa por
ausencia de filas.

Roles: cualquiera autenticado.

Respuesta **200**: arreglo de `AppointmentStatusTransitionResponse` —
`fromAppointmentStatusPK`, `toAppointmentStatusPK`.

#### `POST /services` — RF3

Roles: `clinicAdmin`.

Cuerpo (`CreateServiceRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `name` | string | sí | 1–200 caracteres |
| `description` | string o null | no (default `null`) | máximo 1000 caracteres |
| `durationMinutes` | entero | sí | 5 ≤ valor ≤ 480 y múltiplo de 5 |
| `specialtyID` | UUID | sí | — |

Respuesta **201** (`ServiceResponse`): `serviceID`, `clinicID`, `name`, `description`,
`durationMinutes`, `specialtyID`, `specialtyName` (string o null), `isActive`, `createdAt`.

| Código | `errorCode` | Causa |
|---|---|---|
| 409 | `duplicateResource` | `23505`: ya existe un servicio con ese nombre en la clínica |
| 422 | `relatedResourceNotFound` | `23503`: la especialidad no existe |

#### `GET /services` — RF3

Roles: `clinicAdmin`, `reception`, `professional`.

- Parámetro de consulta: `onlyActive` (bool, default `true`; con `false` incluye los
  inactivos).
- Respuesta **200**: arreglo de `ServiceResponse`.

#### `PUT /services/{serviceID}` — RF3

Reemplazo completo. Roles: `clinicAdmin`.

- Parámetro de ruta: `serviceID` (UUID).
- Cuerpo (`UpdateServiceRequest`): `name` (string, sí, 1–200), `description` (string o null,
  no, ≤1000), `durationMinutes` (entero, sí, 5–480 múltiplo de 5), `isActive` (bool, sí).
- Respuesta **200**: `ServiceResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El servicio no existe en su clínica |
| 409 | `duplicateResource` | `23505`: el nombre choca con otro servicio de la clínica |

Cambiar `durationMinutes` no altera la duración de las citas ya creadas: I4 la congela en la
cita (`MC011`).

#### `POST /professionals` — RF4

Registra un profesional y, en la misma transacción, los servicios que queda habilitado para
atender.

Roles: `clinicAdmin`.

Cuerpo (`CreateProfessionalRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `userID` | UUID | sí | usuario de la clínica con rol `professional` |
| `specialtyID` | UUID | sí | — |
| `fullName` | string | sí | 1–200 caracteres |
| `licenseCode` | string o null | no (default `null`) | máximo 50 caracteres |
| `serviceIDs` | arreglo de UUID | no (default `[]`) | — |

Respuesta **201** (`ProfessionalResponse`): `professionalID`, `clinicID`, `userID`,
`specialtyID`, `specialtyName` (string o null), `fullName`, `licenseCode`, `isActive`,
`createdAt`.

| Código | `errorCode` | Causa |
|---|---|---|
| 409 | `duplicateResource` | `23505`: ese `userID` ya es profesional, o el `licenseCode` se repite |
| 422 | `relatedResourceNotFound` | `23503`: el usuario, la especialidad o alguno de los `serviceIDs` no existe dentro de su clínica |

#### `GET /professionals` — RF4

Roles: `clinicAdmin`, `reception`, `professional`.

- Parámetro de consulta: `onlyActive` (bool, default `true`).
- Respuesta **200**: arreglo de `ProfessionalResponse`.

#### `GET /professionals/{professionalID}/services` — RF4

Roles: `clinicAdmin`, `reception`, `professional`.

- Parámetro de ruta: `professionalID` (UUID).
- Respuesta **200**: arreglo de `ProfessionalServiceResponse` — `serviceID`, `name`,
  `durationMinutes`, `isActive`. Un profesional de otra clínica no da 404 aquí: devuelve un
  arreglo vacío, porque RLS filtra las filas y la ruta no verifica antes la existencia del
  profesional.

#### `PUT /professionals/{professionalID}/services` — RF4

Reemplaza el conjunto completo de servicios habilitados. Roles: `clinicAdmin`.

- Parámetro de ruta: `professionalID` (UUID).
- Cuerpo (`ReplaceProfessionalServicesRequest`): `serviceIDs` (arreglo de UUID,
  obligatorio; un arreglo vacío deja al profesional sin servicios).
- Respuesta **200**: arreglo de `ProfessionalServiceResponse` con el estado resultante.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El profesional no existe en su clínica |
| 422 | `relatedResourceNotFound` | `23503`: alguno de los `serviceIDs` no existe en su clínica |
| 409 | `duplicateResource` | `23505`: el arreglo trae un `serviceID` repetido |

#### `PATCH /professionals/{professionalID}/activeState` — RF4

Roles: `clinicAdmin`.

- Parámetro de ruta: `professionalID` (UUID).
- Cuerpo (`UpdateProfessionalActiveStateRequest`): `isActive` (bool, obligatorio).
- Respuesta **200**: `ProfessionalResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El profesional no existe en su clínica |

Desactivar un profesional retira su disponibilidad hacia adelante (`MC005` al reservar) pero
no cancela por su cuenta las citas ya reservadas.

---

### 3.2 Agenda y disponibilidad — `app/routers/scheduleRouter.py`

#### `POST /professionals/{professionalID}/workingHours` — RF5

Añade un bloque al horario semanal. Admite varios bloques por día, lo que cubre la jornada
partida que pide RF5.

Roles: `clinicAdmin`, `professional` (y un profesional solo sobre sí mismo).

- Parámetro de ruta: `professionalID` (UUID).
- Cuerpo (`CreateWorkingHourRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `weekday` | entero | sí | 1 ≤ valor ≤ 7 |
| `startTimeLocal` | time | sí | hora local, sin zona |
| `endTimeLocal` | time | sí | `startTimeLocal` debe ser estrictamente anterior (validador de modelo) |

Respuesta **201** (`WorkingHourResponse`): `workingHourID`, `clinicID`, `professionalID`,
`weekday`, `startTimeLocal`, `endTimeLocal`, `createdAt`.

| Código | `errorCode` | Causa |
|---|---|---|
| 403 | `forbiddenNotOwnResource` | Un profesional intenta tocar el horario de otro |
| 404 | `resourceNotFound` | El profesional no existe en su clínica |
| 409 | `duplicateResource` | `23505`: el bloque ya existe |
| 422 | `constraintViolated` | `23514`: un `CHECK` del modelo rechaza el rango |

Tras el commit se invalida la caché de disponibilidad de ese profesional (I8).

#### `GET /professionals/{professionalID}/workingHours` — RF5

Roles: `clinicAdmin`, `reception`, `professional`.

- Parámetro de ruta: `professionalID` (UUID).
- Respuesta **200**: arreglo de `WorkingHourResponse` (vacío si el profesional no es de su
  clínica).

#### `DELETE /workingHours/{workingHourID}` — RF5

Roles: `clinicAdmin`, `professional`. La pertenencia aquí **no** se comprueba en la
aplicación: el `DELETE` va directo y es la política RLS la que decide qué filas ve el
perfil, de modo que un bloque ajeno simplemente no se borra y la respuesta es 404.

- Parámetro de ruta: `workingHourID` (UUID).
- Respuesta **204**: sin cuerpo.

| Código | `errorCode` | Causa |
|---|---|---|
| 204 | — | Bloque retirado; se invalida la caché del profesional afectado |
| 404 | `resourceNotFound` | «El bloque de horario no existe o no es suyo» |

#### `POST /scheduleBlocks` — RF6

Registra un bloqueo por vacaciones o permiso. Retira la disponibilidad hacia adelante y
**no** cancela las citas ya reservadas que caigan dentro: se listan como conflictos en la
ruta siguiente.

Roles: `clinicAdmin`, `professional` (solo sobre sí mismo).

Cuerpo (`CreateScheduleBlockRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `professionalID` | UUID | sí | — |
| `startAt` | timestamptz | sí | ISO 8601 con zona |
| `endAt` | timestamptz | sí | `startAt` debe ser estrictamente anterior (validador de modelo) |
| `reason` | string | sí | 1–500 caracteres |

Respuesta **201** (`ScheduleBlockResponse`): `scheduleBlockID`, `clinicID`,
`professionalID`, `startAt`, `endAt`, `reason`, `userID` (quien lo registró), `createdAt`.

| Código | `errorCode` | Causa |
|---|---|---|
| 403 | `forbiddenNotOwnResource` | Un profesional bloquea la agenda de otro |
| 404 | `resourceNotFound` | El profesional no existe en su clínica |
| 409 | `slotTaken` | `23P01`: el bloqueo se solapa con otro bloqueo del mismo profesional |
| 422 | `constraintViolated` | `23514`: un `CHECK` del modelo rechaza el rango |

#### `GET /scheduleBlocks` — RF6

Roles: `clinicAdmin`, `reception`, `professional`.

| Parámetro de consulta | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `fromDate` | date | sí | primer día del rango, inclusive |
| `toDate` | date | sí | último día del rango, inclusive |
| `professionalID` | UUID | no | si se omite, devuelve los de toda la clínica |

Respuesta **200**: arreglo de `ScheduleBlockResponse`. No hay tope de rango en esta ruta.

#### `GET /scheduleBlocks/{scheduleBlockID}/conflicts` — RF6

Las citas vigentes que caen dentro del bloqueo, para que recepción las reprograme.

Roles: `clinicAdmin`, `reception`, `professional`.

- Parámetro de ruta: `scheduleBlockID` (UUID).
- Respuesta **200**: arreglo de `ConflictingAppointmentResponse` — `appointmentID`,
  `patientID`, `professionalID`, `serviceID`, `startAt`, `endAt`, `appointmentStatusPK`,
  `firstName`, `lastName`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El bloqueo no existe en su clínica |

#### `DELETE /scheduleBlocks/{scheduleBlockID}` — RF6

Roles: `clinicAdmin`, `professional` (solo los propios).

- Parámetro de ruta: `scheduleBlockID` (UUID).
- Respuesta **204**: sin cuerpo; se invalida la caché del profesional del bloqueo.

| Código | `errorCode` | Causa |
|---|---|---|
| 403 | `forbiddenNotOwnResource` | Un profesional levanta el bloqueo de otro |
| 404 | `resourceNotFound` | El bloqueo no existe en su clínica, o el `DELETE` no afectó ninguna fila |

#### `GET /availability/professional` — RF7

Espacios libres de un profesional en una fecha, a partir de su horario, de la duración del
servicio (I4), de sus bloqueos y de las citas vigentes. Es la consulta más frecuente del
sistema y la única con caché.

Roles: `clinicAdmin`, `reception`, `professional`.

| Parámetro de consulta | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `professionalID` | UUID | sí | — |
| `serviceID` | UUID | sí | determina el tamaño del espacio buscado (I4) |
| `targetDate` | date | sí | se interpreta en la zona horaria de la clínica |

Respuesta **200** (`ProfessionalAvailabilityResponse`):

| Campo | Tipo |
|---|---|
| `professionalID` | UUID |
| `professionalName` | string o null |
| `serviceID` | UUID |
| `durationMinutes` | entero |
| `targetDate` | date |
| `availableSlots` | arreglo de `{ "startAt": timestamptz, "endAt": timestamptz }` |

La rejilla avanza a pasos de la duración del servicio y los espacios ya pasados no se
devuelven. Si el profesional no atiende ese día, `availableSlots` es un arreglo vacío.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El servicio no existe o no está activo en su clínica |
| 404 | `resourceNotFound` | El profesional no existe en su clínica: es el resultado que delata un intento de cruzar la frontera de tenant (I5) |

#### `GET /availability/service` — RF8

Los profesionales que tienen espacio para un servicio en un rango de fechas, y cuáles son.
Solo se devuelven las combinaciones de profesional y día con al menos un espacio libre.

Roles: `clinicAdmin`, `reception`, `professional`.

| Parámetro de consulta | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `serviceID` | UUID | sí | — |
| `fromDate` | date | sí | — |
| `toDate` | date | sí | el rango está topado a 31 días |

Respuesta **200** (`ServiceAvailabilityResponse`): `serviceID`, `durationMinutes`,
`fromDate`, `toDate`, `availabilityByProfessional` (arreglo de
`ProfessionalAvailabilityResponse`, uno por combinación de profesional y día con espacio).

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | `toDate` anterior a `fromDate` |
| 404 | `resourceNotFound` | El rango excede 31 días |
| 404 | `resourceNotFound` | El servicio no existe o no está activo en su clínica |

> Los dos primeros son errores de entrada que el código clasifica como `resourceNotFound`
> (404) y no como `invalidRequest` (422); ver la anotación 7 de la sección 6.

---

### 3.3 Citas — `app/routers/appointmentRouter.py`

#### `POST /appointments` — RF9

La operación crítica, la que la pregunta rectora interroga. **No hay `SELECT` previo** que
compruebe si el espacio está libre: se inserta, y si la restricción `EXCLUDE` devuelve
`23P01`, la respuesta es 409. Dos recepcionistas simultáneas sobre el último espacio
obtienen una 201 y una 409 `slotTaken`.

Roles: `clinicAdmin`, `reception`.

Cuerpo (`CreateAppointmentRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `patientID` | UUID | sí | debe ser de su clínica |
| `professionalID` | UUID | sí | debe estar habilitado para el servicio |
| `serviceID` | UUID | sí | — |
| `startAt` | timestamptz | sí | ISO 8601 con zona |

**`durationMinutes` y `endAt` no se envían.** Los asigna el trigger
`appointmentsBi10AssignTiming` leyendo la duración del servicio (I4): si el cliente pudiera
enviarlos, podría reservar 15 minutos para un servicio de 45 y romper la agenda.

Respuesta **201** (`AppointmentResponse`):

| Campo | Tipo |
|---|---|
| `appointmentID`, `clinicID`, `patientID`, `professionalID`, `serviceID` | UUID |
| `startAt`, `endAt`, `createdAt` | timestamptz |
| `durationMinutes` | entero |
| `appointmentStatusPK` | string (`reserved` al crearse) |
| `createdByUserID` | UUID |
| `cancelledAt`, `outcomeRecordedAt` | timestamptz o null |
| `cancelledByUserID`, `outcomeRecordedByUserID`, `rescheduledToAppointmentID` | UUID o null |
| `cancellationReason` | string o null |

| Código | `errorCode` | Causa |
|---|---|---|
| 201 | — | Reserva concedida |
| 409 | `slotTaken` | `23P01`: la restricción `EXCLUDE` detectó otra cita vigente solapada del mismo profesional (I1) o del mismo paciente (I2) |
| 409 | `serializationConflict` | `40001`/`40P01` tras agotar los 3 reintentos |
| 409 | `duplicateResource` | `23505` |
| 422 | `outsideWorkingHours` | `MC001`: fuera del horario de atención del profesional (I3) |
| 422 | `scheduleBlocked` | `MC002`: dentro de un bloqueo de agenda (I3) |
| 422 | `professionalNotEnabledForService` | `MC005`: el profesional no atiende ese servicio, o alguno de los dos está inactivo |
| 422 | `appointmentCrossesMidnight` | `MC010`: la cita cruzaría la medianoche local de la clínica |
| 422 | `relatedResourceNotFound` | `23503`: paciente, profesional o servicio inexistente **dentro de su clínica** — es la respuesta a un identificador de otra clínica (I5) |

#### `POST /appointments/{appointmentID}/reschedule` — RF10

Reprogramar **no mueve la fila**: en una sola transacción se inserta la cita nueva y la
original pasa al estado final `rescheduled` apuntando a su sustituta con
`rescheduledToAppointmentID`. Ese orden —primero la nueva— lo exige el `CHECK`
`appointmentsRescheduleConsistent`.

Roles: `clinicAdmin`, `reception`.

- Parámetro de ruta: `appointmentID` (UUID).
- Cuerpo (`RescheduleAppointmentRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `startAt` | timestamptz | sí | nuevo instante de inicio |
| `professionalID` | UUID o null | no (default `null`) | si se omite, se conserva el profesional original |

El paciente y el servicio **no** se pueden cambiar: se heredan de la cita original.

Respuesta **200** (`RescheduleAppointmentResponse`): `originalAppointment` y
`newAppointment`, ambos `AppointmentResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 200 | — | Reprogramada: la original queda `rescheduled`, la nueva nace `reserved` |
| 404 | `resourceNotFound` | La cita no existe en su clínica |
| 409 | `appointmentNotReserved` | La cita no está en `reserved` (ya cancelada, atendida, ausente o reprogramada) |
| 409 | `rescheduleOverlapsOrigin` | La inserción de la nueva chocó con una `EXCLUDE`; incluye el caso de un espacio destino que se solapa con el original, limitación conocida porque la original sigue ocupando su espacio mientras se inserta la nueva |
| 409 | `invalidStatusTransition` | `MC003`: la transición no está declarada en `appointmentStatusTransitions` (RF13) |
| 409 | `serializationConflict` | `40001`/`40P01` tras agotar los reintentos |
| 422 | `outsideWorkingHours` / `scheduleBlocked` / `professionalNotEnabledForService` / `appointmentCrossesMidnight` | `MC001`, `MC002`, `MC005`, `MC010` sobre el espacio destino |

Tras el commit se invalida la caché del profesional original y, si cambió, también la del
nuevo: I7 exige que el espacio liberado se vea libre en la consulta siguiente.

#### `POST /appointments/{appointmentID}/cancel` — RF11

Roles: `clinicAdmin`, `reception`.

- Parámetro de ruta: `appointmentID` (UUID).
- Cuerpo (`CancelAppointmentRequest`): `cancellationReason` (string, obligatorio, 1–500
  caracteres).
- Respuesta **200**: `AppointmentResponse` con `appointmentStatusPK = "cancelled"`,
  `cancelledAt`, `cancelledByUserID` y `cancellationReason` llenos.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | La cita no existe en su clínica |
| 409 | `appointmentNotReserved` | La cita no está en `reserved` |
| 409 | `invalidStatusTransition` | `MC003`: transición no permitida (RF13) |

El espacio queda libre en el instante del commit: `cancelled` tiene `occupiesSlot = false` y
sale de los índices parciales (I7). Después del commit se invalida la caché.

#### `POST /appointments/{appointmentID}/outcome` — RF12

Roles: `clinicAdmin`, `reception`, `professional` — y un profesional solo sobre sus propias
citas (ampliación documentada de la matriz de permisos).

- Parámetro de ruta: `appointmentID` (UUID).
- Cuerpo (`RecordOutcomeRequest`): `appointmentStatusPK` (string, obligatorio, patrón
  `^(attended|absent)$`).
- Respuesta **200**: `AppointmentResponse` con `outcomeRecordedAt` y
  `outcomeRecordedByUserID` llenos.

| Código | `errorCode` | Causa |
|---|---|---|
| 403 | `forbiddenNotOwnResource` | Un profesional registra el desenlace de una cita de otro |
| 404 | `resourceNotFound` | La cita no existe en su clínica |
| 409 | `appointmentNotReserved` | La cita no está en `reserved` |
| 409 | `invalidStatusTransition` | `MC003` |
| 422 | `outcomeBeforeStart` | La cita todavía no ha empezado: RF12 solo admite el desenlace pasada la hora de inicio |

#### `GET /appointments/day` — RF20

La agenda del día, la vista con la que trabaja recepción.

Roles: `clinicAdmin`, `reception`, `professional`.

| Parámetro de consulta | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `targetDate` | date | sí | se interpreta en la zona horaria de la clínica |
| `professionalID` | UUID | no | si se omite, la agenda de toda la clínica |

Si el rol es `professional`, el `professionalID` recibido se **descarta** y se usa el del
solicitante: la matriz dice que consulta «su propia agenda».

Respuesta **200**: arreglo de `DayAgendaItemResponse` — `appointmentID`, `patientID`,
`professionalID`, `serviceID`, `startAt`, `endAt`, `durationMinutes`,
`appointmentStatusPK`, `firstName`, `lastName`, `nationalID`, `professionalName`,
`serviceName`.

#### `GET /appointments/countsByStatus` — RF21

Roles: `clinicAdmin`, `reception`.

| Parámetro de consulta | Tipo | Obligatorio |
|---|---|---|
| `fromDate` | date | sí |
| `toDate` | date | sí |

Respuesta **200**: arreglo de `AppointmentStatusCountResponse` — `appointmentStatusPK`,
`name`, `total` (entero). No hay tope de rango ni validación del orden de las fechas en esta
ruta: un rango invertido devuelve simplemente un resultado sin filas.

#### `GET /appointments/{appointmentID}`

Roles: `clinicAdmin`, `reception`, `professional`.

- Parámetro de ruta: `appointmentID` (UUID).
- Respuesta **200**: `AppointmentResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | La cita no existe en su clínica (también para un `appointmentID` real de otra clínica, I5) |

#### `PUT /appointments/{appointmentID}/clinicalNote` — RF15

El dato más sensible del sistema. Solo lo escribe el profesional que atendió la cita, y solo
sobre una cita en estado `attended` (`MC007`, hecho valer en el motor). Es `PUT` porque hay
como máximo una nota por cita: repetir la llamada corrige el contenido.

Roles: `professional` exclusivamente.

- Parámetro de ruta: `appointmentID` (UUID).
- Cuerpo (`WriteClinicalNoteRequest`): `content` (string, obligatorio, 1–20000 caracteres).
- Respuesta **200** (`ClinicalNoteResponse`): `clinicalNoteID`, `clinicID`, `appointmentID`,
  `professionalID`, `content`, `createdAt`, `updatedAt`.

| Código | `errorCode` | Causa |
|---|---|---|
| 403 | `forbiddenNotOwnResource` | La cita es de otro profesional |
| 404 | `resourceNotFound` | La cita no existe en su clínica |
| 409 | `appointmentNotAttended` | `MC007`: la cita no está en estado `attended` (RF15) |

Queda registrada en la bitácora como `writeClinicalNote`, en la misma transacción, con la
longitud del texto en los metadatos y nunca el texto (RF18).

#### `GET /appointments/{appointmentID}/clinicalNote` — RF15

Roles: `professional` exclusivamente. El administrador de clínica y recepción no tienen
siquiera privilegio de `SELECT` sobre `clinicalNotes`.

- Parámetro de ruta: `appointmentID` (UUID).
- Respuesta **200**: `ClinicalNoteResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | «La cita no tiene nota clínica, o la nota no es suya» — las dos causas comparten respuesta a propósito: distinguirlas revelaría la existencia de una nota ajena |

Queda registrada como `readClinicalNote` (RF18).

---

### 3.4 Pacientes — `app/routers/patientRouter.py`

#### `POST /patients` — RF14

Roles: `clinicAdmin`, `reception`.

Cuerpo (`CreatePatientRequest`):

| Campo | Tipo | Obligatorio | Validación |
|---|---|---|---|
| `nationalID` | string | sí | 5–30 caracteres, patrón `^[A-Za-z0-9-]{5,30}$`. Es la cédula, texto, no un UUID |
| `firstName` | string | sí | 1–100 caracteres |
| `lastName` | string | sí | 1–100 caracteres |
| `birthDate` | date | sí | no puede estar en el futuro, lo hace valer el motor (`MC009`) |
| `phone` | string o null | no (default `null`) | máximo 20 caracteres, patrón `^\+?[0-9 ()-]{7,20}$` |
| `email` | string o null | no (default `null`) | máximo 255 caracteres |

Respuesta **201** (`PatientResponse`): `patientID`, `clinicID`, `nationalID`, `firstName`,
`lastName`, `birthDate`, `phone`, `email`, `isActive`, `createdAt`, `updatedAt`.

| Código | `errorCode` | Causa |
|---|---|---|
| 409 | `duplicateResource` | `23505`: ya existe un paciente con ese `nationalID` en la clínica |
| 422 | `birthDateInFuture` | `MC009` |

Queda registrada como `writePatientContact` (RF18).

#### `GET /patients` — RF14

Roles: `clinicAdmin`, `reception`, `professional`.

| Parámetro de consulta | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `searchText` | string | no | busca por el inicio del apellido o del nombre, sin distinguir mayúsculas |

Respuesta **200**: arreglo de `PatientResponse`, solo pacientes activos, ordenado por
apellido y nombre, con tope de 200 filas. **Esta ruta no se audita**: existe para encontrar
a una persona y anotar cada búsqueda llenaría la bitácora de ruido.

#### `GET /patients/{patientID}` — RF14

Roles: `clinicAdmin`, `reception`, `professional`.

- Parámetro de ruta: `patientID` (UUID).
- Respuesta **200**: `PatientResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El paciente no existe en su clínica. Un `patientID` real de otra clínica da exactamente este 404 (I5) |

Queda registrada como `readPatientContact` (RF18).

#### `PUT /patients/{patientID}` — RF14

Reemplazo completo de los datos modificables. `nationalID` **no** se puede cambiar: no está
en el cuerpo.

Roles: `clinicAdmin`, `reception`.

- Parámetro de ruta: `patientID` (UUID).
- Cuerpo (`UpdatePatientRequest`): `firstName` (string, sí, 1–100), `lastName` (string, sí,
  1–100), `birthDate` (date, sí), `phone` (string o null, no, patrón
  `^\+?[0-9 ()-]{7,20}$`), `email` (string o null, no, ≤255).
- Respuesta **200**: `PatientResponse`.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El paciente no existe en su clínica |
| 422 | `birthDateInFuture` | `MC009` |

Queda registrada como `writePatientContact` (RF18).

#### `GET /patients/{patientID}/appointments` — RF16

Historial de citas del paciente dentro de su clínica, con el estado de cada una y la cadena
de reprogramaciones vía `rescheduledToAppointmentID`.

Roles: `clinicAdmin`, `reception`, `professional`.

- Parámetro de ruta: `patientID` (UUID).
- Respuesta **200**: arreglo de `PatientAppointmentHistoryItemResponse` — `appointmentID`,
  `professionalID`, `serviceID`, `startAt`, `endAt`, `appointmentStatusPK`,
  `cancellationReason` (string o null), `rescheduledToAppointmentID` (UUID o null),
  `professionalName`, `serviceName`.

No hay ningún campo que indique si la cita tiene nota clínica: «existe una nota sobre este
paciente» ya es información sobre el dato más sensible del sistema, y recepción no tiene
privilegio para saberlo.

| Código | `errorCode` | Causa |
|---|---|---|
| 404 | `resourceNotFound` | El paciente no existe en su clínica |

Queda registrada como `readPatientHistory` (RF18).

---

### 3.5 Auditoría — `app/routers/auditRouter.py`

#### `GET /auditLogs` — RF19

Consulta de la bitácora, reservada al administrador de la clínica. Quien la consulta queda
él mismo auditado (`readAuditLog`), porque es el rol con más alcance sobre datos de
pacientes.

Roles: `clinicAdmin`.

| Parámetro de consulta | Tipo | Obligatorio | Nota |
|---|---|---|---|
| `userID` | UUID | no | filtra por el usuario que realizó la acción |
| `patientID` | UUID | no | filtra por el paciente afectado |
| `fromDate` | date | no | desde esta fecha, en la zona de la clínica |
| `toDate` | date | no | hasta esta fecha, **inclusive** |

Respuesta **200**: arreglo de `AuditLogResponse`, ordenado por `sequenceNo` descendente, con
tope de 500 filas:

| Campo | Tipo |
|---|---|
| `auditLogPK` | entero |
| `clinicID` | UUID |
| `sequenceNo` | entero (por clínica) |
| `occurredAt` | timestamptz |
| `userID` | UUID o null |
| `rolePK` | string |
| `auditActionPK` | string (`readPatientContact`, `writePatientContact`, `readPatientHistory`, `readClinicalNote`, `writeClinicalNote`, `readAuditLog`) |
| `entityType` | string |
| `entityID` | UUID o null |
| `patientID` | UUID o null |
| `requestID` | UUID o null |
| `metadata` | objeto JSON: dice **qué** pasó, nunca el dato sensible en sí |
| `previousHashHex` | string hexadecimal |
| `rowHashHex` | string hexadecimal |

No hay escritura, actualización ni borrado de la bitácora por API: I6 la hace append-only en
el motor (`auditLogsBud10PreventMutation` más `REVOKE UPDATE, DELETE, TRUNCATE`). Un intento
de mutarla desde la base devuelve `MC006` → **403 `auditLogImmutable`**.

#### `GET /auditLogs/verification`

Módulo adicional del grupo de tres (opción 1, auditoría verificable). Recorre la cadena de
huellas de la clínica del solicitante llamando a `verifyAuditChain(clinicID)`.

Roles: `clinicAdmin`. Sin parámetros: la clínica se deriva del token.

Respuesta **200** (`AuditChainVerificationResponse`):

| Campo | Tipo |
|---|---|
| `clinicID` | UUID |
| `isIntact` | bool (`true` si no hay anomalías) |
| `anomalies` | arreglo de `AuditChainAnomalyResponse` |

`AuditChainAnomalyResponse`: `sequenceNo` (entero o null), `auditLogPK` (entero o null),
`anomaly` (string), `detail` (string). Los cuatro valores posibles de `anomaly` son
`missingSequence`, `brokenLink`, `tamperedRow` y `headMismatch`; el último es el único que
delata el borrado del *final* de la cadena, que no deja hueco.

---

## 4. Catálogo de errores

### 5.1 Errores propios de la aplicación (`app/errors.py`)

| `errorCode` | HTTP | `title` | Significado |
|---|---|---|---|
| `missingToken` | 401 | Falta el token de acceso | No hay `Authorization`, o no tiene la forma `Bearer <token>` |
| `invalidToken` | 401 | Token de acceso inválido | Vencido, firma inválida, `aud` o `iss` distintos, o sin claim `sub` |
| `unknownIdentity` | 403 | Identidad no registrada en la plataforma | El `sub` no corresponde a ningún usuario |
| `inactiveUser` | 403 | Usuario desactivado | El usuario existe pero está dado de baja lógicamente |
| `tenantClaimMismatch` | 403 | El token declara una clínica que no le corresponde | Un claim de clínica del token no coincide con la base (I5) |
| `forbiddenRole` | 403 | Su rol no permite esta operación | `requireRoles` rechazó el `rolePK` |
| `forbiddenNotOwnResource` | 403 | Solo puede operar sobre sus propios registros | Un profesional sobre el horario, el bloqueo, el desenlace o la nota de otro |
| `resourceNotFound` | 404 | Recurso no encontrado | La fila no existe para esa transacción, también cuando es de otra clínica |
| `invalidRequest` | 422 | Solicitud inválida | Validación de Pydantic; añade `validationErrors` |
| `outcomeBeforeStart` | 422 | La cita todavía no ha empezado | RF12 solo admite desenlace pasada la hora de inicio |
| `appointmentNotReserved` | 409 | La cita ya tiene un estado final | Cancelar, reprogramar o registrar desenlace sobre una cita que no está en `reserved` |
| `rescheduleOverlapsOrigin` | 409 | El espacio destino se solapa con el de la cita original | `23P01` capturado durante RF10 |
| `httpError` | varía | Error de la solicitud | `HTTPException` de Starlette que no es 404 (por ejemplo 405 por método no permitido) |
| `internalError` | 500 | Error interno del servicio | Excepción no prevista; el rastro va al log, nunca al cuerpo |
| `databaseError` | 500 | Error de base de datos | SQLSTATE que no está en la tabla siguiente |

### 5.2 Traducción SQLSTATE y códigos `MC` (`PROBLEM_BY_SQLSTATE`)

| SQLSTATE | HTTP | `errorCode` | Significado |
|---|---|---|---|
| `MC001` | 422 | `outsideWorkingHours` | La cita no cae dentro del horario de atención del profesional (I3) |
| `MC002` | 422 | `scheduleBlocked` | La cita cae dentro de un bloqueo de agenda del profesional (I3) |
| `MC003` | 409 | `invalidStatusTransition` | El ciclo de vida de la cita no admite esa transición (RF13) |
| `MC004` | 409 | `appointmentImmutable` | Intento de mover o reasignar una cita existente; para cambiar su espacio hay que reprogramarla (RF10) |
| `MC005` | 422 | `professionalNotEnabledForService` | El profesional no está habilitado para ese servicio, o uno de los dos está inactivo (RF4) |
| `MC006` | 403 | `auditLogImmutable` | Intento de modificar la bitácora, que solo admite agregar (I6) |
| `MC007` | 409 | `appointmentNotAttended` | Nota clínica sobre una cita que no está atendida (RF15) |
| `MC008` | 422 | `unknownTimeZone` | La zona horaria no es una zona IANA válida (RF1) |
| `MC009` | 422 | `birthDateInFuture` | Fecha de nacimiento en el futuro (RF14) |
| `MC010` | 422 | `appointmentCrossesMidnight` | La cita cruzaría la medianoche local de la clínica |
| `MC011` | 409 | `appointmentDurationImmutable` | Intento de alterar la duración, que la determina el servicio (I4) |
| `23P01` | 409 | `slotTaken` | Violación de una restricción `EXCLUDE`: el espacio ya está ocupado por otra cita vigente (I1, I2). Es el rechazo del perdedor de la carrera de RF9 y **no se reintenta** |
| `23505` | 409 | `duplicateResource` | Violación de unicidad: ya existe un registro con esos datos |
| `23503` | 422 | `relatedResourceNotFound` | Violación de clave ajena: alguno de los recursos referenciados no existe **dentro de su clínica**, que es lo que devuelven las claves ajenas compuestas ante un identificador de otro tenant (I5) |
| `23514` | 422 | `constraintViolated` | Violación de un `CHECK` del modelo |
| `23502` | 422 | `missingRequiredField` | Falta un campo obligatorio del registro |
| `42501` | 403 | `insufficientDatabasePrivilege` | El perfil de base de datos del rol no tiene privilegio sobre ese dato, o la fila viola el `WITH CHECK` de una política RLS |
| `40001` | 409 | `serializationConflict` | Fallo de serialización tras agotar los reintentos |
| `40P01` | 409 | `serializationConflict` | Bloqueo mutuo entre transacciones tras agotar los reintentos |

