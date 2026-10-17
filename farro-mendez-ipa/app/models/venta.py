"""Modelo de datos para Ventas concretadas."""

from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Venta(Base):
    """Tabla ventas que registra los pagos validados y compras concretadas."""

    __tablename__ = "ventas"

    venta_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    pedido_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("pedidos.pedido_id", ondelete="CASCADE"), nullable=False, index=True
    )
    telefono: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    monto: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    operacion: Mapped[str] = mapped_column(String(100), nullable=False)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="Pagado")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Venta(id='{self.venta_id}', pedido='{self.pedido_id}', monto={self.monto}, op='{self.operacion}')>"
