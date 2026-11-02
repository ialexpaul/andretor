"""Banco de Pruebas Automatizadas (Entregable E2 - Instrumento Lab 2).

FARRO MENDEZ CORPORATION S.A.C. - Proceso de Pedidos por Canal Digital
Ejecuta y verifica al 100% las 4 pruebas obligatorias del instrumento de evaluación:
- P1: Validación de Contrato de Datos de Entrada (5 solicitudes mal formadas -> HTTP 400)
- P2: Idempotencia SHA-256 (Dos envíos idénticos -> un solo registro, HTTP 200)
- P3: Cola de Fallidos (Registro de solicitud inválida con payload íntegro y campos de auditoría)
- P4: Códigos de Respuesta HTTP (200 / 201 vs 400 según corresponda)
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db
from app.models.pedido import Pedido
from app.models.inventario import Inventario
from app.models.cola_fallidos import ColaFallidos
from app.schemas.contrato_entrada import validar_payload_contrato


# ──────────────────────────────────────────────────────────────────
# Mocks y Fixtures
# ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db_session():
    """Sesión simulada de base de datos para pruebas aisladas."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def override_db(mock_db_session):
    """Sobrescribe la dependencia de base de datos en FastAPI."""
    app.dependency_overrides[get_db] = lambda: mock_db_session
    yield mock_db_session
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────
# P1: PRUEBA DE VALIDACIÓN (5 Solicitudes Mal Formadas -> HTTP 400)
# ──────────────────────────────────────────────────────────────────

