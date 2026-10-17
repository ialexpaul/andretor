"""Modelo de datos para Cola de Fallidos (Auditoría y Revisión)."""

from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Text, Integer, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ColaFallidos(Base):
    """Tabla cola_fallidos para registrar solicitudes no entendibles o incidentes."""

    __tablename__ = "cola_fallidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    mensaje_original: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    motivo: Mapped[str] = mapped_column(String(100), nullable=False)
    carga_original: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ColaFallidos(id={self.id}, tel='{self.telefono}', motivo='{self.motivo}', estado='{self.estado}')>"
