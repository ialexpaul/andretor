"""Tool: consultar_stock_y_precio para el Agente LangChain."""

import json
import asyncio
from typing import Optional
from langchain_core.tools import tool
from sqlalchemy import select, or_
from app.database import async_session_factory
from app.models.inventario import Inventario
from app.utils.logger import logger


async def _consultar_stock_async(termino: Optional[str] = None) -> str:
    """Función asíncrona interna para consultar inventario."""
    async with async_session_factory() as db:
        if termino and termino.strip():
            term = termino.strip()
            query = select(Inventario).where(
                or_(
                    Inventario.codigo.ilike(term),
                    Inventario.nombre.ilike(f"%{term}%")
                )
            ).order_by(Inventario.stock.desc())
        else:
            query = select(Inventario).order_by(Inventario.codigo)

        res = await db.execute(query)
        items = res.scalars().all()

        if not items:
            return json.dumps({
                "mensaje": f"No se encontraron productos coincidentes con '{termino}'",
                "productos": []
            }, ensure_ascii=False)

        catalogo = [
            {
                "product_id": item.codigo,
                "nombre": item.nombre,
                "precio": float(item.precio),
                "stock": item.stock
            }
            for item in items
        ]
        return json.dumps({"productos": catalogo}, ensure_ascii=False)


@tool
def consultar_stock_y_precio(producto: str = "") -> str:
    """Consulta la base de datos de productos e inventario.

    Devuelve los productos con product_id, nombre, precio y stock.
    Úsala para verificar disponibilidad y precio de lo que pide el cliente.
    """
    try:
        # Ejecuta de forma segura en loop sincrónico o existente
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(lambda: asyncio.run(_consultar_stock_async(producto))).result()
        else:
            return asyncio.run(_consultar_stock_async(producto))
    except Exception as exc:
        logger.error(f"Error en tool consultar_stock_y_precio: {exc}")
        return json.dumps({"error": str(exc), "productos": []})
