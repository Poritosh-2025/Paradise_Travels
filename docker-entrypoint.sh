#!/bin/bash
set -e

# Wait for Postgres
if [ -n "$DATABASE_HOST" ]; then
  echo "Waiting for database at $DATABASE_HOST..."
  until pg_isready -h "$DATABASE_HOST" -p "${DATABASE_PORT:-5432}" >/dev/null 2>&1; do
    sleep 1
  done
  echo "Database is ready!"
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Applying database migrations..."
python manage.py migrate --noinput

# ADD THIS SECTION - Seed subscription plans
echo "Seeding subscription plans..."
python manage.py seed_plans || echo "seed_plans skipped or already done"

echo "Starting server..."
exec "$@"