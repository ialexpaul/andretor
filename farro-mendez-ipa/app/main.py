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
from app.schemas.contrato_entrada import validar_payload_contrato, ContratoEntrada
from app.services.inventario_service import seed_catalogo_si_vacio, listar_catalogo, consultar_producto
from app.services.pedido_service import registrar_pedido_con_idempotencia
from app.services.venta_service import registrar_venta_y_actualizar_stock
from app.services.cola_fallidos_service import registrar_en_cola_fallidos
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
# ENDPOINTS DE PROCESO Y CONTRATO DE ENTRADA (LABORATORIO 02)
# =====================================================================

@app.post("/api/proceso/solicitud", tags=["Proceso BPMN / Lab 2"])
async def procesar_solicitud_contrato(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Endpoint oficial para procesar solicitudes sujetas al Contrato de Datos de Entrada (Lab 2).

    Valida el contrato estricto:
    - Si falla la validación: responde HTTP 400 y registra en rpa_cola_fallidos con la carga original.
    - Si accion == 'consulta': verifica stock en tiempo real y retorna HTTP 200.
    - Si accion == 'compra': aplica validación de idempotencia SHA-256. Devuelve HTTP 201 (nuevo) o 200 (existente sin duplicar).
    - Si accion == 'pago': valida longitud >= 6 caracteres, registra venta y descuenta stock (HTTP 200).
    """
    try:
        payload = await request.json()
    except Exception:
        # Fallo de parseo JSON básico -> HTTP 400 y registrar en cola de fallidos
        await registrar_en_cola_fallidos(
            db=db,
            telefono="DESCONOCIDO",
            mensaje_original="Payload JSON malformado",
            motivo="JSON Decode Error",
            carga_original=None
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Payload JSON malformado", "codigo": 400}
        )

    # Validar contra el contrato de entrada
    es_valido, contrato, motivo_error = validar_payload_contrato(payload)

    if not es_valido or not contrato:
        # Registrar en cola de fallidos con la carga original íntegra
        telefono_cliente = str(payload.get("cliente") or payload.get("telefono") or "DESCONOCIDO")
        await registrar_en_cola_fallidos(
            db=db,
            telefono=telefono_cliente,
            mensaje_original=str(payload),
            motivo=f"Violación de Contrato: {motivo_error}",
            carga_original=payload
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "Solicitud no cumple el Contrato de Datos de Entrada",
                "motivo": motivo_error,
                "codigo": 400,
                "registrado_en_cola_fallidos": True
            }
        )

    # 1. ACCION: CONSULTA
    if contrato.accion == "consulta":
        prod = await consultar_producto(db, contrato.producto)
        if not prod or prod.stock <= 0:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "sin_stock",
                    "mensaje": f"No hay stock disponible para el producto '{contrato.producto}'",
                    "disponible": False
                }
            )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "disponible",
                "disponible": True,
                "producto_id": prod.product_id,
                "nombre": prod.nombre,
                "precio": float(prod.precio),
                "stock": prod.stock,
                "mensaje": f"Stock disponible: {prod.nombre} a S/ {prod.precio:.2f} ({prod.stock} unidades)"
            }
        )

    # 2. ACCION: COMPRA
    elif contrato.accion == "compra":
        if contrato.decision == "no":
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "compra_rechazada", "mensaje": "Compra cancelada por decisión del cliente"}
            )

        prod = await consultar_producto(db, contrato.producto)
        if not prod or prod.stock < contrato.cantidad:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "stock_insuficiente",
                    "mensaje": f"Stock insuficiente para {contrato.producto}. Solicitado: {contrato.cantidad}, Disponible: {prod.stock if prod else 0}"
                }
            )

        # Inserción con idempotencia estricta SHA-256
        pedido, fue_insertado = await registrar_pedido_con_idempotencia(
            db=db,
            telefono=contrato.cliente,
            producto_id=prod.product_id,
            producto_nombre=prod.nombre,
            cantidad=contrato.cantidad,
            precio_unitario=prod.precio,
            accion="compra"
        )

        status_http = status.HTTP_201_CREATED if fue_insertado else status.HTTP_200_OK
        return JSONResponse(
            status_code=status_http,
            content={
                "status": "registrado" if fue_insertado else "pedido_existente",
                "idempotente": not fue_insertado,
                "pedido_id": pedido.pedido_id,
                "monto_total": float(pedido.total),
                "idempotency_key": pedido.idempotency_key,
                "metodos_pago": ["Yape", "Plin", "Transferencia BCP"]
            }
        )

    # 3. ACCION: PAGO
    elif contrato.accion == "pago":
        comprobante_limpio = (contrato.comprobante or "").strip()
        if len(comprobante_limpio) < 6:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "comprobante_invalido",
                    "mensaje": "Comprobante inválido: debe contener al menos 6 caracteres alfanuméricos.",
                    "requiere_reintento": True
                }
            )

        try:
            # Buscar el pedido para obtener datos y monto
            q_ped = select(Pedido).where(Pedido.pedido_id == contrato.pedido_id)
            res_ped = await db.execute(q_ped)
            ped = res_ped.scalar_one_or_none()
            if not ped:
                await registrar_en_cola_fallidos(
                    db=db,
                    telefono="DESCONOCIDO",
                    mensaje_original=str(payload),
                    motivo=f"Pedido ID {contrato.pedido_id} inexistente",
                    carga_original=payload
                )
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": f"Pedido ID '{contrato.pedido_id}' no existe en el sistema", "codigo": 400}
                )

            venta, stock_nuevo = await registrar_venta_y_actualizar_stock(
                db=db,
                pedido_id=ped.pedido_id,
                telefono=ped.telefono,
                monto=ped.total,
                operacion=comprobante_limpio
            )

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "venta_confirmada",
                    "venta_id": venta.venta_id,
                    "pedido_id": ped.pedido_id,
                    "monto": float(venta.monto),
                    "stock_actualizado": stock_nuevo,
                    "mensaje": f"Pago confirmado y venta registrada exitosamente. ID Venta: {venta.venta_id}"
                }
            )
        except Exception as exc:
            logger.error(f"Error procesando pago de contrato: {exc}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": f"Error interno al concretar venta: {str(exc)}"}
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
