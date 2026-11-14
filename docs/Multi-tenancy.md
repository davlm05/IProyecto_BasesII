# Multi-tenancy

## 1. La decisión 

**Elegida: columna discriminadora 'clinicID` + Row-Level Security + claves ajenas compuestas.**

Las tres estrategias asilan igual de bien cuando el codigo es correcto. La eleccion correcta de las tecnicas es valorar lo que pasa si se implementa de forma incorrecta y aqui es donde el asilamiento importante.

- Con **columna discriminadora sola**, un `WHERE` olvidado produce una  respuesta con filas de otras clinicas, con código 200 y sin ningun error. El fallo es que el sistema sigue funcionando pero filtra datos ajenos. 
- Con **RLS**, ese mismo olvido produce un resultado vacio. El fallo es cerrado: la primera prueba que lo ejercite lo detecta, y el peor caso es una funcionalidad que no funciona no una filtracion de datos.
- El **esquema por *tenant*** tiene la mejor funcionalidad en la teoria, pero se complica con migraciones multiplicadas, multiples cargas de DDLs y mayor complijidad en general que puede ser simplificada con otras tecnicas si la implementacion se hace con cuidado.

Lo que se sacrifica al elegir RLS:

1. **Coste en tiempo de ejecución.** Cada consulta lleva un dato añadido y una llamada a`currentClinicID()`. 
2. **Una dependencia invisible.** Todo rol que consulte una tabla con RLS necesita `EXECUTE` sobre cada función de sus políticas.
3. **El rol dueño se salta las políticas.** `medicitasOwner` no tiene RLS y por eso la API nunca lo usa: su contraseña no se pasa al contenedor del servicio. 
4. **Depuración menos obvia.** No encontrar una fila puede ser un dato que no existe o un problema del contexto.

## 2. Las tres capas que sostienen la decisicion

### Capa 1 · Claves ajenas compuestas

Toda tabla de tenant declara `UNIQUE ("clinicID", <su PK>)` y toda referencia entre tablas de tenant incluye `clinicID`:

```sql
CONSTRAINT "appointmentsPatientFk"
    FOREIGN KEY ("clinicID", "patientID")
    REFERENCES "patients" ("clinicID", "patientID")
```

### Capa 2 · RLS 

`10_rls.sql` habilita RLS en las once tablas de *tenant*. Toda política compara contra `currentClinicID()`:

```sql
CREATE POLICY "appointmentsTenantIsolation" ON "appointments"
    FOR ALL USING ("clinicID" = "currentClinicID"())
            WITH CHECK ("clinicID" = "currentClinicID"());
```

Tres detalles que importan:

- `USING` y `WITH CHECK`, los dos. `USING` filtra lo que se lee y lo que se puede modificar; `WITH CHECK` valida lo que se escribe. Sin `WITH CHECK`, una clínica podría insertar filas en otra aunque no pudiera leerlas.
- `currentClinicID()` devuelve `NULL` sin contexto, y `"clinicID" = NULL` no es existe para ninguna fila. Una transacción sin contexto no ve nada.
- Las políticas por rol afinan la matriz de permisos dentro del tenant. 

### Capa 3 · El filtro explícito

Esta capa está aplicada en las escrituras todo `INSERT` pasa `clinicID` explícitamente desde `requestContext`, nunca desde la petición.

## 3. El contrato de la API: de donde sale la clinicID

`clinicID` nunca se acepta como entrada. Ninguna ruta, ningún parámetro de consulta y ningún campo de cuerpo lo lleva. Manipular el identificador de clínica en los parámetros es imposible porque el parámetro no existe; si se envía, FastAPI lo ignora.

El tenant se deriva del claim `sub` del token:

```
sub  →  resolveIdentity(sub)  →  (userID, clinicID, rolePK, professionalID)
```

`resolveIdentity` es el único punto del sistema donde se determina la clínica. Si el token trae además un claim de clínica se compara con el valor de la base, y una desigualdad da `403 tenantClaimMismatch` más una entrada en el log del servicio.

`SET LOCAL`, nunca `SET`. El contexto se deposita con `set_config(..., true)`, de modo que una conexión devuelta al pool no arrastra el tenant de la petición anterior. 

```sql
SELECT set_config('app.currentClinicID',       $1, true),
       set_config('app.currentRoleCode',       $2, true),
       set_config('app.currentUserID',         $3, true),
       set_config('app.currentProfessionalID', $4, true);
```

Un pool de conexiones por rol de base de datos, de modo que los privilegios de tabla y de columna acotan cada petición además de RLS. `medicitasOwner` no tiene pool y su contraseña no llega al contenedor de la API. 