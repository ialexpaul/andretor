"""Servicio para consultas y administración de inventario."""

from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.inventario import Inventario
from app.utils.logger import logger


async def consultar_producto(db: AsyncSession, termino: str) -> Optional[Inventario]:
    """Busca un producto por código exacto o coincidencia parcial en nombre.

    Estrategia multicapa:
    1. Coincidencia exacta de código.
    2. El término completo aparece en el nombre (ilike %termino%).
    3. Cada palabra del término aparece en el nombre (AND lógico).
    Ordena por mayor stock disponible para priorizar disponibilidad.
    """
    if not termino:
        return None

    term_clean = termino.strip()

    # --- Intento 1: Coincidencia exacta de código o nombre completo ---
    query = (
        select(Inventario)
        .where(
            or_(
                Inventario.codigo.ilike(term_clean),
                Inventario.nombre.ilike(f"%{term_clean}%"),
            )
        )
        .order_by(Inventario.stock.desc())
        .limit(1)
    )
    result = await db.execute(query)
    found = result.scalar_one_or_none()
    if found:
        return found

    # --- Intento 2: Tokenizar por palabras (cada palabra debe aparecer en el nombre) ---
    tokens = [t for t in term_clean.split() if len(t) >= 3]
    if tokens:
        conditions = [Inventario.nombre.ilike(f"%{token}%") for token in tokens]
        from sqlalchemy import and_
        query2 = (
            select(Inventario)
            .where(and_(*conditions))
            .order_by(Inventario.stock.desc())
            .limit(1)
        )
        result2 = await db.execute(query2)
        found2 = result2.scalar_one_or_none()
        if found2:
            return found2

    # --- Intento 3: Primera palabra significativa (fallback) ---
    first_token = tokens[0] if tokens else term_clean
    query3 = (
        select(Inventario)
        .where(Inventario.nombre.ilike(f"%{first_token}%"))
        .order_by(Inventario.stock.desc())
        .limit(1)
    )
    result3 = await db.execute(query3)
    return result3.scalar_one_or_none()


async def listar_catalogo(db: AsyncSession) -> List[Inventario]:
    """Retorna la lista completa del catálogo de productos e inventario."""
    result = await db.execute(select(Inventario).order_by(Inventario.codigo))
    return list(result.scalars().all())


async def seed_catalogo_si_vacio(db: AsyncSession) -> None:
    """Inserta productos iniciales en la base de datos si la tabla inventario está vacía."""
    existentes = await db.execute(select(Inventario).limit(1))
    if existentes.scalar_one_or_none() is not None:
        return

    logger.info("Inicializando catálogo base de FARRO MENDEZ CORPORATION S.A.C...")
    productos_base = [
        Inventario(codigo="P001", nombre="Balanza Analítica Digital", precio=150.00, stock=15),
        Inventario(codigo="P002", nombre="Termómetro Infrarrojo Digital", precio=85.00, stock=20),
        Inventario(codigo="P003", nombre="Pack Mascarillas KN95 x50", precio=35.00, stock=50),
        Inventario(codigo="P004", nombre="Alcohol en Gel 1L Antibacterial", precio=18.50, stock=0),  # Sin stock de prueba
    ]
    db.add_all(productos_base)
    await db.commit()
    logger.info("Catálogo inicial sembrado con éxito.")
