"""Modelo de datos para Casos Escalados a Asesor Humano."""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CasoEscalado(Base):
    """Tabla casos_escalados para derivaciones que requieren intervención manual."""

    __tablename__ = "casos_escalados"

    caso_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    pedido_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    motivo: Mapped[str] = mapped_column(String(200), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<CasoEscalado(id='{self.caso_id}', tel='{self.telefono}', pedido='{self.pedido_id}', motivo='{self.motivo}')>"
