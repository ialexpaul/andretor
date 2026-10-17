"""Módulo de Idempotencia del Negocio.

Implementa la regla estricta:
Hash SHA-256 de la concatenación: 'accion|producto|cliente|cantidad'.
Excluye pedido_id, marcas de tiempo (timestamp) o identificadores de plataforma.
"""

import hashlib
from typing import Union


def generar_clave_idempotencia(
    accion: str,
    producto: str,
    cliente: str,
    cantidad: Union[int, str]
) -> str:
    """Genera una clave SHA-256 determinista a partir de los atributos esenciales del pedido.

    Args:
        accion: Operación ('compra', 'pedido').
        producto: Código o nombre normalizado del producto solicitado.
        cliente: Identificador único del cliente (número de teléfono normalizado).
        cantidad: Cantidad de unidades solicitadas.

    Returns:
        Hexdigest SHA-256 de 64 caracteres.
    """
    accion_norm = (accion or "").strip().lower()
    producto_norm = (producto or "").strip().lower()
    cliente_norm = (str(cliente) or "").strip().replace("+", "").replace(" ", "")
    cantidad_norm = str(int(cantidad) if str(cantidad).isdigit() else cantidad).strip()

    cadena_base = f"{accion_norm}|{producto_norm}|{cliente_norm}|{cantidad_norm}"
    return hashlib.sha256(cadena_base.encode("utf-8")).hexdigest()
