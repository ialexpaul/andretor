"""Servicio de integración con WhatsApp Cloud API (Meta Graph API)."""

from typing import Optional
import httpx
from app.config import settings
from app.utils.logger import logger


async def enviar_mensaje(
    telefono: str,
    texto: str,
    phone_number_id: Optional[str] = None
) -> bool:
    """Envía un mensaje de texto plano a un cliente a través de WhatsApp Cloud API.

    Si las credenciales son placeholders, simula el envío exitoso en logs
    para permitir desarrollo local y pruebas sin romper el flujo.
    """
    token = settings.WHATSAPP_API_TOKEN
    p_id = phone_number_id or settings.WHATSAPP_PHONE_NUMBER_ID

    # Modo simulación si no hay credenciales configuradas
    if not token or "TU_TOKEN" in token or not p_id or "TU_PHONE" in p_id:
        logger.info(
            f"[WHATSAPP SIMULADO] Destino: {telefono} | Contenido:\n"
            f"----------------------------------------\n"
            f"{texto}\n"
            f"----------------------------------------"
        )
        return True

    url = f"{settings.WHATSAPP_API_URL}/{p_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": telefono.strip().replace("+", ""),
        "type": "text",
        "text": {"preview_url": False, "body": texto},
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                logger.info(f"Mensaje WhatsApp enviado con éxito a {telefono}")
                return True
            else:
                logger.error(
                    f"Error enviando mensaje WhatsApp a {telefono}: HTTP {resp.status_code} - {resp.text}"
                )
                return False
    except Exception as exc:
        logger.error(f"Excepción al conectar con WhatsApp API: {exc}")
        return False


async def obtener_url_media(media_id: str) -> Optional[str]:
    """Obtiene la URL temporal de descarga de un archivo multimedia (imagen/PDF) mediante su media_id."""
    token = settings.WHATSAPP_API_TOKEN
    if not token or "TU_TOKEN" in token or not media_id:
        logger.warning(f"No hay token de WhatsApp válido para consultar media_id={media_id}")
        return None

    url = f"{settings.WHATSAPP_API_URL}/{media_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("url")
            logger.error(f"Error consultando media_id={media_id}: {resp.text}")
            return None
    except Exception as exc:
        logger.error(f"Excepción al obtener URL de media: {exc}")
        return None


async def descargar_media(url: str) -> bytes:
    """Descarga los bytes binarios del archivo multimedia desde la URL de Meta."""
    token = settings.WHATSAPP_API_TOKEN
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.content
    except Exception as exc:
        logger.error(f"Error descargando binario de comprobante: {exc}")
        raise
