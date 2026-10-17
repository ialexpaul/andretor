"""Tests de integración para el Flujo RPA Orquestado."""

from typing import Optional
from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.schemas.whatsapp import MensajeWhatsAppNormalizado
from app.schemas.pedido import ValidacionSolicitudResult


# ──────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────

def _make_msg(
    telefono: str = "51987654321",
    texto: str = "Quiero 2 balanzas analíticas",
    tipo: str = "text",
    media_id: Optional[str] = None,
    message_id: str = "MSG-001"
) -> MensajeWhatsAppNormalizado:
    return MensajeWhatsAppNormalizado(
        telefono=telefono,
        texto=texto,
        tipo=tipo,
        media_id=media_id,
        message_id=message_id,
        phone_number_id="TEST_PHONE_ID"
    )


def _make_producto_mock(
    codigo: str = "P001",
    nombre: str = "Balanza Analítica",
    precio: Decimal = Decimal("150.00"),
    stock: int = 10
):
    p = MagicMock()
    p.codigo = codigo
    p.nombre = nombre
    p.precio = precio
    p.stock = stock
    return p


def _make_conv_mock(
    estado: str = "consulta",
    producto_id: Optional[str] = None,
    producto_nombre: Optional[str] = None,
    cantidad: Optional[int] = None,
    precio: Optional[Decimal] = None,
    pedido_id: Optional[str] = None,
    intentos: int = 0
):
    c = MagicMock()
    c.telefono = "51987654321"
    c.estado = estado
    c.producto_id = producto_id
    c.producto_nombre = producto_nombre
    c.cantidad = cantidad
    c.precio = precio
    c.pedido_id = pedido_id
    c.intentos = intentos
    return c


def _make_db_mock(conv=None):
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = conv
    db.execute.return_value = result_mock
    return db


# ──────────────────────────────────────────────────────────────────
# Tests de Fase CONSULTA
# ──────────────────────────────────────────────────────────────────

class TestFaseConsulta:
    """Tests del Paso 1 BPMN: Validación de solicitud y consulta de stock."""

    @pytest.mark.asyncio
    async def test_solicitud_invalida_registra_fallido_y_responde(self):
        """Si Gemini indica solicitud no válida, debe registrarse en cola_fallidos y enviar MSG_NO_ENTENDIDO."""
        msg = _make_msg(texto="hola")
        conv = _make_conv_mock(estado="consulta")
        db = _make_db_mock(conv)

        val_invalida = ValidacionSolicitudResult(
            es_valida=False,
            motivo="Solo es un saludo",
            cantidad=1
        )

        with patch("app.flows.rpa_flow.validar_solicitud", AsyncMock(return_value=val_invalida)), \
             patch("app.flows.rpa_flow.registrar_en_cola_fallidos", AsyncMock()) as mock_fallido, \
             patch("app.flows.rpa_flow.enviar_mensaje", AsyncMock()) as mock_enviar:
            from app.flows.rpa_flow import procesar_flujo_rpa
            resultado = await procesar_flujo_rpa(msg, db)

        assert resultado["resultado"] == "no_valida"
        mock_fallido.assert_awaited_once()
        mock_enviar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_consulta_con_stock_actualiza_estado_y_envia_disponibilidad(self):
        """Si hay stock, debe actualizar estado a esperando_confirmacion y enviar precio."""
        msg = _make_msg(texto="Quiero una balanza analítica")
        conv = _make_conv_mock(estado="consulta")
        producto = _make_producto_mock(stock=5)
        db = _make_db_mock(conv)

        val_valida = ValidacionSolicitudResult(
            es_valida=True, producto="balanza analítica", cantidad=1
        )

        with patch("app.flows.rpa_flow.validar_solicitud", AsyncMock(return_value=val_valida)), \
             patch("app.flows.rpa_flow.consultar_producto", AsyncMock(return_value=producto)), \
             patch("app.flows.rpa_flow.enviar_mensaje", AsyncMock()) as mock_enviar:
            from app.flows.rpa_flow import procesar_flujo_rpa
            resultado = await procesar_flujo_rpa(msg, db)

        assert resultado["resultado"] == "disponible"
        assert resultado["stock"] == 5
        mock_enviar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_consulta_sin_stock_envia_mensaje_sin_stock(self):
        """Si el stock es 0, debe enviar MSG_SIN_STOCK y cerrar conversación."""
        msg = _make_msg(texto="Quiero alcohol en gel")
        conv = _make_conv_mock(estado="consulta")
        producto_sin_stock = _make_producto_mock(stock=0)
        db = _make_db_mock(conv)

        val_valida = ValidacionSolicitudResult(
            es_valida=True, producto="alcohol en gel", cantidad=1
        )

        with patch("app.flows.rpa_flow.validar_solicitud", AsyncMock(return_value=val_valida)), \
             patch("app.flows.rpa_flow.consultar_producto", AsyncMock(return_value=producto_sin_stock)), \
             patch("app.flows.rpa_flow.enviar_mensaje", AsyncMock()) as mock_enviar:
            from app.flows.rpa_flow import procesar_flujo_rpa
            resultado = await procesar_flujo_rpa(msg, db)

        assert resultado["resultado"] == "sin_stock"
        mock_enviar.assert_awaited_once()


