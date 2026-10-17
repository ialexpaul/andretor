"""Modelo de datos para Pedidos."""

from datetime import datetime
from sqlalchemy import String, Numeric, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Pedido(Base):
    """Tabla pedidos que registra las intenciones de compra confirmadas."""

    __tablename__ = "pedidos"

    pedido_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    producto_id: Mapped[str] = mapped_column(String(50), nullable=False)
    producto_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(50), nullable=False, default="Pendiente de pago")
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Pedido(id='{self.pedido_id}', cliente='{self.telefono}', total={self.total}, estado='{self.estado}')>"
