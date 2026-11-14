# Arquitectura del servicio de API

**Dependencias: Python + FastAPI + psycopg 3 + PyJWT**

## 1. Arquitectura de cuatro capas

```
router       valida la entrada, exige el rol, devuelve el código HTTP
   ↓
service      reglas de negocio, orquesta la auditoría
   ↓
repository   una función = una consulta
   ↓
PostgreSQL   
```

**La decisión central del diseño es el reparto de responsabilidad con la base de datos:** la base hace valer los invariantes y la API solo traduce el fallo. El servicio no comprueba si un espacio está libre antes de reservar: inserta, y si la restricción de exclusión devuelve `23P01`, responde `409`. 

## 2. SQL a mano y no un ORM

Se decidió no usarlo, por las siguientes razones:

2. **Cada transacción necesita cuatro `SET LOCAL` y hay un pool por rol.** Todo eso se construye alrededor del ORM, no con él, de modo que el ORM no ahorraría la parte difícil.
3. **Se exige justificar los índices con el plan de ejecución.** Por lo que es mas facil escribir las consultas textuales.
4. **RF7 es una consulta de rangos de tiempo** con conversión de zona horaria; en un ORM sería más
   difícil de leer, no menos.

El costo es que los repositorios devuelven `dict` en lugar de objetos, y los nombres de columna no se verifican hasta que la consulta corre. 

## 3. El ciclo de una petición

```
1.  Llega  Authorization: Bearer <token>
2.  tokenValidator   → firma contra el JWKS + iss + aud + exp ........ 401
3.  Se extrae SOLO el claim `sub`
4.  identityResolver → resolveIdentity(sub)
                       → userID, clinicID, rolePK, professionalID
                       sub no registrado / usuario inactivo .......... 403
                       el token declara otra clínica ................. 403
5.  requireRoles(...) compara el rol con la matriz de permisos ....... 403
6.  Se elige el pool según el rol  (reception → medicitasReception)
7.  Se abre la transacción y se depositan las cuatro variables de sesión
8.  service → repository → SQL
9.  COMMIT; el contexto muere con la transacción
```

**Un *pool* por rol de base de datos:**

```
platformAdmin  → medicitasPlatform       sin acceso a datos clínicos
clinicAdmin    → medicitasClinicAdmin    + la bitácora
reception      → medicitasReception      sin acceso a notas clínicas
professional   → medicitasProfessional   solo UPDATE de 3 columnas en citas
```

## 4. RF7 - Disponibilidad

El algoritmo, deliberadamente simple:

1. se pide al motor la duración del servicio (el tamaño del espacio a buscar);
2. los bloques de horario del profesional ese día, ya convertidos a instantes con la zona
   horaria de la clínica;
3. los intervalos ocupados: citas vigentes + bloqueos, en una sola consulta con `UNION ALL`;
4. se recorre cada bloque a pasos del tamaño del servicio, descartando lo que choque.

Tres decisiones:

- **El paso de la rejilla es la propia duración del servicio**, de modo que un servicio de 30
  minutos ofrece 08:00, 08:30, 09:00… y no cada 5 minutos. 
- **Los espacios ya pasados no se devuelven:** ofrecer algo que no se puede reservar no es
  disponibilidad.
- **La conversión de zona se hace en SQL**, `((fecha + wh."startTimeLocal") AT TIME ZONE
  c."timeZone")`.


## 5. El modelo de errores

Formato **RFC 9457 «Problem Details for HTTP APIs»**, con tipo de contenido`application/problem+json`:

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

Los tres desenlaces de la reserva:

| Desenlace | Código | `errorCode` |
|---|---|---|
| Concedida | `201` | — |
| Espacio ya tomado | `409` | `slotTaken` |
| Solicitud inválida | `422` | `invalidRequest`, `outsideWorkingHours`, `scheduleBlocked`, `professionalNotEnabledForService`, `relatedResourceNotFound` según la causa |
### 
## 6. Decisiones de diseño de las rutas

**Los cambios de estado son `POST` sobre un sub-recurso:**
`/appointments/{id}/cancel` y no `PATCH {"status": "cancelled"}`. Cancelar no es escribir
`cancelled` en una columna, es una operación con sus propias reglas y sus propios datos
obligatorios. 

**La nota clínica es `PUT`** porque hay como máximo una por cita (`UNIQUE ("appointmentID")`):
repetir la llamada corrige el contenido en lugar de crear una segunda.

**Ninguna ruta acepta un identificador de clínica**, y `/health` es la única sin token.

### Ampliacion documentada de la matriz de permisos

1. **El profesional solo registra el desenlace de sus propias citas.** La matriz dice que el rol
   puede registrar desenlaces, sin acotarlo. Marcar como ausente al paciente de otro profesional altera la
   agenda de otro sin ninguna necesidad clínica. 
