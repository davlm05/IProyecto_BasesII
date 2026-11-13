from psycopg import Connection


def listSpecialties(connection: Connection) -> list[dict]:
    """Especialidades disponibles para servicios (RF3) y profesionales (RF4)."""
    cursor = connection.execute(
        """
        SELECT "specialtyID", "code", "name"
          FROM "specialties"
         ORDER BY "name"
        """
    )
    return cursor.fetchall()


def listRoles(connection: Connection) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT "rolePK", "name", "description"
          FROM "roles"
         ORDER BY "rolePK"
        """
    )
    return cursor.fetchall()


def listAppointmentStatuses(connection: Connection) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT "appointmentStatusPK", "name", "isFinal", "occupiesSlot"
          FROM "appointmentStatuses"
         ORDER BY "appointmentStatusPK"
        """
    )
    return cursor.fetchall()


def listAppointmentStatusTransitions(connection: Connection) -> list[dict]:
    cursor = connection.execute(
        """
        SELECT "fromAppointmentStatusPK", "toAppointmentStatusPK"
          FROM "appointmentStatusTransitions"
         ORDER BY "fromAppointmentStatusPK", "toAppointmentStatusPK"
        """
    )
    return cursor.fetchall()
