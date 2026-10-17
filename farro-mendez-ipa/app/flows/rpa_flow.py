"""Flujo RPA (Orquestado y Determinista) para FARRO MENDEZ CORPORATION S.A.C.

Implementa la máquina de estados BPMN TO-BE con control estricto de transiciones:
1. Fase 'consulta': Validación de solicitud e inspección de inventario.
2. Fase 'confirmacion': Interpretación de decisión y registro con clave de idempotencia SHA-256.
3. Fase 'pago': Descarga, análisis OCR con Gemini, validación de comprobante y cierre de venta o escalado.
"""

from decimal import Decimal
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversacion import Conversacion
from app.schemas.whatsapp import MensajeWhatsAppNormalizado
from app.services.inventario_service import consultar_producto
from app.services.pedido_service import registrar_pedido_con_idempotencia
from app.services.venta_service import registrar_venta_y_actualizar_stock
from app.services.cola_fallidos_service import registrar_en_cola_fallidos, registrar_caso_escalado
from app.services.whatsapp_service import enviar_mensaje, obtener_url_media, descargar_media
from app.services.gemini_service import validar_solicitud, analizar_comprobante
from app.utils.constants import (
    ESTADO_CONSULTA,
    ESTADO_CONFIRMACION,
    ESTADO_PAGO,
    ESTADO_FINALIZADO,
    ESTADO_DERIVADO,
    MOTIVO_SOLICITUD_INVALIDA,
    MOTIVO_ESCALADO_2_INTENTOS,
    MSG_NO_ENTENDIDO,
    MSG_SIN_STOCK,
    MSG_COMPRA_RECHAZADA,
    MSG_SOLICITAR_NUEVO_COMPROBANTE,
    MSG_DERIVADO_HUMANO,
    TEMPLATE_DISPONIBILIDAD,
    TEMPLATE_METODOS_PAGO,
    TEMPLATE_CONFIRMACION_VENTA,
)
from app.utils.logger import logger