# ──────────────────────────────────────────────────────────────────
# Tests de Fase CONFIRMACIÓN
# ──────────────────────────────────────────────────────────────────

class TestFaseConfirmacion:
    """Tests del Paso 2 BPMN: Decisión de compra e idempotencia."""

    @pytest.mark.asyncio
    async def test_cliente_dice_si_registra_pedido_con_idempotencia(self):
        """Si el cliente confirma (SI), debe invocar registrar_pedido_con_idempotencia y enviar métodos de pago."""
        msg = _make_msg(texto="sí, quiero comprar")
        conv = _make_conv_mock(
            estado="esperando_confirmacion",
            producto_id="P001",
            producto_nombre="Balanza Analítica",
            cantidad=1,
            precio=Decimal("150.00")
        )
        db = _make_db_mock(conv)

        pedido_mock = MagicMock()
        pedido_mock.pedido_id = "PED-123456789"
        pedido_mock.estado = "Pendiente de pago"
        pedido_mock.idempotency_key = "deadbeef" * 8

        with patch("app.flows.rpa_flow.registrar_pedido_con_idempotencia", AsyncMock(return_value=(pedido_mock, True))), \
             patch("app.flows.rpa_flow.enviar_mensaje", AsyncMock()) as mock_enviar:
            from app.flows.rpa_flow import procesar_flujo_rpa
            resultado = await procesar_flujo_rpa(msg, db)

        assert resultado["decision"] == "aceptada"
        assert resultado["pedido_id"] == "PED-123456789"
        mock_enviar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cliente_dice_no_cierra_conversacion(self):
        """Si el cliente rechaza (NO), debe actualizar a finalizado y enviar despedida."""
        msg = _make_msg(texto="no gracias")
        conv = _make_conv_mock(estado="esperando_confirmacion")
        db = _make_db_mock(conv)

        with patch("app.flows.rpa_flow.enviar_mensaje", AsyncMock()) as mock_enviar:
            from app.flows.rpa_flow import procesar_flujo_rpa
            resultado = await procesar_flujo_rpa(msg, db)

        assert resultado["decision"] == "rechazada"
        mock_enviar.assert_awaited_once()


# ──────────────────────────────────────────────────────────────────
# Tests de Fase PAGO
# ──────────────────────────────────────────────────────────────────

class TestFasePago:
    """Tests del Paso 3 BPMN: Validación de comprobante y cierre de venta."""

    @pytest.mark.asyncio
    async def test_comprobante_valido_registra_venta(self):
        """Comprobante con operación >= 6 dígitos debe registrar venta y cerrar conversación."""
        msg = _make_msg(texto="OP987654", tipo="text")
        conv = _make_conv_mock(
            estado="esperando_pago",
            pedido_id="PED-999",
            precio=Decimal("150.00"),
            intentos=0
        )
        db = _make_db_mock(conv)

        venta_mock = MagicMock()
        venta_mock.venta_id = "VEN-111222333"

        with patch("app.flows.rpa_flow.registrar_venta_y_actualizar_stock", AsyncMock(return_value=(venta_mock, 8))), \
             patch("app.flows.rpa_flow.enviar_mensaje", AsyncMock()) as mock_enviar:
            from app.flows.rpa_flow import procesar_flujo_rpa
            resultado = await procesar_flujo_rpa(msg, db)

        assert resultado["resultado"] == "valido"
        assert resultado["venta_id"] == "VEN-111222333"
        mock_enviar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_comprobante_invalido_primer_intento_solicita_nuevo(self):
        """Un comprobante inválido en primer intento debe solicitar reenvío."""
        msg = _make_msg(texto="123", tipo="text")  # Menos de 6 chars
        conv = _make_conv_mock(
            estado="esperando_pago",
            pedido_id="PED-999",
            intentos=0
        )
        db = _make_db_mock(conv)

        with patch("app.flows.rpa_flow.enviar_mensaje", AsyncMock()) as mock_enviar:
            from app.flows.rpa_flow import procesar_flujo_rpa
            resultado = await procesar_flujo_rpa(msg, db)

        assert resultado["resultado"] == "invalido"
        assert resultado["intentos"] == 1
        mock_enviar.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_comprobante_invalido_tercer_intento_escala_a_humano(self):
        """Más de 2 intentos fallidos consecutivos debe derivar a asesor humano."""
        msg = _make_msg(texto="ab", tipo="text")  # Menos de 6 chars
        conv = _make_conv_mock(
            estado="esperando_pago",
            pedido_id="PED-999",
            intentos=2  # Ya hubo 2 intentos previos
        )
        db = _make_db_mock(conv)

        caso_mock = MagicMock()
        caso_mock.caso_id = "CASO-123456"
        caso_mock.motivo = "comprobante_invalido_2_intentos"

        with patch("app.flows.rpa_flow.registrar_caso_escalado", AsyncMock(return_value=caso_mock)), \
             patch("app.flows.rpa_flow.enviar_mensaje", AsyncMock()):
            from app.flows.rpa_flow import procesar_flujo_rpa
            resultado = await procesar_flujo_rpa(msg, db)

        assert resultado["resultado"] == "escalado_a_humano"
        assert resultado["caso_id"] == "CASO-123456"
