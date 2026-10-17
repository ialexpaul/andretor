"""Schemas Pydantic para validación y gestión de Pedidos."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ValidacionSolicitudResult(BaseModel):
    """Resultado del análisis de la solicitud con Gemini."""
    es_valida: bool = Field(description="Indica si el mensaje contiene una intención de compra comprensible")
    producto: Optional[str] = Field(default=None, description="Nombre o código del producto extraído")
    cantidad: int = Field(default=1, description="Cantidad solicitada, 1 por defecto")
    motivo: Optional[str] = Field(default=None, description="Razón o explicación de la validación")


class SolicitudPedidoCreate(BaseModel):
    """Datos necesarios para registrar un pedido."""
    telefono: str
    producto_id: str
    producto_nombre: str
    cantidad: int
    precio_unitario: Decimal


class PedidoResponse(BaseModel):
    """Representación del pedido registrado."""
    pedido_id: str
    telefono: str
    producto_id: str
    producto_nombre: str
    cantidad: int
    precio_unitario: Decimal
    total: Decimal
    estado: str
    idempotency_key: str
    creado_en: datetime

    model_config = ConfigDict(from_attributes=True)
