"""Flujo Agéntico (AI Agent con LangChain y Google Gemini).

Replica el modelo BPMN TO-BE mediante un agente autónomo provisto de herramientas (tool-calling),
memoria por sesión telefónica (Window Buffer) y un prompt de sistema estructurado.
"""

from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.database import async_session_factory
from app.schemas.whatsapp import MensajeWhatsAppNormalizado
from app.tools import AGENT_TOOLS
from app.services.whatsapp_service import enviar_mensaje
from app.utils.logger import logger


SYSTEM_PROMPT_BPMN = """Eres el asistente inteligente de "Atención de Pedidos por Canal Digital (WhatsApp)" de la empresa FARRO MENDEZ CORPORATION S.A.C.
Atiendes a un cliente por WhatsApp; el número de teléfono del cliente es su identificador único (cliente/from).
Responde SIEMPRE en español, de forma breve, cordial, profesional y clara. Devuelve exclusivamente el texto que se enviará al cliente por WhatsApp.

Tienes a tu disposición estas 6 herramientas obligatorias:
1. validar_solicitud_tool: Verifica si el mensaje es una consulta o solicitud interpretable de productos.
2. consultar_stock_y_precio: Consulta el inventario en tiempo real (product_id, nombre, precio, stock).
3. registrar_pedido: Inserta el pedido con idempotencia SHA-256 en la base de datos (estado 'Pendiente de pago').
4. validar_comprobante_pago: Valida que el comprobante de pago tenga al menos 6 caracteres alfanuméricos.
5. registrar_venta: Inserta la venta final en la base de datos y descuenta automáticamente el stock en inventario.
6. derivar_a_humano: Escala el caso a un asesor humano registrándolo en Casos_Escalados.

FLUJO OBLIGATORIO (BPMN TO-BE), respeta rigurosamente el orden de las fases:
[PASO 1] Consulta Inicial:
  - Llama a `validar_solicitud_tool` con el texto recibido.
  - Si NO es válida (saludos, spam o no entendible): responde cordialmente pidiendo que especifiquen el producto y cantidad, y finaliza.
  - Si es válida: llama a `consultar_stock_y_precio`.

[PASO 2] Validación de Stock:
  - Identifica el producto solicitado en el catálogo.
  - Si NO hay stock disponible (stock <= 0) o no existe: informa amablemente la falta de stock y finaliza la atención.
  - Si SI hay stock: informa el nombre exacto, precio unitario y stock disponible, y pregunta explícitamente: "¿Deseas comprar? Responde SI o NO".

[PASO 3] Confirmación y Registro de Pedido:
  - Si el cliente responde que NO desea comprar: cancela amablemente la interacción ("Entendido, no registraremos la compra...").
  - Si el cliente responde que SI: llama de inmediato a `registrar_pedido` (con cliente=telefono, product_id, producto_nombre, cantidad, precio_unitario).
  - Tras registrar el pedido, envía el mensaje informando el #pedido_id registrado y los métodos de pago (Yape, Plin, Transferencia BCP, Efectivo contra entrega), solicitando que envíe su comprobante.

[PASO 4] Validación de Pago y Confirmación de Venta:
  - Cuando el cliente envíe su comprobante o número de operación:
  - Llama a `validar_comprobante_pago`.
  - Si es VÁLIDO (>= 6 caracteres): llama a `registrar_venta` con el pedido_id, cliente, monto y operacion. Luego envía la felicitación y confirmación de compra finalizada al cliente.
  - Si es INVÁLIDO: solicita un nuevo comprobante legible. Si ya ha fallado 2 veces consecutivas en la conversación, llama a `derivar_a_humano` y avisa al cliente que un asesor humano lo contactará en breve.

Reglas esenciales:
- Usa el historial de la conversación para saber en qué etapa estás.
- NUNCA inventes precios ni existencias: usa siempre `consultar_stock_y_precio`.
- Ante errores irrecuperables o segundo fallo consecutivo de comprobante, usa siempre `derivar_a_humano`.
"""

