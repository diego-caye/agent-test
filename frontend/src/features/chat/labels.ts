export const TOOL_ACTIVITY: Record<string, string> = {
  search_knowledge_base: 'Consultando la guía técnica…',
  guardar_lead: 'Guardando tus datos…',
  solicitar_contacto_humano: 'Preparando tu solicitud…',
}

export const MOTIVO_LABEL: Record<string, string> = {
  TEST_DRIVE: 'agendar un test drive',
  COTIZACION_FORMAL: 'una cotización formal',
  COMPRA_INMEDIATA: 'avanzar con la compra',
  DISCONFORMIDAD: 'atender un reclamo',
  FUERA_DE_ALCANCE: 'hablar con un especialista',
}

export const CANAL_LABEL: Record<string, string> = {
  WHATSAPP: 'WhatsApp',
  LLAMADA: 'llamada',
  EMAIL: 'correo',
  CHAT: 'chat',
}

export const ETAPA_LABEL: Record<string, string> = {
  NUEVO: 'Nuevo',
  DESCUBRIMIENTO: 'Descubrimiento',
  INTERES_CONCRETO: 'Interés concreto',
  DERIVACION_PENDIENTE: 'Derivación pendiente',
  DERIVADO: 'Derivado',
}

export const LEAD_FIELDS: { key: string; label: string }[] = [
  { key: 'nombre', label: 'Nombre' },
  { key: 'uso_principal', label: 'Uso' },
  { key: 'tipo_vehiculo_interes', label: 'Carrocería' },
  { key: 'motorizacion_interes', label: 'Motor' },
  { key: 'nivel_interes', label: 'Interés' },
  { key: 'canal_preferido', label: 'Canal' },
]
