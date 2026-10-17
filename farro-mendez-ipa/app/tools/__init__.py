"""Exportación de tools para el Agente LangChain."""

from app.tools.validar_solicitud import validar_solicitud_tool
from app.tools.consultar_stock import consultar_stock_y_precio
from app.tools.registrar_pedido import registrar_pedido
from app.tools.validar_comprobante import validar_comprobante_pago
from app.tools.registrar_venta import registrar_venta
from app.tools.derivar_a_humano import derivar_a_humano

AGENT_TOOLS = [
    validar_solicitud_tool,
    consultar_stock_y_precio,
    registrar_pedido,
    validar_comprobante_pago,
    registrar_venta,
    derivar_a_humano,
]

__all__ = [
    "validar_solicitud_tool",
    "consultar_stock_y_precio",
    "registrar_pedido",
    "validar_comprobante_pago",
    "registrar_venta",
    "derivar_a_humano",
    "AGENT_TOOLS",
]
