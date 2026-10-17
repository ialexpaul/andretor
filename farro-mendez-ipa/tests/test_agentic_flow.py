"""Tests para el Flujo Agéntico (AI Agent con LangChain + Gemini)."""

from typing import Optional
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.schemas.whatsapp import MensajeWhatsAppNormalizado


def _make_msg(
    telefono: str = "51987654321",
    texto: str = "Necesito una balanza",
    tipo: str = "text",
    media_id: Optional[str] = None
) -> MensajeWhatsAppNormalizado:
    return MensajeWhatsAppNormalizado(
        telefono=telefono,
        texto=texto,
        tipo=tipo,
        media_id=media_id,
        message_id="MSG-AGENTIC-001",
        phone_number_id="TEST_PHONE_ID"
    )


class TestFlujAgenticoValidacion:
    """Tests del sistema prompt y herramientas del Agente."""

    def test_validar_comprobante_tool_invalido_menos_de_6(self):
        """El tool validar_comprobante_pago debe rechazar operaciones con < 6 caracteres."""
        from app.tools.validar_comprobante import validar_comprobante_pago
        resultado = validar_comprobante_pago.invoke({"comprobante": "123"})
        import json
        data = json.loads(resultado)
        assert data["valido"] is False

    def test_validar_comprobante_tool_valido_6_chars(self):
        """El tool validar_comprobante_pago debe aceptar operaciones con >= 6 caracteres."""
        from app.tools.validar_comprobante import validar_comprobante_pago
        resultado = validar_comprobante_pago.invoke({"comprobante": "OP987654"})
        import json
        data = json.loads(resultado)
        assert data["valido"] is True

    def test_validar_comprobante_tool_vacio(self):
        """El tool debe rechazar comprobante vacío."""
        from app.tools.validar_comprobante import validar_comprobante_pago
        resultado = validar_comprobante_pago.invoke({"comprobante": ""})
        import json
        data = json.loads(resultado)
        assert data["valido"] is False

    def test_validar_solicitud_tool_saludo(self):
        """El tool validar_solicitud_tool debe rechazar un simple saludo."""
        from app.tools.validar_solicitud import validar_solicitud_tool
        resultado = validar_solicitud_tool.invoke({"query": "hola"})
        import json
        data = json.loads(resultado)
        assert data["valida"] is False

    def test_validar_solicitud_tool_consulta_valida(self):
        """El tool validar_solicitud_tool debe aceptar una consulta de producto."""
        from app.tools.validar_solicitud import validar_solicitud_tool
        resultado = validar_solicitud_tool.invoke({"query": "Necesito 2 balanzas analíticas"})
        import json
        data = json.loads(resultado)
        assert data["valida"] is True

    def test_validar_solicitud_tool_mensaje_corto(self):
        """El tool debe rechazar mensajes de 1 solo carácter."""
        from app.tools.validar_solicitud import validar_solicitud_tool
        resultado = validar_solicitud_tool.invoke({"query": "a"})
        import json
        data = json.loads(resultado)
        assert data["valida"] is False


class TestFlujAgenticoSinApiKey:
    """Tests del fallback cuando no hay API key de Gemini configurada."""

    @pytest.mark.asyncio
    async def test_flujo_agentico_fallback_a_rpa_sin_api_key(self):
        """Sin API key de Gemini válida, el agente debe delegar al flujo RPA."""
        msg = _make_msg(texto="Quiero una balanza")

        resultado_rpa_mock = {"fase": "consulta", "resultado": "disponible", "stock": 5}

        with patch("app.flows.agentic_flow.settings") as mock_settings, \
             patch("app.flows.rpa_flow.procesar_flujo_rpa", AsyncMock(return_value=resultado_rpa_mock)), \
             patch("app.flows.agentic_flow.async_session_factory") as mock_session:
            mock_session.return_value.__aenter__.return_value = AsyncMock()
            mock_settings.GEMINI_API_KEY = "TU_GEMINI_API_KEY_AQUI"  # Placeholder = sin key válida
            mock_settings.GEMINI_MODEL = "gemini-1.5-flash"
            mock_settings.FLOW_MODE = "agentic"

            from app.flows.agentic_flow import procesar_flujo_agentico
            resultado = await procesar_flujo_agentico(msg)

        assert resultado["modo"] in ("agentic_fallback", "agentic")


class TestHerramientasAgente:
    """Tests de consistencia entre tools del agente y constantes de negocio."""

    def test_tools_exportadas_en_agent_tools_list(self):
        """Todos los 6 tools deben estar presentes en la lista AGENT_TOOLS."""
        from app.tools import AGENT_TOOLS
        tool_names = [t.name for t in AGENT_TOOLS]
        expected_tools = [
            "validar_solicitud_tool",
            "consultar_stock_y_precio",
            "registrar_pedido",
            "validar_comprobante_pago",
            "registrar_venta",
            "derivar_a_humano"
        ]
        for expected in expected_tools:
            assert expected in tool_names, f"Herramienta '{expected}' no encontrada en AGENT_TOOLS"

    def test_system_prompt_contiene_todos_los_pasos_bpmn(self):
        """El system prompt debe contener los 4 pasos del flujo BPMN TO-BE."""
        from app.flows.agentic_flow import SYSTEM_PROMPT_BPMN
        assert "PASO 1" in SYSTEM_PROMPT_BPMN
        assert "PASO 2" in SYSTEM_PROMPT_BPMN
        assert "PASO 3" in SYSTEM_PROMPT_BPMN
        assert "PASO 4" in SYSTEM_PROMPT_BPMN

    def test_system_prompt_menciona_todas_las_herramientas(self):
        """El system prompt debe mencionar las 6 herramientas por nombre."""
        from app.flows.agentic_flow import SYSTEM_PROMPT_BPMN
        herramientas = [
            "validar_solicitud_tool",
            "consultar_stock_y_precio",
            "registrar_pedido",
            "validar_comprobante_pago",
            "registrar_venta",
            "derivar_a_humano"
        ]
        for herramienta in herramientas:
            assert herramienta in SYSTEM_PROMPT_BPMN, f"'{herramienta}' no está en el System Prompt"
