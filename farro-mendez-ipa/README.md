# 🏪 FARRO MENDEZ CORPORATION S.A.C. — IPA Platform

> **Automatización Inteligente de Procesos (IPA)**  
> Sistema de atención de pedidos por WhatsApp con Flujo RPA Orquestado y Flujo Agéntico con Gemini.

---

## 📋 Descripción del Proyecto

Este repositorio implementa la digitalización y automatización del proceso de **Atención de Pedidos Digitales por WhatsApp (modelo BPMN TO-BE)** para la empresa FARRO MENDEZ CORPORATION S.A.C.

### Problema que resuelve
| Indicador | AS-IS (Manual) | TO-BE (Automatizado) |
|-----------|---------------|----------------------|
| Tiempo de ciclo | 1.5 – 2.2 horas | ~16 minutos efectivos |
| Reprocesos por error | 35% | ≈0% (idempotencia SHA-256) |
| Visibilidad de stock | Ninguna | Tiempo real (PostgreSQL) |
| Costo por pedido | S/ 12,546.11 | Drásticamente reducido |

### Dos flujos intercambiables por `FLOW_MODE`:
- **`rpa` (por defecto):** Flujo determinista orquestado, máquina de estados estricta con 3 fases BPMN.  
- **`agentic`:** AI Agent autónomo con LangChain + Google Gemini 1.5 Flash, con memoria de ventana por sesión telefónica.

---

## 📁 Estructura del Proyecto

```
farro-mendez-ipa/
├── .env.example              ← Variables de entorno (COPIA como .env)
├── .gitignore
├── README.md
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── pytest.ini
├── app/
│   ├── main.py               ← FastAPI + Webhook + Endpoints de Auditoría
│   ├── config.py             ← Settings Pydantic (DATABASE_URL, tokens, FLOW_MODE)
│   ├── database.py           ← Engine async SQLAlchemy 2.0 + sessionmaker
│   ├── models/               ← ORM (inventario, pedidos, conversaciones, ventas, fallidos, escalados)
│   ├── schemas/              ← Pydantic schemas para WhatsApp, pedidos y comprobantes
│   ├── services/             ← Capa de negocio (WhatsApp, Gemini, inventario, pedidos, ventas)
│   ├── flows/
│   │   ├── rpa_flow.py       ← Flujo Orquestado (determinista, fases consulta→confirmacion→pago)
│   │   └── agentic_flow.py   ← Flujo Agéntico (LangChain Tool Calling + Gemini)
│   ├── tools/                ← 6 tools para el AI Agent (BPMN TO-BE)
│   └── utils/                ← Logger + Constantes de negocio
├── alembic/
│   └── versions/
│       └── 0001_initial_schema.py  ← Migración inicial (6 tablas)
└── tests/
    ├── test_idempotencia.py
    ├── test_rpa_flow.py
    └── test_agentic_flow.py
```

---

## ✅ Requisitos Previos

