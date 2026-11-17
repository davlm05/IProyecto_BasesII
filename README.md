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


## Declaración del uso de IA

Durante esta etapa se emplearon herramientas de inteligencia artificial como apoyo en tareas puntuales. A continuación se describen sus usos concretos:

   - Apoyo para el desarrollo de pruebas automatizadas.
   - Análisis de bugs o fallos durante la ejecución de código del proyecto, revisando como interactuan los distintos servicios de PostgreSQL, Redis, Docker Compose y Keycloak.
   - Se utilizó como apoyo para la escritura correcta y estructurada del README.MD

Todas las pruebas fueron ejecutadas manualmente en el entorno local y se verificó su comportamiento contra los servicios reales de Docker Compose, PostgreSQL y Keycloak. Las decisiones finales sobre la arquitectura, la adaptación al código existente y la validación de los resultados fueron realizadas por el grupo.
