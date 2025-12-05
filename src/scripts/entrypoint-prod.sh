#!/bin/bash
set -e

cd /home/runner/src

source venv/bin/activate

echo "=== BanBif Dashboard - Inicio de Produccion ==="

# Paso 1: Migrar esquema de BD (agrega tablas nuevas si no existen)
echo "[1/2] Migrando esquema de base de datos..."
python scripts/migrate_db.py --db data/dashboard.db

# Paso 2: Iniciar servidor de produccion
echo "[2/2] Iniciando servidor Gunicorn..."
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    app:app

