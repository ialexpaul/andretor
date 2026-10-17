"""Schemas Pydantic para la integración con WhatsApp Cloud API."""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class WhatsAppMetadata(BaseModel):
    display_phone_number: Optional[str] = None
    phone_number_id: Optional[str] = None


class WhatsAppTextMessage(BaseModel):
    body: str = ""


class WhatsAppMediaItem(BaseModel):
    id: str
    mime_type: Optional[str] = None
    sha256: Optional[str] = None


class WhatsAppButtonReply(BaseModel):
    id: Optional[str] = None
    text: Optional[str] = None


class WhatsAppListReply(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class WhatsAppInteractive(BaseModel):
    type: Optional[str] = None
    button_reply: Optional[WhatsAppButtonReply] = None
    list_reply: Optional[WhatsAppListReply] = None


class WhatsAppMessageRaw(BaseModel):
    from_: str = Field(alias="from")
    id: str
    timestamp: str
    type: str = "text"
    text: Optional[WhatsAppTextMessage] = None
    image: Optional[WhatsAppMediaItem] = None
    document: Optional[WhatsAppMediaItem] = None
    interactive: Optional[WhatsAppInteractive] = None
    button: Optional[WhatsAppButtonReply] = None

    model_config = ConfigDict(populate_by_name=True)


class WhatsAppContact(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    wa_id: Optional[str] = None


class WhatsAppValue(BaseModel):
    messaging_product: Optional[str] = None
    metadata: Optional[WhatsAppMetadata] = None
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessageRaw]] = None


class WhatsAppChange(BaseModel):
    value: WhatsAppValue
    field: str


class WhatsAppEntry(BaseModel):
    id: str
    changes: List[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    """Payload raíz recibido de Meta Cloud API Webhook."""
    object: Optional[str] = None
    entry: List[WhatsAppEntry] = []


class MensajeWhatsAppNormalizado(BaseModel):
    """Estructura normalizada y desacoplada del mensaje entrante."""
    telefono: str
    texto: str = ""
    tipo: str = "text"
    media_id: Optional[str] = None
    message_id: str = ""
    phone_number_id: Optional[str] = None
    timestamp: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None


def extraer_mensaje_normalizado(payload: dict) -> Optional[MensajeWhatsAppNormalizado]:
    """Extrae y normaliza los datos relevantes del webhook de WhatsApp.

    Soporta mensajes de texto, imágenes, documentos (PDF) y botones interactivos.
    """
    try:
        entries = payload.get("entry", [])
        if not entries:
            return None

        changes = entries[0].get("changes", [])
        if not changes:
            return None

        val = changes[0].get("value", {})
        messages = val.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        meta = val.get("metadata", {})

        tipo = msg.get("type", "text")
        texto = ""
        media_id = None

        if tipo == "text" and "text" in msg:
            texto = msg["text"].get("body", "").strip()
        elif tipo == "button" and "button" in msg:
            texto = msg["button"].get("text", "").strip()
        elif tipo == "interactive" and "interactive" in msg:
            inter = msg["interactive"]
            if "button_reply" in inter:
                texto = inter["button_reply"].get("title", "")
            elif "list_reply" in inter:
                texto = inter["list_reply"].get("title", "")
        elif tipo == "image" and "image" in msg:
            media_id = msg["image"].get("id")
            texto = msg["image"].get("caption", "").strip() or "Comprobante de pago (imagen)"
        elif tipo == "document" and "document" in msg:
            media_id = msg["document"].get("id")
            texto = msg["document"].get("caption", "").strip() or "Comprobante de pago (PDF/documento)"

        return MensajeWhatsAppNormalizado(
            telefono=str(msg.get("from", "")),
            texto=texto,
            tipo=tipo,
            media_id=media_id,
            message_id=str(msg.get("id", "")),
            phone_number_id=str(meta.get("phone_number_id", "")) if meta else None,
            timestamp=str(msg.get("timestamp", "")),
            raw_payload=payload
        )
    except Exception:
        return None
