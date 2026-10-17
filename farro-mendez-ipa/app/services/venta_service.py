"""Servicio para registro de ventas, validación final y descuento de inventario."""

import time
from decimal import Decimal
from typing import Tuple, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pedido import Pedido
from app.models.venta import Venta
from app.models.inventario import Inventario
from app.utils.logger import logger


async def registrar_venta_y_actualizar_stock(
    db: AsyncSession,
    pedido_id: str,
    telefono: str,
    monto: Decimal,
    operacion: str
) -> Tuple[Venta, int]:
    """Registra la venta atómica, actualiza el estado del pedido a 'Pagado' y descuenta stock.

    Args:
        db: Sesión de base de datos asíncrona.
        pedido_id: Identificador del pedido.
        telefono: Teléfono del cliente.
        monto: Monto verificado del comprobante.
        operacion: Código de operación bancaria o de billetera digital.

    Returns:
        Tuple[Venta, int]: (Instancia de la venta generada, Nuevo stock del producto).

    Raises:
        ValueError: Si el pedido no existe o ya fue procesado.
    """
    # 1. Buscar y bloquear el pedido
    query_ped = select(Pedido).where(Pedido.pedido_id == pedido_id)
    res_ped = await db.execute(query_ped)
    pedido = res_ped.scalar_one_or_none()

    if not pedido:
        raise ValueError(f"El pedido #{pedido_id} no existe en la base de datos.")

    # 2. Descontar stock en inventario
    query_inv = select(Inventario).where(Inventario.codigo == pedido.producto_id)
    res_inv = await db.execute(query_inv)
    producto = res_inv.scalar_one_or_none()

    nuevo_stock = 0
    if producto:
        producto.stock = max(0, producto.stock - pedido.cantidad)
        nuevo_stock = producto.stock

    # 3. Actualizar estado del pedido a Pagado
    pedido.estado = "Pagado"

    # 4. Registrar la venta
    timestamp_ms = int(time.time() * 1000)
    venta_id = f"VEN-{timestamp_ms}"

    venta = Venta(
        venta_id=venta_id,
        pedido_id=pedido.pedido_id,
        telefono=telefono,
        monto=monto,
        operacion=operacion,
        estado="Pagado"
    )
    db.add(venta)

    # Commit atómico de toda la transacción
    await db.commit()
    await db.refresh(venta)

    logger.info(
        f"Venta registrada exitosamente: {venta_id} para Pedido {pedido_id}. "
        f"Nuevo stock de {pedido.producto_id}: {nuevo_stock}"
    )

    return venta, nuevo_stock
