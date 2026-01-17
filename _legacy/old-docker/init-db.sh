#!/bin/bash
set -e

echo "========================================="
echo "Multi-Agent Database Initialization"
echo "========================================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h postgres -U postgres; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is ready!"

# Change to backend directory
cd /app

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

echo "Database initialization complete!"
echo "========================================="