# Almacenamiento en memoria tipo Window Buffer por cada sesión telefónica (últimos 10 turnos)
_MEMORY_STORE: Dict[str, List[BaseMessage]] = {}
MAX_WINDOW_LENGTH = 10


def _obtener_historial_sesion(telefono: str) -> List[BaseMessage]:
    """Recupera el historial de conversación para una ventana deslizante de memoria."""
    if telefono not in _MEMORY_STORE:
        _MEMORY_STORE[telefono] = []
    return _MEMORY_STORE[telefono]


def _guardar_mensaje_sesion(telefono: str, mensaje: BaseMessage) -> None:
    """Agrega un mensaje a la memoria y preserva el tamaño de la ventana."""
    historial = _obtener_historial_sesion(telefono)
    historial.append(mensaje)
    if len(historial) > MAX_WINDOW_LENGTH * 2:
        _MEMORY_STORE[telefono] = historial[-(MAX_WINDOW_LENGTH * 2):]


async def procesar_flujo_agentico(
    msg: MensajeWhatsAppNormalizado
) -> Dict[str, Any]:
    """Ejecuta el flujo agéntico con LangChain y Google Gemini.

    Args:
        msg: Mensaje normalizado recibido del webhook.

    Returns:
        Dict con la respuesta generada por el agente y metadatos.
    """
    telefono = msg.telefono
    texto = msg.texto.strip()
    tipo = msg.tipo

    # Si llegó archivo multimedia, contextualizar para el agente
    if tipo in ("image", "document"):
        user_input = (
            f"El cliente {telefono} envió un archivo adjunto ({tipo}, media_id: {msg.media_id or 'adjunto'}). "
            f"Voucher/Operación indicada: {texto or 'comprobante_adjunto'}"
        )
    else:
        user_input = f"El cliente {telefono} dice: {texto}"

    logger.info(f"[AGENTIC FLOW] Invocando AI Agent para {telefono}")

    # Inicializar modelo Gemini o fallback
    api_key = settings.GEMINI_API_KEY
    tiene_api_key = api_key and "TU_GEMINI" not in api_key

    if tiene_api_key:
        try:
            llm = ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL,
                google_api_key=api_key,
                temperature=0.2
            )

            agent = create_react_agent(
                model=llm,
                tools=AGENT_TOOLS,
                prompt=SYSTEM_PROMPT_BPMN
            )

            historial = _obtener_historial_sesion(telefono)
            mensajes_input = list(historial) + [HumanMessage(content=user_input)]
            resultado = await agent.ainvoke({"messages": mensajes_input})

            mensajes_salida = resultado.get("messages", [])
            respuesta_texto = ""
            if mensajes_salida:
                ultimo_msg = mensajes_salida[-1]
                respuesta_texto = getattr(ultimo_msg, "content", str(ultimo_msg))

            # Actualizar memoria de conversación
            _guardar_mensaje_sesion(telefono, HumanMessage(content=user_input))
            _guardar_mensaje_sesion(telefono, AIMessage(content=respuesta_texto))

            # Enviar respuesta al cliente vía WhatsApp
            await enviar_mensaje(telefono=telefono, texto=respuesta_texto, phone_number_id=msg.phone_number_id)

            return {
                "modo": "agentic",
                "telefono": telefono,
                "respuesta": respuesta_texto,
                "status": "success"
            }
        except Exception as exc:
            logger.error(f"[AGENTIC FLOW] Error en ejecución de LangChain: {exc}")

    # Fallback transparente si no hay API key de Gemini activa:
    # Se asegura la continuidad del servicio ejecutando las tools con la lógica de negocio.
    logger.warning("[AGENTIC FLOW] Operando en modo agéntico heurístico/simulado")
    from app.flows.rpa_flow import procesar_flujo_rpa

    try:
        async with async_session_factory() as db:
            res_rpa = await procesar_flujo_rpa(msg, db)
    except Exception as exc:
        logger.error(f"[AGENTIC FLOW] Error en fallback RPA: {exc}")
        res_rpa = {"status": "fallback_error", "error": str(exc)}

    return {
        "modo": "agentic_fallback",
        "telefono": telefono,
        "resultado": res_rpa,
        "status": "completed_via_orchestrator"
    }
