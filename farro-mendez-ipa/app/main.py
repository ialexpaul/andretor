"""Aplicación Principal FastAPI y Webhooks de WhatsApp.

FARRO MENDEZ CORPORATION S.A.C. - Automatización Inteligente de Procesos (IPA)
Permite alternar de forma transparente entre el Flujo RPA y el Flujo Agéntico mediante FLOW_MODE.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Response, Query, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db, async_session_factory
from app.schemas.whatsapp import extraer_mensaje_normalizado, MensajeWhatsAppNormalizado
from app.services.inventario_service import seed_catalogo_si_vacio, listar_catalogo
from app.flows.rpa_flow import procesar_flujo_rpa
from app.flows.agentic_flow import procesar_flujo_agentico
from app.models.pedido import Pedido
from app.models.venta import Venta
from app.models.cola_fallidos import ColaFallidos
from app.models.caso_escalado import CasoEscalado
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ciclo de vida de la aplicación: inicialización y sembrado de datos."""
    logger.info("Iniciando servicio IPA de FARRO MENDEZ CORPORATION S.A.C...")
    logger.info(f"Modo de flujo configurado: [{settings.FLOW_MODE.upper()}]")
    try:
        async with async_session_factory() as session:
            await seed_catalogo_si_vacio(session)
    except Exception as exc:
        logger.warning(f"Aviso durante la conexión inicial a la base de datos: {exc}")
    yield
    logger.info("Deteniendo servicio IPA.")


app = FastAPI(
    title="FARRO MENDEZ CORPORATION S.A.C. - IPA Platform",
    description="Sistema de Automatización Inteligente de Pedidos por WhatsApp (RPA + AI Agent)",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["General"])
async def root():
    """Ruta raíz informativa."""
    return {
        "empresa": "FARRO MENDEZ CORPORATION S.A.C.",
        "sistema": "Automatización Inteligente de Procesos (IPA)",
        "estado": "operativo",
        "flow_mode": settings.FLOW_MODE,
        "docs_url": "/docs"
    }


@app.get("/health", tags=["General"])
async def health_check():
    """Verificación de salud del sistema."""
    return {
        "status": "healthy",
        "flow_mode": settings.FLOW_MODE,
        "gemini_model": settings.GEMINI_MODEL
    }


# =====================================================================
# WEBHOOK WHATSAPP CLOUD API
# =====================================================================

@app.get("/webhook", tags=["WhatsApp Webhook"])
async def verificar_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Verificación GET requerida por Meta for Developers para validar el Webhook."""
    logger.info(f"Petición de verificación de webhook recibida: mode={hub_mode}")

    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verificado exitosamente por token de Meta.")
        return PlainTextResponse(content=hub_challenge, status_code=status.HTTP_200_OK)

    logger.warning("Fallo en la verificación del Webhook: token inválido o modo no soportado.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de verificación inválido")


@app.post("/webhook", tags=["WhatsApp Webhook"])
async def recibir_mensaje_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Recepción POST de mensajes y eventos enviados por WhatsApp Cloud API."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload JSON inválido")

    logger.debug(f"Payload recibido del webhook: {payload}")

    # Extraer y normalizar mensaje
    msg = extraer_mensaje_normalizado(payload)
    if not msg or not msg.telefono:
        # Respuestas o confirmaciones de lectura que no requieren procesamiento de compra
        return JSONResponse(content={"status": "ignored", "reason": "no_actionable_message"}, status_code=status.HTTP_200_OK)

    logger.info(f"Mensaje entrante de {msg.telefono}: '{msg.texto}' (tipo: {msg.tipo})")

    # Enrutamiento según FLOW_MODE
    modo = settings.FLOW_MODE.lower()
    if modo == "agentic":
        logger.info("[ROUTER] Enrutando al Flujo Agéntico (LangChain + Gemini)")
        resultado = await procesar_flujo_agentico(msg)
    else:
        logger.info("[ROUTER] Enrutando al Flujo RPA Orquestado (BPMN Determinista)")
        resultado = await procesar_flujo_rpa(msg, db)

    return JSONResponse(
        content={"status": "processed", "mode": modo, "result": resultado},
        status_code=status.HTTP_200_OK
    )


# =====================================================================
# ENDPOINTS DE PRUEBA Y AUDITORÍA
# =====================================================================

@app.post("/api/test/message", tags=["Testing Local"])
async def simular_mensaje_cliente(
    telefono: str = Query("51987654321", description="Número de teléfono simulado"),
    texto: str = Query("Quiero 2 balanzas analiticas", description="Texto del mensaje"),
    tipo: str = Query("text", description="text, image o document"),
    media_id: str = Query(None, description="media_id de comprobante simulado"),
    db: AsyncSession = Depends(get_db)
):
    """Permite probar ambos flujos directamente sin necesidad de tener ngrok ni Meta configurados."""
    msg = MensajeWhatsAppNormalizado(
        telefono=telefono,
        texto=texto,
        tipo=tipo,
        media_id=media_id,
        message_id="TEST-MSG-001",
        phone_number_id="TEST-PHONE-ID"
    )

    modo = settings.FLOW_MODE.lower()
    if modo == "agentic":
        res = await procesar_flujo_agentico(msg)
    else:
        res = await procesar_flujo_rpa(msg, db)

    return {"modo": modo, "mensaje_enviado": texto, "resultado": res}


@app.get("/api/inventario", tags=["Auditoría y Gestión"])
async def obtener_inventario(db: AsyncSession = Depends(get_db)):
    """Lista los productos en inventario y sus existencias."""
    return await listar_catalogo(db)


@app.get("/api/pedidos", tags=["Auditoría y Gestión"])
async def obtener_pedidos(db: AsyncSession = Depends(get_db)):
    """Lista todos los pedidos registrados."""
    res = await db.execute(select(Pedido).order_by(Pedido.creado_en.desc()).limit(50))
    return res.scalars().all()


@app.get("/api/ventas", tags=["Auditoría y Gestión"])
async def obtener_ventas(db: AsyncSession = Depends(get_db)):
    """Lista todas las ventas concretadas."""
    res = await db.execute(select(Venta).order_by(Venta.creado_en.desc()).limit(50))
    return res.scalars().all()


@app.get("/api/cola-fallidos", tags=["Auditoría y Gestión"])
async def obtener_cola_fallidos(db: AsyncSession = Depends(get_db)):
    """Lista las incidencias registradas en la cola de fallidos."""
    res = await db.execute(select(ColaFallidos).order_by(ColaFallidos.creado_en.desc()).limit(50))
    return res.scalars().all()


@app.get("/api/casos-escalados", tags=["Auditoría y Gestión"])
async def obtener_casos_escalados(db: AsyncSession = Depends(get_db)):
    """Lista los casos derivados a asesores humanos."""
    res = await db.execute(select(CasoEscalado).order_by(CasoEscalado.creado_en.desc()).limit(50))
    return res.scalars().all()
