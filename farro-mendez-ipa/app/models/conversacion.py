"""Modelo de datos para el Estado de Conversaciones."""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Numeric, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Conversacion(Base):
    """Tabla conversaciones para control de estados del cliente en el flujo BPMN."""

    __tablename__ = "conversaciones"

    telefono: Mapped[str] = mapped_column(String(30), primary_key=True, index=True)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="consulta")
    producto_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("inventario.codigo", ondelete="SET NULL"), nullable=True
    )
    producto_nombre: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cantidad: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    precio: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    pedido_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("pedidos.pedido_id", ondelete="SET NULL"), nullable=True
    )
    intentos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Conversacion(telefono='{self.telefono}', estado='{self.estado}', intentos={self.intentos})>"