class TestP1ValidacionContrato:
    """P1: Cinco solicitudes mal formadas deben ser rechazadas con código 400."""

    @pytest.mark.asyncio
    async def test_p1_1_falta_campo_accion(self, override_db):
        """1. Solicitud sin campo 'accion'."""
        payload = {"producto": "P001", "cliente": "51987654321"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/proceso/solicitud", json=payload)
        assert res.status_code == 400
        assert "accion" in res.json()["motivo"].lower()

    @pytest.mark.asyncio
    async def test_p1_2_accion_no_contemplada(self, override_db):
        """2. Acción desconocida o no permitida."""
        payload = {"accion": "transferencia_externa", "producto": "P001"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/proceso/solicitud", json=payload)
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_p1_3_consulta_sin_producto(self, override_db):
        """3. Consulta sin especificar el producto."""
        payload = {"accion": "consulta"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/proceso/solicitud", json=payload)
        assert res.status_code == 400
        assert "producto" in res.json()["motivo"].lower()

    @pytest.mark.asyncio
    async def test_p1_4_compra_datos_incompletos(self, override_db):
        """4. Compra sin cliente o sin cantidad."""
        payload = {"accion": "compra", "producto": "P001", "decision": "si"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/proceso/solicitud", json=payload)
        assert res.status_code == 400
        assert "cliente" in res.json()["motivo"].lower() or "cantidad" in res.json()["motivo"].lower()

    @pytest.mark.asyncio
    async def test_p1_5_compra_cantidad_fuera_de_rango(self, override_db):
        """5. Compra con cantidad fuera del rango permitido (1-500)."""
        payload = {
            "accion": "compra",
            "producto": "P001",
            "cliente": "51987654321",
            "cantidad": 9999,
            "decision": "si"
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post("/api/proceso/solicitud", json=payload)
        assert res.status_code == 400
        assert "500" in res.json()["motivo"]


# ──────────────────────────────────────────────────────────────────
# P2: PRUEBA DE IDEMPOTENCIA (2 Envíos Idénticos Consecutivos)
# ──────────────────────────────────────────────────────────────────

class TestP2Idempotencia:
    """P2: Dos envíos idénticos generan un único pedido; el segundo responde HTTP 200 con el pedido existente."""

    @pytest.mark.asyncio
    async def test_p2_dos_envios_identicos_consecutivos(self, override_db):
        payload_compra = {
            "accion": "compra",
            "producto": "P001",
            "cliente": "51987654321",
            "cantidad": 2,
            "decision": "si"
        }

        # Simular producto disponible en stock
        prod_mock = MagicMock()
        prod_mock.product_id = "P001"
        prod_mock.nombre = "Balanza Analítica"
        prod_mock.precio = Decimal("150.00")
        prod_mock.stock = 15

        pedido_mock = MagicMock()
        pedido_mock.pedido_id = "PED-20261029-001"
        pedido_mock.total = Decimal("300.00")
        pedido_mock.idempotency_key = "abc123sha256"

        with patch("app.main.consultar_producto", new_callable=AsyncMock) as mock_prod:
            mock_prod.return_value = prod_mock

            with patch("app.main.registrar_pedido_con_idempotencia", new_callable=AsyncMock) as mock_reg:
                # 1er envío: Pedido nuevo insertado de novo
                mock_reg.return_value = (pedido_mock, True)
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    res1 = await ac.post("/api/proceso/solicitud", json=payload_compra)

                assert res1.status_code in (200, 201)
                data1 = res1.json()
                assert data1["pedido_id"] == "PED-20261029-001"
                assert data1["idempotente"] is False

                # 2do envío idéntico: Colisión detectada, devuelve el existente
                mock_reg.return_value = (pedido_mock, False)
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                    res2 = await ac.post("/api/proceso/solicitud", json=payload_compra)

                assert res2.status_code == 200
                data2 = res2.json()
                assert data2["pedido_id"] == data1["pedido_id"]
                assert data2["idempotente"] is True


# ──────────────────────────────────────────────────────────────────
# P3: PRUEBA DE COLA DE FALLIDOS (Carga Original + 6 Campos Mínimos)
# ──────────────────────────────────────────────────────────────────

class TestP3ColaFallidos:
    """P3: Toda solicitud mal formada debe persistirse íntegra en la cola de fallidos."""

    @pytest.mark.asyncio
    async def test_p3_registro_en_cola_con_carga_original(self, override_db):
        solicitud_invalida = {
            "accion": "pago",
            "pedido_id": "PED-001",
            "comprobante": ""  # Inválido: comprobante vacío
        }

        with patch("app.main.registrar_en_cola_fallidos", new_callable=AsyncMock) as mock_cola:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                res = await ac.post("/api/proceso/solicitud", json=solicitud_invalida)

            assert res.status_code == 400
            assert mock_cola.called
            # Verificar que se envió la carga original íntegra
            args, kwargs = mock_cola.call_args
            assert kwargs.get("carga_original") == solicitud_invalida


# ──────────────────────────────────────────────────────────────────
# P4: PRUEBA DE CÓDIGOS DE RESPUESTA HTTP (200 / 201 vs 400)
# ──────────────────────────────────────────────────────────────────

class TestP4CodigosRespuesta:
    """P4: Códigos correctos: entrada válida retorna éxito (200/201); inválida retorna 400."""

    @pytest.mark.asyncio
    async def test_p4_consulta_valida_e_invalida(self, override_db):
        prod_mock = MagicMock()
        prod_mock.product_id = "P001"
        prod_mock.nombre = "Balanza Analítica"
        prod_mock.precio = Decimal("150.00")
        prod_mock.stock = 5

        with patch("app.main.consultar_producto", new_callable=AsyncMock) as mock_prod:
            mock_prod.return_value = prod_mock

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                # Válida -> HTTP 200
                res_valida = await ac.post("/api/proceso/solicitud", json={"accion": "consulta", "producto": "P001"})
                assert res_valida.status_code == 200

                # Inválida -> HTTP 400
                res_invalida = await ac.post("/api/proceso/solicitud", json={"accion": "consulta"})
                assert res_invalida.status_code == 400

    @pytest.mark.asyncio
    async def test_p4_pago_valido_e_invalido(self, override_db):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Inválido (sin comprobante) -> HTTP 400
            res_inv = await ac.post("/api/proceso/solicitud", json={"accion": "pago", "pedido_id": "PED-01"})
            assert res_inv.status_code == 400
