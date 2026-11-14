# Concurrencia

## 1. La pregunta rectora

> *Dos recepcionistas reservan el último espacio exactamente al mismo tiempo. ¿Qué hace el
> sistema, por qué, y cómo se demuestra?*

**Qué hace.** Una recibe `201 Created` con la cita. La otra recibe `409 slotTaken`.

Porque no hay comprobación separada de la escritura. La reserva es una sola sentencia:

```sql
INSERT INTO "appointments" ("clinicID", "patientID", "professionalID", "serviceID",
                            "startAt", "durationMinutes", "endAt", "createdByUserID")
VALUES (%s, %s, %s, %s, %s, 5, %s + interval '5 minutes', %s)
RETURNING ...
```

No hay un `SELECT` previo que compruebe si el espacio está libre. Si lo hubiera, entre ese
`SELECT` y el `INSERT` cabría la transacción de la otra recepcionista y las dos verían el
espacio libre: esa es exactamente la condición de carrera que el proyecto interroga. En su
lugar, las dos insertan, y quien decide es la restricción:

```sql
CONSTRAINT "appointmentsProfessionalNoOverlap" EXCLUDE USING gist (
    "professionalID" WITH =,
    tstzrange("startAt", "endAt", '[)') WITH &&
) WHERE ("appointmentStatusPK" NOT IN ('cancelled', 'rescheduled'))
```

Una restricción de exclusión se evalúa tomando bloqueos en el índice gist. La segunda
transacción no «consulta y decide»: se bloquea esperando a que la primera termine. Cuando la
primera hace `COMMIT`, la segunda despierta, encuentra la fila escrita y falla con
`23P01 exclusion_violation`. Si la primera hubiera hecho `ROLLBACK`, la segunda habría
continuado y ganado. No hay ventana entre comprobar y escribir porque no hay dos pasos.


## 2. El nivel de aislamiento, elegido y defendido

**`READ COMMITTED`**

| Nivel | Qué aportaría aquí | Veredicto |
|---|---|---|
| `READ UNCOMMITTED` | En PostgreSQL es idéntico a `READ COMMITTED` | irrelevante |
| **`READ COMMITTED`** | I1 e I2 los sostienen las `EXCLUDE`; la lectura de la cita antes de cancelar o cerrar ve el último estado confirmado | **elegido** |
| `REPEATABLE READ` | Evitaría lecturas no repetibles dentro de una transacción;  | innecesario |
| `SERIALIZABLE` | Garantías que las restricciones ya dan por lo que es inecesario | descartado |

