"""Tool: validar_solicitud para el Agente LangChain."""

import json
from langchain_core.tools import tool
from app.services.gemini_service import validar_solicitud as validar_gemini


@tool
def validar_solicitud_tool(query: str) -> str:
    """Verifica si el mensaje del cliente es una consulta válida de productos del catálogo.

    Pasa el texto del mensaje del cliente.
    Devuelve un JSON string con { valida: boolean, motivo: string, texto: string, producto: string, cantidad: number }.
    """
    q = (query or "").strip()
    if not q:
        return json.dumps({
            "valida": False,
            "motivo": "Mensaje vacío o sin contenido interpretable"
        }, ensure_ascii=False)

    if len(q) < 2:
        return json.dumps({
            "valida": False,
            "motivo": "Mensaje demasiado corto para interpretar una solicitud"
        }, ensure_ascii=False)

    palabras_irrelevantes = ["hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "gracias", "chau", "ok"]
    if q.lower() in palabras_irrelevantes:
        return json.dumps({
            "valida": False,
            "motivo": "El cliente solo envió un saludo o mensaje de cortesía, no una consulta de producto"
        }, ensure_ascii=False)

    return json.dumps({
        "valida": True,
        "motivo": "Solicitud interpretable de producto",
        "texto": q
    }, ensure_ascii=False)
