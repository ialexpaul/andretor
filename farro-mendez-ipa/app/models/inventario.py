"""Modelo de datos para Inventario de Productos."""

from sqlalchemy import String, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Inventario(Base):
    """Tabla inventario que almacena el catálogo de productos y stock en tiempo real."""

    __tablename__ = "inventario"

    codigo: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    precio: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Inventario(codigo='{self.codigo}', nombre='{self.nombre}', precio={self.precio}, stock={self.stock})>"
