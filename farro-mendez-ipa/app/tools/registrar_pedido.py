"""Tool: registrar_pedido para el Agente LangChain."""

import json
import asyncio
from decimal import Decimal
from langchain_core.tools import tool
from app.database import async_session_factory
from app.services.pedido_service import registrar_pedido_con_idempotencia
from app.utils.logger import logger


async def _registrar_pedido_async(
    cliente: str,
    product_id: str,
    producto_nombre: str,
    cantidad: int,
    precio_unitario: float
) -> str:
    """Función asíncrona interna para insertar el pedido con idempotencia."""
    async with async_session_factory() as db:
        pedido, fue_creado = await registrar_pedido_con_idempotencia(
            db=db,
            telefono=cliente,
            producto_id=product_id,
            producto_nombre=producto_nombre,
            cantidad=int(cantidad),
            precio_unitario=Decimal(str(precio_unitario)),
            accion="compra"
        )
        return json.dumps({
            "pedido_id": pedido.pedido_id,
            "cliente": pedido.telefono,
            "product_id": pedido.producto_id,
            "producto_nombre": pedido.producto_nombre,
            "cantidad": pedido.cantidad,
            "precio_unitario": float(pedido.precio_unitario),
            "total": float(pedido.total),
            "estado": pedido.estado,
            "idempotency_key": pedido.idempotency_key,
            "nuevo_registro": fue_creado
        }, ensure_ascii=False)


@tool
def registrar_pedido(
    cliente: str,
    product_id: str,
    producto_nombre: str,
    cantidad: int,
    precio_unitario: float
) -> str:
    """Inserta una nueva orden en la base de datos de Pedidos con idempotencia cuando el cliente confirma la compra.

    Genera un pedido_id único (formato PED-<timestamp>) y usa estado 'Pendiente de pago'.
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(
                    lambda: asyncio.run(
                        _registrar_pedido_async(cliente, product_id, producto_nombre, cantidad, precio_unitario)
                    )
                ).result()
        else:
            return asyncio.run(
                _registrar_pedido_async(cliente, product_id, producto_nombre, cantidad, precio_unitario)
            )
    except Exception as exc:
        logger.error(f"Error en tool registrar_pedido: {exc}")
        return json.dumps({"error": str(exc)})
