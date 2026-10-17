"""Servicio para registrar solicitudes en la cola de fallidos y casos escalados."""

import time
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.cola_fallidos import ColaFallidos
from app.models.caso_escalado import CasoEscalado
from app.utils.logger import logger


async def registrar_en_cola_fallidos(
    db: AsyncSession,
    telefono: str,
    mensaje_original: Optional[str],
    motivo: str,
    carga_original: Optional[Any] = None
) -> ColaFallidos:
    """Registra una solicitud no comprendida o errónea en cola_fallidos para auditoría."""
    registro = ColaFallidos(
        telefono=telefono,
        mensaje_original=mensaje_original,
        motivo=motivo,
        carga_original=carga_original,
        estado="pendiente"
    )
    db.add(registro)
    await db.commit()
    await db.refresh(registro)
    logger.warning(
        f"[COLA FALLIDOS] Registrado incidente id={registro.id} para tel={telefono}, motivo='{motivo}'"
    )
    return registro


async def registrar_caso_escalado(
    db: AsyncSession,
    telefono: str,
    pedido_id: Optional[str],
    motivo: str
) -> CasoEscalado:
    """Registra una derivación a asesor humano en la tabla casos_escalados."""
    timestamp_ms = int(time.time() * 1000)
    caso_id = f"CASO-{timestamp_ms}"

    caso = CasoEscalado(
        caso_id=caso_id,
        telefono=telefono,
        pedido_id=pedido_id or "N/A",
        motivo=motivo
    )
    db.add(caso)
    await db.commit()
    await db.refresh(caso)
    logger.warning(
        f"[CASO ESCALADO] Caso {caso_id} generado para tel={telefono}, motivo='{motivo}'"
    )
    return caso
