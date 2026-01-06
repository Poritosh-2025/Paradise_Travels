#!/bin/bash
set -e

# ===========================================
# PARADISE - Docker Entrypoint
# ===========================================
# Unified entrypoint for all environments
# Automatically adapts based on ENVIRONMENT variable
# ===========================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Environment (default: local)
ENVIRONMENT="${ENVIRONMENT:-local}"

echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  PARADISE - Application Startup${NC}"
echo -e "${CYAN}  Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "${CYAN}  Time: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ===========================================
# Function: Wait for service
# ===========================================
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local max_attempts=${4:-30}
    local attempt=1

    echo -e "${YELLOW}⏳ Waiting for $service ($host:$port)...${NC}"
    
    while ! nc -z "$host" "$port" 2>/dev/null; do
        if [ $attempt -ge $max_attempts ]; then
            echo -e "${RED}✖ ERROR: $service not available after $max_attempts attempts${NC}"
            exit 1
        fi
        echo "   Attempt $attempt/$max_attempts - waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e "${GREEN}✔ $service is ready!${NC}"
}

# ===========================================
# Function: Run migrations with retry
# ===========================================
run_migrations() {
    local max_attempts=5
    local attempt=1
    
    echo -e "${YELLOW}⏳ Running database migrations...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if python manage.py migrate --noinput 2>&1; then
            echo -e "${GREEN}✔ Migrations completed successfully!${NC}"
            return 0
        else
            if [ $attempt -eq $max_attempts ]; then
                echo -e "${RED}✖ Migrations failed after $max_attempts attempts${NC}"
                return 1
            fi
            echo -e "${YELLOW}   Attempt $attempt/$max_attempts failed, retrying in 5s...${NC}"
            sleep 5
            attempt=$((attempt + 1))
        fi
    done
}

# ===========================================
# Wait for dependencies
# ===========================================
echo -e "${CYAN}[1/5] Checking dependencies...${NC}"

# Wait for PostgreSQL
wait_for_service "${DATABASE_HOST:-db}" "${DATABASE_PORT:-5432}" "PostgreSQL" 30

# Wait for Redis
wait_for_service "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" "Redis" 30

# ===========================================
# Collect static files
# ===========================================
echo ""
echo -e "${CYAN}[2/5] Collecting static files...${NC}"

if [ "$ENVIRONMENT" = "local" ] && [ "${SKIP_COLLECTSTATIC:-false}" = "true" ]; then
    echo -e "${YELLOW}   Skipped (SKIP_COLLECTSTATIC=true)${NC}"
else
    if python manage.py collectstatic --noinput 2>&1; then
        echo -e "${GREEN}✔ Static files collected!${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: collectstatic failed (non-critical)${NC}"
    fi
fi

# ===========================================
# Run migrations
# ===========================================
echo ""
echo -e "${CYAN}[3/5] Database migrations...${NC}"

if [ "${SKIP_MIGRATIONS:-false}" = "true" ]; then
    echo -e "${YELLOW}   Skipped (SKIP_MIGRATIONS=true)${NC}"
else
    run_migrations
fi

# ===========================================
# Seed data (if applicable)
# ===========================================
echo ""
echo -e "${CYAN}[4/5] Seeding data...${NC}"

if [ "${SKIP_SEED:-false}" = "true" ]; then
    echo -e "${YELLOW}   Skipped (SKIP_SEED=true)${NC}"
else
    if python manage.py seed_plans 2>&1; then
        echo -e "${GREEN}✔ Subscription plans seeded!${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: seed_plans failed or already seeded${NC}"
    fi
fi

# ===========================================
# Environment-specific setup
# ===========================================
echo ""
echo -e "${CYAN}[5/5] Environment setup...${NC}"

case "$ENVIRONMENT" in
    local|development)
        echo -e "${GREEN}✔ Local development mode${NC}"
        echo "   • Debug: ${DEBUG:-True}"
        echo "   • Hot reload: Enabled"
        ;;
    staging)
        echo -e "${GREEN}✔ Staging mode${NC}"
        echo "   • Debug: ${DEBUG:-False}"
        echo "   • Testing environment"
        ;;
    production|prod)
        echo -e "${GREEN}✔ Production mode${NC}"
        echo "   • Debug: ${DEBUG:-False}"
        echo "   • Security hardened"
        
        # Production safety checks
        if [ "${DEBUG:-False}" = "True" ] || [ "${DEBUG:-False}" = "true" ]; then
            echo -e "${RED}⚠ WARNING: DEBUG=True in production!${NC}"
        fi
        
        if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "django-insecure-paradise-fallback-key" ]; then
            echo -e "${RED}⚠ WARNING: Using insecure SECRET_KEY!${NC}"
        fi
        ;;
    *)
        echo -e "${YELLOW}⚠ Unknown environment: $ENVIRONMENT${NC}"
        ;;
esac

# ===========================================
# Start application
# ===========================================
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}  Starting application...${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

exec "$@"

# #!/bin/bash
# set -e

# echo "Starting application..."

# # Skip database wait - Django will retry connection
# echo "Collecting static files..."
# python manage.py collectstatic --noinput || true

# echo "Applying database migrations..."
# for i in $(seq 1 5); do
#   python manage.py migrate --noinput && break
#   echo "Migration attempt $i failed, retrying in 5 seconds..."
#   sleep 5
# done

# echo "Seeding subscription plans..."
# python manage.py seed_plans || true

# echo "Starting server..."
# exec "$@"
