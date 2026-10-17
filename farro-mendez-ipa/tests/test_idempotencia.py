"""Tests para la función de idempotencia SHA-256."""

import hashlib
import pytest
from app.services.idempotencia import generar_clave_idempotencia


class TestIdempotencia:
    """Suite de pruebas para la generación de claves de idempotencia."""

    def test_genera_hash_sha256(self):
        """La clave debe tener exactamente 64 caracteres hexadecimales (SHA-256)."""
        key = generar_clave_idempotencia("compra", "P001", "51987654321", 2)
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_determinismo_mismos_valores(self):
        """Mismos parámetros deben generar exactamente la misma clave."""
        key1 = generar_clave_idempotencia("compra", "P001", "51987654321", 2)
        key2 = generar_clave_idempotencia("compra", "P001", "51987654321", 2)
        assert key1 == key2

    def test_diferente_producto_produce_diferente_key(self):
        """Diferentes productos deben generar claves distintas."""
        key1 = generar_clave_idempotencia("compra", "P001", "51987654321", 2)
        key2 = generar_clave_idempotencia("compra", "P002", "51987654321", 2)
        assert key1 != key2

    def test_diferente_cliente_produce_diferente_key(self):
        """Diferentes clientes deben generar claves distintas."""
        key1 = generar_clave_idempotencia("compra", "P001", "51987654321", 2)
        key2 = generar_clave_idempotencia("compra", "P001", "51912345678", 2)
        assert key1 != key2

    def test_diferente_cantidad_produce_diferente_key(self):
        """Diferentes cantidades deben producir claves distintas."""
        key1 = generar_clave_idempotencia("compra", "P001", "51987654321", 1)
        key2 = generar_clave_idempotencia("compra", "P001", "51987654321", 3)
        assert key1 != key2

    def test_normaliza_signos_en_telefono(self):
        """El teléfono con o sin '+' debe generar la misma clave."""
        key1 = generar_clave_idempotencia("compra", "P001", "+51987654321", 2)
        key2 = generar_clave_idempotencia("compra", "P001", "51987654321", 2)
        assert key1 == key2

    def test_normaliza_mayusculas_en_producto(self):
        """El código de producto en mayúsculas y minúsculas debe dar la misma clave."""
        key1 = generar_clave_idempotencia("compra", "P001", "51987654321", 2)
        key2 = generar_clave_idempotencia("COMPRA", "p001", "51987654321", 2)
        assert key1 == key2

    def test_no_incluye_timestamp(self):
        """Verificar que el mismo input siempre da la misma clave (no usa timestamps)."""
        import time
        key1 = generar_clave_idempotencia("compra", "P001", "51999000000", 5)
        time.sleep(0.01)
        key2 = generar_clave_idempotencia("compra", "P001", "51999000000", 5)
        assert key1 == key2

    def test_verificar_calculo_manual(self):
        """Verificar que el hash es SHA-256 de la cadena esperada."""
        accion, producto, cliente, cantidad = "compra", "p001", "51987654321", 2
        cadena_esperada = f"{accion}|{producto}|{cliente}|{cantidad}"
        hash_esperado = hashlib.sha256(cadena_esperada.encode("utf-8")).hexdigest()
        key = generar_clave_idempotencia(accion, producto, f"+{cliente}", cantidad)
        assert key == hash_esperado
