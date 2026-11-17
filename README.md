# MediCitas — Proyecto 1

**Escuela:**
Escuela de Ingeniería en Computación

**Curso:**
Bases de datos II (IC-4302)

**Profesor:**
Kenneth Roberto Obando Rodríguez

**Estudiantes:** 
* David López Murillo
* Tomás Blando Reyes
* Lindsay Marín Sánchez

**Fecha:**
15 de noviembre de 2026

## Instrucciones para la ejecución

### Ejecución con Docker Compose

El repositorio de GitHub se debe clonar en su entorno local.

1. Una vez que se tienen los archivos del proyecto, abrir una terminal y dirigirse al directorio `IProyecto_BasesII` mediante el siguiente comando:

   ```bash
   cd X:/XXX/XXX/IProyecto_BasesII
   ```

2. Copiar el contenido del archivo `.env.example` a un nuevo archivo `.env` y configurar las variables de entorno según las necesidades del entorno de ejecución.

3. Ejecutar el siguiente comando para iniciar los servicios:

   ```bash
   docker compose up
   ```

4. Para detener los servicios, se debe ejecutar:

   ```bash
   docker compose down
   ```
   También, está la opción de eliminar todos los volúmenes creados con:

   ```bash
   docker compose down -v
   ```

## Pruebas automatizadas

El proyecto cuenta con una suite de pruebas automaatizadas en python usando unittest. Para verificar el correcto funcionamiento de las diferentes partes de la base de datos, seguridad y concurrencia.

### Requisitos de la prueba
1. Contar con docker y Python.
2.Configurar el env a partir de .env.example
3.Iniciar los servicios con docker
4.Crear el entrono virtual de python y tener las dependencias

En la carpeta con linea de comandos:

Crear el entorno virtual

```bash
py -3.13 -m venv .venv
 ```

Instalar dependencias
 ```bash
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
 ```

 Para ejecutar la suite
 ```bash
 .\.venv\Scripts\python.exe -m unittest discover -s tests -p"test_*.py" -v
 ```
Este comando ejecuta las pruebas generales del proyecto. Las tres pruebas que realizan operaciones directas de integridad sobre PostgreSQL se omiten de forma predeterminada.

Para habilitar todas las pruebas en una base de datos local de desarrollo, ejecutar primero:

 ```bash
set RUN_AUDIT_DB_TESTS=1
 ```
Y ejecutar la suite.

| Archivo | Cantidad | Funcionalidad verificada |
|---|---:|---|
| `test_disponibilidad.py` | 4 | Cálculo de horarios disponibles, intervalos ocupados y espacios consecutivos. |
| `test_transacciones.py` | 4 | Reintentos ante conflictos de serialización y bloqueos mutuos. |
| `test_seguridad_api.py` | 5 | Autenticación, tokens inválidos y permisos de acceso. |
| `test_aislamiento.py` | 4 | Aislamiento de información entre clínicas. |
| `test_citas_api.py` | 13 | Reservas, cancelaciones, reprogramaciones, concurrencia y restricciones de citas. |
| `test_auditoria.py` | 4 | Generación, consulta, aislamiento e integridad de auditoría. |
| `test_integridad_auditoria.py` | 3 | Protección contra modificaciones de auditoría y validación de campos inmutables. |
| `test_redis.py` | 6 | Almacenamiento, expiración, aislamiento e invalidación de caché. |
| `test_redis_fallos.py` | 1 | Comportamiento ante una desconexión simulada de Redis. |
| **Total** | **44** | |


## Declaración del uso de IA

Durante esta etapa se emplearon herramientas de inteligencia artificial como apoyo en tareas puntuales. A continuación se describen sus usos concretos:

   - Apoyo para el desarrollo de pruebas automatizadas.
   - Análisis de bugs o fallos durante la ejecución de código del proyecto, revisando como interactuan los distintos servicios de PostgreSQL, Redis, Docker Compose y Keycloak.
   - Se utilizó como apoyo para la escritura correcta y estructurada del README.MD

Todas las pruebas fueron ejecutadas manualmente en el entorno local y se verificó su comportamiento contra los servicios reales de Docker Compose, PostgreSQL y Keycloak. Las decisiones finales sobre la arquitectura, la adaptación al código existente y la validación de los resultados fueron realizadas por el grupo.
