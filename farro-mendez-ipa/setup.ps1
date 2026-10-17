# ==============================================================================
# FARRO MENDEZ CORPORATION S.A.C. - Script de Instalación Automatizada (PowerShell)
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  FARRO MENDEZ CORPORATION S.A.C. - IPA Platform Setup     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verificar versión de Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python no está instalado o no se encuentra en el PATH." -ForegroundColor Red
    exit 1
}

$pyVersion = python --version
Write-Host "[OK] Detectado: $pyVersion" -ForegroundColor Green

# 2. Copiar .env.example si no existe .env
if (-not (Test-Path ".env")) {
    Write-Host "[INFO] Creando archivo .env a partir de .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[OK] Archivo .env creado. Configure sus credenciales antes de iniciar producción." -ForegroundColor Green
} else {
    Write-Host "[INFO] Archivo .env existente detectado." -ForegroundColor Gray
}

# 3. Instalar dependencias
Write-Host "[INFO] Instalando dependencias desde requirements.txt..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

# 4. Instalar paquete en modo editable para resolución de rutas
Write-Host "[INFO] Instalando proyecto en modo editable (pip install -e .)..." -ForegroundColor Yellow
python -m pip install -e . --no-deps

# 5. Ejecutar suite de pruebas unitarias
Write-Host "[INFO] Ejecutando pruebas unitarias con pytest..." -ForegroundColor Yellow
python -m pytest

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n==========================================================" -ForegroundColor Green
    Write-Host "  ¡Instalación y validación completadas exitosamente!     " -ForegroundColor Green
    Write-Host "  Para iniciar el servidor:                               " -ForegroundColor Green
    Write-Host "    uvicorn app.main:app --reload --port 8000             " -ForegroundColor White
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Host "[ADVERTENCIA] Algunas pruebas fallaron. Revise el log anterior." -ForegroundColor Red
}
