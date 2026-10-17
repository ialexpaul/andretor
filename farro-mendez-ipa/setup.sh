#!/usr/bin/env bash
# ==============================================================================
# FARRO MENDEZ CORPORATION S.A.C. - Script de Instalación Automatizada (Bash)
# ==============================================================================
set -e

echo "=========================================================="
echo "  FARRO MENDEZ CORPORATION S.A.C. - IPA Platform Setup     "
echo "=========================================================="

# 1. Verificar versión de Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[ERROR] Python 3 no está instalado o no se encuentra en el PATH."
    exit 1
fi

PYTHON_BIN=$(command -v python3 || command -v python)
echo "[OK] Detectado: $($PYTHON_BIN --version)"

# 2. Copiar .env.example si no existe .env
if [ ! -f ".env" ]; then
    echo "[INFO] Creando archivo .env a partir de .env.example..."
    cp .env.example .env
    echo "[OK] Archivo .env creado. Configure sus credenciales antes de iniciar producción."
else
    echo "[INFO] Archivo .env existente detectado."
fi

# 3. Instalar dependencias
echo "[INFO] Instalando dependencias desde requirements.txt..."
$PYTHON_BIN -m pip install -r requirements.txt

# 4. Instalar paquete en modo editable
echo "[INFO] Instalando paquete en modo editable..."
$PYTHON_BIN -m pip install -e . --no-deps

# 5. Ejecutar suite de pruebas
echo "[INFO] Ejecutando pruebas unitarias con pytest..."
$PYTHON_BIN -m pytest

echo ""
echo "=========================================================="
echo "  ¡Instalación y validación completadas exitosamente!     "
echo "  Para iniciar el servidor:                               "
echo "    uvicorn app.main:app --reload --port 8000             "
echo "=========================================================="
