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
