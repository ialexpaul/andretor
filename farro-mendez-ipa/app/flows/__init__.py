"""Exportación de flujos de automatización."""

from app.flows.rpa_flow import procesar_flujo_rpa
from app.flows.agentic_flow import procesar_flujo_agentico

__all__ = ["procesar_flujo_rpa", "procesar_flujo_agentico"]