- **Python 3.11+** → [python.org](https://www.python.org/downloads/)
- **PostgreSQL 14+** → [postgresql.org](https://www.postgresql.org/download/)
- **DBeaver** (gestión visual de la BD) → [dbeaver.io](https://dbeaver.io/download/)
- **ngrok** (para exponer el webhook de WhatsApp) → [ngrok.com](https://ngrok.com/download)

---

## ⚙️ Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/farro-mendez-ipa.git
cd farro-mendez-ipa
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
# Edita el archivo .env con tus credenciales reales
```

---

## 🗄️ Configuración de Base de Datos en DBeaver

1. Abre DBeaver y crea una nueva conexión PostgreSQL.
2. Configura:
   - **Host:** `localhost`
   - **Puerto:** `5432`
   - **Base de datos:** `farro_mendez`
   - **Usuario:** `postgres`
   - **Contraseña:** (la que pusiste en `.env`)
3. Crea la base de datos si no existe:
```sql
CREATE DATABASE farro_mendez;
```

---

## 🔄 Migraciones Alembic

```bash
# Aplicar la migración inicial (crea las 6 tablas)
alembic upgrade head

# Ver estado actual de migraciones
alembic current

# Revertir la última migración
alembic downgrade -1
```

---

## 🚀 Levantar el Servidor

```bash
# Modo desarrollo con auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Verificar que funciona
curl http://localhost:8000/health
```

La documentación interactiva Swagger UI estará disponible en:
📄 http://localhost:8000/docs

---

## 🌐 Exponer el Webhook con ngrok

WhatsApp Cloud API requiere una URL pública HTTPS para enviar los mensajes al sistema.

```bash
# En una terminal aparte
ngrok http 8000

# Copiar la URL HTTPS generada (ej: https://abc123.ngrok.io)
# Configurar en Meta Developers como:
# Callback URL: https://abc123.ngrok.io/webhook
# Verify Token: (el valor de WHATSAPP_VERIFY_TOKEN en tu .env)
```

---

## 🔀 Alternar entre Flujo RPA y Agéntico

Edita el archivo `.env`:

```env
# Para el Flujo RPA Orquestado (determinista, recomendado para producción)
FLOW_MODE=rpa

# Para el Flujo Agéntico (AI Agent con Gemini, mayor flexibilidad)
FLOW_MODE=agentic
```

Reinicia el servidor para aplicar el cambio.

### Diferencias clave entre ambos flujos:

| Característica | Flujo RPA | Flujo Agéntico |
|---|---|---|
| Tipo | Determinista / Orquestado | Autónomo / Razonamiento |
| Control de fase | Máquina de estados explícita | Memoria de ventana + tools |
| Modelo IA | Gemini (solo para extracción) | Gemini (razonamiento completo) |
| Fallback | No aplica | Cae en RPA si no hay API Key |
| Ideal para | Producción controlada | Escenarios complejos / conversacionales |

---

## 🧪 Ejecutar Pruebas

```bash
# Ejecutar todos los tests
pytest

# Con reporte detallado
pytest -v

# Solo tests de idempotencia
pytest tests/test_idempotencia.py -v

# Solo tests del flujo RPA
pytest tests/test_rpa_flow.py -v
```

---

## 🐳 Docker (Opcional)

```bash
# Levantar PostgreSQL + FastAPI en contenedores
docker-compose up -d

# Ver logs del servicio
docker-compose logs -f app

# Detener
docker-compose down
```

---

## 📡 Endpoints Disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Información del sistema |
| GET | `/health` | Estado de salud |
| GET | `/docs` | Swagger UI |
| GET | `/webhook` | Verificación Meta (hub.challenge) |
| POST | `/webhook` | Recepción de mensajes WhatsApp |
| POST | `/api/test/message` | **Simular mensaje sin WhatsApp real** |
| GET | `/api/inventario` | Listar catálogo de productos |
| GET | `/api/pedidos` | Listar pedidos |
| GET | `/api/ventas` | Listar ventas |
| GET | `/api/cola-fallidos` | Listar solicitudes fallidas |
| GET | `/api/casos-escalados` | Listar casos derivados a humano |

### Probar sin WhatsApp (endpoint de testing local):
```bash
# Simular una consulta de producto
curl -X POST "http://localhost:8000/api/test/message?telefono=51987654321&texto=Quiero+2+balanzas"

# Simular confirmación de compra
curl -X POST "http://localhost:8000/api/test/message?telefono=51987654321&texto=si"

# Simular envío de comprobante
curl -X POST "http://localhost:8000/api/test/message?telefono=51987654321&texto=OP987654321"
```

---

## 🔐 Credenciales Requeridas

Para que el sistema funcione completamente, necesitas obtener estas credenciales y agregarlas al archivo `.env`:

### 1. 🟢 WhatsApp Cloud API (Meta for Developers)
- **Variable:** `WHATSAPP_API_TOKEN`
- **Dónde obtener:** [Meta for Developers](https://developers.facebook.com/) → Crear App → Configurar WhatsApp → Obtener Token de acceso permanente
- **Variable:** `WHATSAPP_PHONE_NUMBER_ID`
- **Dónde obtener:** En la misma consola de Meta, panel de WhatsApp → Tu número de teléfono → ID del número
- **Variable:** `WHATSAPP_VERIFY_TOKEN`
- **Dónde obtener:** Lo defines tú (cualquier cadena secreta aleatoria). Se usa para verificar el webhook.

### 2. 🔵 Google Gemini API
- **Variable:** `GEMINI_API_KEY`
- **Dónde obtener:** [Google AI Studio](https://aistudio.google.com/app/apikey) → Crear API Key
- **Costo:** Plan gratuito incluye ~15 RPM con `gemini-1.5-flash`. Para producción se recomienda plan de pago.

### 3. 🟡 PostgreSQL
- **Variable:** `DATABASE_URL`
- **Formato:** `postgresql+asyncpg://usuario:password@host:5432/farro_mendez`
- **Local:** Instalar PostgreSQL y crear la base de datos `farro_mendez` con DBeaver.

---

## 🏗️ Arquitectura del Sistema

```
WhatsApp Cloud API
        │
        ▼
  POST /webhook (FastAPI)
        │
        ├── FLOW_MODE=rpa  ────────────► Flujo RPA Orquestado
        │                                (Máquina de Estados)
        │                                consulta → confirmacion → pago
        │
        └── FLOW_MODE=agentic ─────────► Flujo Agéntico
                                         (LangChain + Gemini)
                                         AI Agent con 6 tools + Window Memory
                                                │
                                         ┌──────┴──────┐
                                         │             │
                               Google Gemini      PostgreSQL
                               (Validación +      (Inventario +
                                Comprobante OCR)   Pedidos + Ventas)
```

---

## 📝 Notas de Desarrollo

- El sistema funciona **sin API keys reales** en modo desarrollo: WhatsApp se simula en logs y Gemini cae en un parser heurístico.
- La **idempotencia SHA-256** previene registrar el mismo pedido dos veces ante reenvíos del webhook.
- El **Flujo Agéntico** tiene un fallback automático al Flujo RPA si Gemini no está disponible.
- Los **endpoints de auditoría** (`/api/pedidos`, `/api/ventas`, etc.) son útiles para supervisión en DBeaver y dashboards.

---

*FARRO MENDEZ CORPORATION S.A.C. — Sistema IPA v1.0.0*
