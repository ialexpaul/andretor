"""Tool: derivar_a_humano para el Agente LangChain."""

import json
import asyncio
from typing import Optional
from langchain_core.tools import tool
from app.database import async_session_factory
from app.services.cola_fallidos_service import registrar_caso_escalado
from app.utils.logger import logger


async def _derivar_a_humano_async(
    cliente: str,
    pedido_id: Optional[str],
    motivo: str
) -> str:
    """Función asíncrona interna para asentar el caso escalado."""
    async with async_session_factory() as db:
        caso = await registrar_caso_escalado(
            db=db,
            telefono=cliente,
            pedido_id=pedido_id if pedido_id and pedido_id != "N/A" else None,
            motivo=motivo
        )
        return json.dumps({
            "caso_id": caso.caso_id,
            "cliente": caso.telefono,
            "pedido_id": caso.pedido_id,
            "motivo": caso.motivo,
            "escalado": True
        }, ensure_ascii=False)


@tool
def derivar_a_humano(
    cliente: str,
    motivo: str,
    pedido_id: str = "N/A"
) -> str:
    """Escala la atención a un asesor humano registrando el caso en la base de datos Casos_Escalados.

    Úsala cuando el comprobante falla dos veces consecutivas o ante solicitudes no soportadas.
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
                    lambda: asyncio.run(_derivar_a_humano_async(cliente, pedido_id, motivo))
                ).result()
        else:
            return asyncio.run(_derivar_a_humano_async(cliente, pedido_id, motivo))
    except Exception as exc:
        logger.error(f"Error en tool derivar_a_humano: {exc}")
        return json.dumps({"escalado": False, "error": str(exc)})
