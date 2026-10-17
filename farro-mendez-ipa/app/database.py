"""Configuración de la Base de Datos PostgreSQL con SQLAlchemy 2.0 (Async).

Gestiona el pool de conexiones asíncronas y las sesiones de base de datos.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.config import settings
from app.utils.logger import logger


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM del sistema."""
    pass


# Motor asíncrono para PostgreSQL (asyncpg)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# Fábrica de sesiones asíncronas
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Generador de dependencias para inyectar sesiones en FastAPI o servicios."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as exc:
            await session.rollback()
            logger.error(f"Error en sesión de base de datos, rollback ejecutado: {exc}")
            raise
        finally:
            await session.close()
