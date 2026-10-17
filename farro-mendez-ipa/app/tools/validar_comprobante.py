"""Tool: validar_comprobante_pago para el Agente LangChain."""

import json
import re
from langchain_core.tools import tool


@tool
def validar_comprobante_pago(comprobante: str) -> str:
    """Valida el comprobante de pago enviado por el cliente.

    Pasa el código o número de operación del comprobante (o texto del voucher).
    Devuelve JSON con { valido: boolean, motivo: string, comprobante: string }.
    Regla BPMN: Es válido si el número de operación tiene 6 o más caracteres alfanuméricos.
    """
    c = (comprobante or "").strip()
    if not c:
        return json.dumps({
            "valido": False,
            "motivo": "No se recibió ningún número de comprobante o texto",
            "comprobante": ""
        }, ensure_ascii=False)

    # Extraer caracteres alfanuméricos limpios
    limpio = re.sub(r"[\s\-_#]+", "", c)
    valido = len(limpio) >= 6

    motivo = (
        "Comprobante válido: cumple con el estándar de mínimo 6 dígitos/caracteres de operación"
        if valido
        else "Comprobante inválido: el número de operación debe tener al menos 6 caracteres"
    )

    return json.dumps({
        "valido": valido,
        "motivo": motivo,
        "comprobante": limpio
    }, ensure_ascii=False)
