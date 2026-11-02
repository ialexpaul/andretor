"""Esquema y validador para el Contrato de Datos de Entrada (Instrumento Lab 2).

FARRO MENDEZ CORPORATION S.A.C. - Proceso de Pedidos por Canal Digital
Define las reglas estrictas de validación de carga útil antes de cualquier
escritura en base de datos.
"""

from typing import Optional, Literal, Dict, Any, Tuple
from pydantic import BaseModel, Field, model_validator


class ContratoEntrada(BaseModel):
    """Contrato formal de datos de entrada conforme a la matriz del Laboratorio 02."""

    accion: Literal["consulta", "compra", "pago"] = Field(
        ...,
        description="Operación solicitada: 'consulta', 'compra' o 'pago'"
    )
    producto: Optional[str] = Field(
        default=None,
        description="Código (P001, P002, P003) o nombre del producto (obligatorio en consulta/compra)"
    )
    cliente: Optional[str] = Field(
        default=None,
        description="Identificador único del cliente o teléfono (obligatorio en compra)"
    )
    cantidad: Optional[int] = Field(
        default=None,
        description="Cantidad solicitada, entero entre 1 y 500 (obligatorio en compra)"
    )
    decision: Optional[Literal["si", "no"]] = Field(
        default=None,
        description="Decisión de compra ('si' o 'no', obligatorio en compra)"
    )
    pedido_id: Optional[str] = Field(
        default=None,
        description="Identificador del pedido (obligatorio en pago)"
    )
    comprobante: Optional[str] = Field(
        default=None,
        description="Referencia del comprobante de pago (obligatorio en pago)"
    )

    @model_validator(mode="after")
    def validar_reglas_por_accion(self) -> "ContratoEntrada":
        """Valida las reglas condicionales según la acción solicitada."""
        # 1. Reglas para ACCION = CONSULTA
        if self.accion == "consulta":
            if not self.producto or not self.producto.strip():
                raise ValueError("El campo 'producto' es obligatorio para la acción 'consulta'")

        # 2. Reglas para ACCION = COMPRA
        elif self.accion == "compra":
            if not self.producto or not self.producto.strip():
                raise ValueError("El campo 'producto' es obligatorio para la acción 'compra'")
            if not self.cliente or not self.cliente.strip():
                raise ValueError("El campo 'cliente' es obligatorio para la acción 'compra'")
            if self.cantidad is None:
                raise ValueError("El campo 'cantidad' es obligatorio para la acción 'compra'")
            if not (1 <= self.cantidad <= 500):
                raise ValueError("El campo 'cantidad' debe ser un entero entre 1 y 500")
            if not self.decision or self.decision not in ("si", "no"):
                raise ValueError("El campo 'decision' es obligatorio para 'compra' y debe ser 'si' o 'no'")

        # 3. Reglas para ACCION = PAGO
        elif self.accion == "pago":
            if not self.pedido_id or not self.pedido_id.strip():
                raise ValueError("El campo 'pedido_id' es obligatorio para la acción 'pago'")
            if self.comprobante is None or not self.comprobante.strip():
                raise ValueError("El campo 'comprobante' es obligatorio y no puede estar vacío para la acción 'pago'")

        return self


def validar_payload_contrato(payload: Dict[str, Any]) -> Tuple[bool, Optional[ContratoEntrada], Optional[str]]:
    """Valida un payload arbitrario contra el Contrato de Entrada del Laboratorio 02.

    Returns:
        (es_valido, contrato_o_none, mensaje_error_o_none)
    """
    if not isinstance(payload, dict):
        return False, None, "El payload debe ser un objeto JSON válido"

    if "accion" not in payload or not payload.get("accion"):
        return False, None, "El campo 'accion' es obligatorio (valores permitidos: consulta, compra, pago)"

    try:
        contrato = ContratoEntrada(**payload)
        return True, contrato, None
    except Exception as exc:
        # Extraer detalle legible del fallo
        msg = str(exc)
        if "Value error, " in msg:
            msg = msg.split("Value error, ")[-1].split(" [type=")[0].strip()
        return False, None, msg
