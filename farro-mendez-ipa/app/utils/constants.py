"""Constantes de negocio para FARRO MENDEZ CORPORATION S.A.C.

Define los estados del modelo BPMN, mensajes estándar hacia el cliente y
códigos de control de errores.
"""

# Estados de Conversación
ESTADO_CONSULTA = "consulta"
ESTADO_CONFIRMACION = "esperando_confirmacion"
ESTADO_PAGO = "esperando_pago"
ESTADO_FINALIZADO = "finalizado"
ESTADO_DERIVADO = "derivado"

# Estados de Pedido
PEDIDO_ESTADO_PENDIENTE = "Pendiente de pago"
PEDIDO_ESTADO_PAGADO = "Pagado"

# Estados de Venta
VENTA_ESTADO_PAGADO = "Pagado"

# Estados de Cola de Fallidos
FALLIDO_ESTADO_PENDIENTE = "pendiente"
FALLIDO_ESTADO_REVISADO = "revisado"

# Motivos de error y escalado
MOTIVO_SOLICITUD_INVALIDA = "solicitud_invalida"
MOTIVO_SIN_STOCK = "sin_stock"
MOTIVO_COMPROBANTE_INVALIDO = "comprobante_invalido"
MOTIVO_ESCALADO_2_INTENTOS = "comprobante_invalido_2_intentos"
MOTIVO_SOLICITUD_NO_SOPORTADA = "solicitud_no_soportada"

# Mensajes Estándar al Cliente
MSG_NO_ENTENDIDO = (
    "No logramos entender tu solicitud. Por favor indícanos el producto que "
    "necesitas y la cantidad (por ejemplo: \"Quiero 2 balanzas analíticas\")."
)

MSG_SIN_STOCK = (
    "Lo sentimos, por el momento no contamos con stock disponible de ese producto. "
    "Gracias por escribirnos a FARRO MENDEZ CORP."
)

MSG_COMPRA_RECHAZADA = (
    "Entendido, no registraremos la compra. Cuando quieras estamos para ayudarte. "
    "¡Gracias por escribir a FARRO MENDEZ CORP!"
)

MSG_SOLICITAR_NUEVO_COMPROBANTE = (
    "No pudimos validar tu comprobante. Por favor envía nuevamente una foto o PDF "
    "claro del comprobante de pago (donde se aprecie el monto, fecha y número de operación con mín. 6 dígitos)."
)

MSG_DERIVADO_HUMANO = (
    "Hemos derivado tu caso a un agente humano para ayudarte con la validación de tu pedido. "
    "En breve un asesor de FARRO MENDEZ CORP se pondrá en contacto contigo."
)

# Plantillas dinámicas de mensajes
TEMPLATE_DISPONIBILIDAD = (
    "Contamos con {nombre} a S/ {precio:.2f} (stock disponible: {stock} unidades). "
    "¿Deseas comprar? Responde SI o NO."
)

TEMPLATE_METODOS_PAGO = (
    "Tu pedido #{pedido_id} fue registrado ({estado}).\n\n"
    "Métodos de pago disponibles:\n"
    "1) Yape / Plin al 999-888-777 (FARRO MENDEZ CORP)\n"
    "2) Transferencia BCP Cta: 191-00000000-0-00 CCI: 00219100000000000000\n"
    "3) Efectivo contra entrega (previa coordinación)\n\n"
    "Cuando realices el pago, envíanos la foto o PDF del comprobante para confirmar tu compra."
)

TEMPLATE_CONFIRMACION_VENTA = (
    "¡Pago confirmado con éxito! 🎉\n"
    "Tu pedido #{pedido_id} ha quedado PAGADO (Venta #{venta_id}).\n"
    "Monto acreditado: S/ {monto:.2f}.\n"
    "¡Muchas gracias por tu compra en FARRO MENDEZ CORPORATION S.A.C.! "
    "Coordinaremos la entrega de inmediato."
)
