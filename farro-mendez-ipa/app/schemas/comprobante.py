"""Schemas Pydantic para comprobantes de pago."""

from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class ComprobanteAnalisisResult(BaseModel):
    """Datos extraídos del comprobante mediante Gemini Vision."""
    monto: Optional[Decimal] = Field(default=None, description="Monto detectado en el voucher")
    operacion: Optional[str] = Field(default=None, description="Número o código de operación bancaria/billetera")
    fecha: Optional[str] = Field(default=None, description="Fecha detectada en formato YYYY-MM-DD")
    raw_response: Optional[str] = Field(default=None, description="Respuesta cruda del modelo")


class ValidacionComprobanteResult(BaseModel):
    """Resultado de la verificación de reglas de negocio del comprobante."""
    valido: bool
    operacion: str = ""
    monto: Optional[Decimal] = None
    fecha: Optional[str] = None
    motivo: str = ""
