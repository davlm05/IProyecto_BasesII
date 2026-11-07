# =============================================================================
# MediCitas - Script de arranque y carga de datos
# =============================================================================
medicitasInitdb() {
    
    local schemaDir="${MEDICITAS_SCHEMA_DIR:-/schema}"
    local seedDir="${MEDICITAS_SEED_DIR:-/seed}"
    local missing=()
    local variableName

    for variableName in \
        MEDICITAS_OWNER_PASSWORD \
        MEDICITAS_PLATFORM_PASSWORD \
        MEDICITAS_CLINIC_ADMIN_PASSWORD \
        MEDICITAS_RECEPTION_PASSWORD \
        MEDICITAS_PROFESSIONAL_PASSWORD
    do
        if [ -z "${!variableName:-}" ]; then
            missing+=("$variableName")
        fi
    done

    if [ "${#missing[@]}" -gt 0 ]; then
        echo "Initdb.sh ERROR: Missing environment variables: ${missing[*]}" >&2
        return 1
    fi

    if [ ! -d "$schemaDir" ]; then
        echo "Initdb.sh ERROR: Schema directory does not exist: $schemaDir" >&2
        return 1
    fi

	echo "Initdb.sh INFO: Creating keycloak database..."

    if ! psql \
        --username "$POSTGRES_USER" \
        --dbname postgres \
        -tAc "SELECT 1 FROM pg_database WHERE datname='keycloakDB'" \
        | grep -q 1; then

        psql \
          --username "$POSTGRES_USER" \
          --dbname postgres \
          -c "CREATE DATABASE keycloakDB;"
    fi

    applyAsSuperuser() {
        psql -v ON_ERROR_STOP=1 --no-psqlrc \
             --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" "$@"
    }

    applyAsOwner() {
        psql -v ON_ERROR_STOP=1 --no-psqlrc \
             --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
             -c 'SET ROLE "medicitasOwner"' "$@"
    }

    local file
    local baseName

    for file in "$schemaDir"/*.sql; do
        baseName="$(basename "$file")"
        echo "Initdb.sh: applying $baseName"

        case "$baseName" in
            00_extensions.sql|01_roles.sql)
                applyAsSuperuser -f "$file"
                ;;
            12_roleCredentials.sql)
                applyAsSuperuser \
                    -v ownerPassword="$MEDICITAS_OWNER_PASSWORD" \
                    -v platformPassword="$MEDICITAS_PLATFORM_PASSWORD" \
                    -v clinicAdminPassword="$MEDICITAS_CLINIC_ADMIN_PASSWORD" \
                    -v receptionPassword="$MEDICITAS_RECEPTION_PASSWORD" \
                    -v professionalPassword="$MEDICITAS_PROFESSIONAL_PASSWORD" \
                    -f "$file"
                ;;
            *)
                applyAsOwner -f "$file"
                ;;
        esac
    done

    if [ -d "$seedDir" ]; then
        for file in "$seedDir"/*.sql; do
            [ -e "$file" ] || continue
            if ! grep -qvE '^[[:space:]]*(--.*)?$' "$file"; then
                echo "Initdb.sh ERROR: seed $(basename "$file") has no statements, skipping"
                continue
            fi
            echo "Initdb.sh: applying seed $(basename "$file")"
            applyAsOwner -f "$file"
        done
    fi

    echo "Initdb.sh: schema and seed applied"
}


( set -euo pipefail; medicitasInitdb )
medicitasInitdbStatus=$?

if [ "$medicitasInitdbStatus" -ne 0 ]; then
    echo "Initdb.sh ERROR: the initialization failed with code $medicitasInitdbStatus" >&2
    exit "$medicitasInitdbStatus"
fi
