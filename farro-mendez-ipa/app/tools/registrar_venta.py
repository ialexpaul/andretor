"""Tool: registrar_venta para el Agente LangChain."""

import json
import asyncio
from decimal import Decimal
from langchain_core.tools import tool
from app.database import async_session_factory
from app.services.venta_service import registrar_venta_y_actualizar_stock
from app.utils.logger import logger


async def _registrar_venta_async(
    pedido_id: str,
    cliente: str,
    monto: float,
    operacion: str
) -> str:
    """Función asíncrona interna para asentar la venta y descontar stock."""
    async with async_session_factory() as db:
        try:
            venta, nuevo_stock = await registrar_venta_y_actualizar_stock(
                db=db,
                pedido_id=pedido_id,
                telefono=cliente,
                monto=Decimal(str(monto)),
                operacion=operacion
            )
            return json.dumps({
                "venta_id": venta.venta_id,
                "pedido_id": venta.pedido_id,
                "cliente": venta.telefono,
                "monto": float(venta.monto),
                "operacion": venta.operacion,
                "estado": venta.estado,
                "nuevo_stock": nuevo_stock,
                "exito": True
            }, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({
                "exito": False,
                "error": str(exc)
            }, ensure_ascii=False)


@tool
def registrar_venta(
    pedido_id: str,
    cliente: str,
    monto: float,
    operacion: str
) -> str:
    """Inserta el registro definitivo de la venta en la base de datos Ventas cuando el comprobante es válido.

    Actualiza el estado del pedido a 'Pagado' y descuenta automáticamente el stock en inventario.
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
                    lambda: asyncio.run(_registrar_venta_async(pedido_id, cliente, monto, operacion))
                ).result()
        else:
            return asyncio.run(_registrar_venta_async(pedido_id, cliente, monto, operacion))
    except Exception as exc:
        logger.error(f"Error en tool registrar_venta: {exc}")
        return json.dumps({"exito": False, "error": str(exc)})
