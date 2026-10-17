"""Servicio para registro de pedidos con garantía de idempotencia."""

import time
from decimal import Decimal
from typing import Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.models.pedido import Pedido
from app.services.idempotencia import generar_clave_idempotencia
from app.utils.logger import logger


async def registrar_pedido_con_idempotencia(
    db: AsyncSession,
    telefono: str,
    producto_id: str,
    producto_nombre: str,
    cantidad: int,
    precio_unitario: Decimal,
    accion: str = "compra"
) -> Tuple[Pedido, bool]:
    """Registra un nuevo pedido asegurando idempotencia estricta mediante SHA-256.

    Si un pedido con la misma clave de idempotencia ya existe, no se duplica
    y se devuelve el pedido existente (ON CONFLICT DO NOTHING).

    Returns:
        Tuple[Pedido, bool]: (Instancia de Pedido, True si fue insertado de novo o False si ya existía).
    """
    idempotency_key = generar_clave_idempotencia(
        accion=accion,
        producto=producto_id,
        cliente=telefono,
        cantidad=cantidad
    )

    total = Decimal(str(cantidad)) * Decimal(str(precio_unitario))
    timestamp_ms = int(time.time() * 1000)
    nuevo_pedido_id = f"PED-{timestamp_ms}"

    try:
        # Intento de inserción con cláusula ON CONFLICT DO NOTHING de PostgreSQL
        stmt = (
            pg_insert(Pedido)
            .values(
                pedido_id=nuevo_pedido_id,
                telefono=telefono,
                producto_id=producto_id,
                producto_nombre=producto_nombre,
                cantidad=cantidad,
                precio_unitario=precio_unitario,
                total=total,
                estado="Pendiente de pago",
                idempotency_key=idempotency_key,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
        )
        await db.execute(stmt)
        await db.commit()
    except Exception as exc:
        # Fallback para dialectos genéricos (como SQLite en tests de integración)
        await db.rollback()
        logger.warning(f"Nota en inserción directa: {exc}. Verificando existencia de clave.")

    # Recuperar el registro garantizado por idempotency_key
    query = select(Pedido).where(Pedido.idempotency_key == idempotency_key)
    res = await db.execute(query)
    pedido_existente = res.scalar_one_or_none()

    if pedido_existente:
        fue_insertado = (pedido_existente.pedido_id == nuevo_pedido_id)
        if not fue_insertado:
            logger.info(
                f"[IDEMPOTENCIA ACTIVADA] Solicitud duplicada ignorada. Clave={idempotency_key}, "
                f"Pedido original={pedido_existente.pedido_id}"
            )
        return pedido_existente, fue_insertado

    # Si no existía previamente (por ejemplo en SQLite de tests), insertarlo normalmente
    pedido_nuevo = Pedido(
        pedido_id=nuevo_pedido_id,
        telefono=telefono,
        producto_id=producto_id,
        producto_nombre=producto_nombre,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        total=total,
        estado="Pendiente de pago",
        idempotency_key=idempotency_key,
    )
    db.add(pedido_nuevo)
    await db.commit()
    await db.refresh(pedido_nuevo)
    return pedido_nuevo, True