async def procesar_flujo_rpa(
    msg: MensajeWhatsAppNormalizado,
    db: AsyncSession
) -> Dict[str, Any]:
    """Orquestador principal del flujo RPA.

    Args:
        msg: Mensaje normalizado recibido del webhook.
        db: Sesión asíncrona de base de datos.

    Returns:
        Dict con los resultados de la ejecución y estado alcanzado.
    """
    telefono = msg.telefono
    texto = msg.texto.strip()
    tipo = msg.tipo

    logger.info(f"[RPA FLOW] Procesando mensaje de {telefono} (tipo: {tipo})")

    # 1. Obtener o inicializar conversación
    query_conv = select(Conversacion).where(Conversacion.telefono == telefono)
    res_conv = await db.execute(query_conv)
    conv = res_conv.scalar_one_or_none()

    if not conv:
        conv = Conversacion(telefono=telefono, estado=ESTADO_CONSULTA, intentos=0)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    # 2. Determinar fase de negocio
    fase = ESTADO_CONSULTA
    if conv.estado == ESTADO_PAGO or tipo in ("image", "document"):
        fase = "pago"
    elif conv.estado == ESTADO_CONFIRMACION:
        fase = "confirmacion"
    else:
        fase = "consulta"

    logger.info(f"[RPA FLOW] Cliente {telefono} en fase '{fase}' (estado BD: {conv.estado})")

    # ============================================================
    # FASE 1: CONSULTA
    # ============================================================
    if fase == "consulta":
        # Validar solicitud con Gemini
        val_res = await validar_solicitud(texto)

        if not val_res.es_valida:
            logger.warning(f"[RPA FLOW] Solicitud no válida de {telefono}: {val_res.motivo}")
            await registrar_en_cola_fallidos(
                db=db,
                telefono=telefono,
                mensaje_original=texto,
                motivo=MOTIVO_SOLICITUD_INVALIDA,
                carga_original=msg.raw_payload or {"texto": texto}
            )
            await enviar_mensaje(telefono=telefono, texto=MSG_NO_ENTENDIDO, phone_number_id=msg.phone_number_id)
            return {"fase": "consulta", "resultado": "no_valida", "motivo": val_res.motivo}

        # Consultar inventario
        producto = await consultar_producto(db=db, termino=val_res.producto or texto)

        if not producto or producto.stock <= 0:
            logger.info(f"[RPA FLOW] Producto sin stock para solicitud '{val_res.producto}' de {telefono}")
            conv.estado = ESTADO_FINALIZADO
            await db.commit()
            await enviar_mensaje(telefono=telefono, texto=MSG_SIN_STOCK, phone_number_id=msg.phone_number_id)
            return {"fase": "consulta", "resultado": "sin_stock", "producto": val_res.producto}

        # Stock disponible -> Transicionar a confirmación
        conv.estado = ESTADO_CONFIRMACION
        conv.producto_id = producto.codigo
        conv.producto_nombre = producto.nombre
        conv.cantidad = val_res.cantidad
        conv.precio = producto.precio
        conv.intentos = 0
        await db.commit()

        mensaje_resp = TEMPLATE_DISPONIBILIDAD.format(
            nombre=producto.nombre,
            precio=float(producto.precio),
            stock=producto.stock
        )
        await enviar_mensaje(telefono=telefono, texto=mensaje_resp, phone_number_id=msg.phone_number_id)
        return {
            "fase": "consulta",
            "resultado": "disponible",
            "producto": producto.nombre,
            "precio": float(producto.precio),
            "stock": producto.stock
        }

    # ============================================================
    # FASE 2: CONFIRMACIÓN
    # ============================================================
    elif fase == "confirmacion":
        t_low = texto.lower()
        no_words = ["no", "cancelar", "luego", "despues", "después", "ya no", "mejor no"]
        si_words = ["si", "sí", "claro", "ok", "dale", "quiero", "confirmo", "comprar", "acepto", "listo"]

        is_no = any(t_low == w or t_low.startswith(w) for w in no_words)
        is_si = any(w in t_low for w in si_words)

        if is_no or (not is_si and "no" in t_low):
            # Cliente rechaza la compra
            conv.estado = ESTADO_FINALIZADO
            await db.commit()
            await enviar_mensaje(telefono=telefono, texto=MSG_COMPRA_RECHAZADA, phone_number_id=msg.phone_number_id)
            return {"fase": "confirmacion", "decision": "rechazada"}

        # Cliente confirma compra (SI)
        producto_id = conv.producto_id or "P001"
        producto_nombre = conv.producto_nombre or "Producto"
        cantidad = conv.cantidad or 1
        precio = conv.precio or Decimal("0.00")

        # Registrar pedido con idempotencia (SHA-256)
        pedido, fue_insertado = await registrar_pedido_con_idempotencia(
            db=db,
            telefono=telefono,
            producto_id=producto_id,
            producto_nombre=producto_nombre,
            cantidad=cantidad,
            precio_unitario=Decimal(str(precio)),
            accion="compra"
        )

        conv.estado = ESTADO_PAGO
        conv.pedido_id = pedido.pedido_id
        conv.intentos = 0
        await db.commit()

        mensaje_pago = TEMPLATE_METODOS_PAGO.format(
            pedido_id=pedido.pedido_id,
            estado=pedido.estado
        )
        await enviar_mensaje(telefono=telefono, texto=mensaje_pago, phone_number_id=msg.phone_number_id)
        return {
            "fase": "confirmacion",
            "decision": "aceptada",
            "pedido_id": pedido.pedido_id,
            "idempotency_key": pedido.idempotency_key
        }

    # ============================================================
    # FASE 3: PAGO Y VALIDACIÓN DE COMPROBANTE
    # ============================================================
    elif fase == "pago":
        binary_data = b""

        # 1. Descarga de imagen o documento si vino por WhatsApp
        if msg.media_id:
            media_url = await obtener_url_media(msg.media_id)
            if media_url:
                try:
                    binary_data = await descargar_media(media_url)
                except Exception as exc:
                    logger.error(f"Fallo al descargar comprobante: {exc}")

        # 2. Análisis del comprobante con Gemini Vision
        if binary_data:
            analisis = await analizar_comprobante(binary_data)
            operacion = (analisis.operacion or "").strip().replace(" ", "")
            monto = analisis.monto or conv.precio or Decimal("0.00")
        else:
            # Si el cliente escribió el texto de la operación en el chat
            operacion = texto.replace(" ", "")
            monto = conv.precio or Decimal("0.00")

        # 3. Regla BPMN: Operación >= 6 caracteres y existencia de pedido_id
        comprobante_valido = len(operacion) >= 6 and bool(conv.pedido_id)

        if comprobante_valido:
            # Transacción definitiva: Registrar Venta y Descontar Stock
            try:
                venta, stock_nuevo = await registrar_venta_y_actualizar_stock(
                    db=db,
                    pedido_id=conv.pedido_id,
                    telefono=telefono,
                    monto=monto,
                    operacion=operacion
                )
                conv.estado = ESTADO_FINALIZADO
                await db.commit()

                mensaje_exito = TEMPLATE_CONFIRMACION_VENTA.format(
                    pedido_id=conv.pedido_id,
                    venta_id=venta.venta_id,
                    monto=float(monto)
                )
                await enviar_mensaje(telefono=telefono, texto=mensaje_exito, phone_number_id=msg.phone_number_id)
                return {
                    "fase": "pago",
                    "resultado": "valido",
                    "venta_id": venta.venta_id,
                    "stock_nuevo": stock_nuevo
                }
            except Exception as exc:
                logger.error(f"Error registrando venta para pedido {conv.pedido_id}: {exc}")

        # Comprobante inválido -> Incrementar intentos
        conv.intentos += 1
        await db.commit()

        if conv.intentos <= 2:
            # Reintentos disponibles: solicitar nuevo comprobante
            await enviar_mensaje(telefono=telefono, texto=MSG_SOLICITAR_NUEVO_COMPROBANTE, phone_number_id=msg.phone_number_id)
            return {"fase": "pago", "resultado": "invalido", "intentos": conv.intentos}
        else:
            # Falla consecutiva > 2: Derivar a humano
            caso = await registrar_caso_escalado(
                db=db,
                telefono=telefono,
                pedido_id=conv.pedido_id,
                motivo=MOTIVO_ESCALADO_2_INTENTOS
            )
            conv.estado = ESTADO_DERIVADO
            await db.commit()

            await enviar_mensaje(telefono=telefono, texto=MSG_DERIVADO_HUMANO, phone_number_id=msg.phone_number_id)
            return {
                "fase": "pago",
                "resultado": "escalado_a_humano",
                "caso_id": caso.caso_id,
                "motivo": caso.motivo
            }

    return {"fase": fase, "estado": "no_determinado"}
