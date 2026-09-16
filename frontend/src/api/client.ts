import { createSseParser, toServerEvent } from './sse'
import type {
  LeadResponse,
  MessageDto,
  ModelOption,
  ServerEvent,
  SessionSummary,
} from './types'

const USER_ID_KEY = 'asesor.user_id'

export function getUserId(): string {
  try {
    const stored = localStorage.getItem(USER_ID_KEY)
    if (stored) return stored
    const fresh = crypto.randomUUID()
    localStorage.setItem(USER_ID_KEY, fresh)
    return fresh
  } catch {
    // Ventana privada o almacenamiento bloqueado: la sesión vive solo en memoria.
    return crypto.randomUUID()
  }
}

const userId = getUserId()

// El backend acumula la respuesta del modelo y no manda nada por el cable
// hasta que el turno termina (spec 02 §4: L4 necesita ver el texto completo).
// Eso significa que, para un turno sin tools, la conexión puede quedar en
// silencio total mientras dura la generación — y con Gemini se ha medido más
// de 2 minutos en un solo turno con reintentos de proveedor. El plazo tiene
// que cubrir eso con margen; lo que corta de verdad es una conexión colgada
// (el proceso del modelo murió, Docker perdió la red), no un turno lento.
const STREAM_IDLE_TIMEOUT_MS = 180_000

export class StreamIdleTimeoutError extends Error {
  constructor() {
    super('El asesor no respondió a tiempo.')
    this.name = 'StreamIdleTimeoutError'
  }
}

async function readWithIdleTimeout(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  timeoutMs: number,
): Promise<ReadableStreamReadResult<Uint8Array>> {
  let timer: ReturnType<typeof setTimeout> | undefined
  const read = reader.read()
  // Si gana el timeout, más tarde cancelamos el reader y esa lectura pendiente
  // puede terminar rechazando igual: sin este no-op, Node la reporta como
  // "unhandled rejection" aunque el resultado de la carrera ya se haya resuelto.
  read.catch(() => {})
  try {
    return await Promise.race([
      read,
      new Promise<never>((_, reject) => {
        timer = setTimeout(() => reject(new StreamIdleTimeoutError()), timeoutMs)
      }),
    ])
  } finally {
    clearTimeout(timer)
  }
}

function headers(): HeadersInit {
  return { 'Content-Type': 'application/json', 'X-User-Id': userId }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: headers() })
  if (!response.ok) throw new Error(`${init?.method ?? 'GET'} ${path} → ${response.status}`)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  createSession: () => request<{ session_id: string }>('/api/v1/sessions', { method: 'POST' }),
  listSessions: () => request<SessionSummary[]>('/api/v1/sessions'),
  listMessages: (sessionId: string) =>
    request<MessageDto[]>(`/api/v1/sessions/${sessionId}/messages`),
  getLead: (sessionId: string) => request<LeadResponse>(`/api/v1/sessions/${sessionId}/lead`),
  deleteSession: (sessionId: string) =>
    request<void>(`/api/v1/sessions/${sessionId}`, { method: 'DELETE' }),
  listModels: () => request<ModelOption[]>('/api/v1/models'),
}

// Exportada solo para que el test del timeout pueda pasar un plazo corto y
// usar timers reales, en vez de esperar 3 minutos o lidiar con temporizadores
// falsos compitiendo dentro de un Promise.race.
export async function* streamEvents(
  path: string,
  body: unknown,
  signal: AbortSignal,
  idleTimeoutMs = STREAM_IDLE_TIMEOUT_MS,
): AsyncGenerator<ServerEvent> {
  const response = await fetch(path, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body),
    signal,
  })

  if (!response.ok || !response.body) {
    throw new Error(`POST ${path} → ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const parse = createSseParser()

  try {
    while (true) {
      const { done, value } = await readWithIdleTimeout(reader, idleTimeoutMs)
      if (done) break

      for (const frame of parse(decoder.decode(value, { stream: true }))) {
        const event = toServerEvent(frame)
        if (event) yield event
      }
    }
  } catch (error) {
    // El timeout no cierra la conexión por sí solo: sin esto, la petición
    // colgada sigue viva en el navegador aunque ya hayamos dejado de leerla.
    await reader.cancel().catch(() => {})
    throw error
  }
}

export function sendMessage(
  sessionId: string,
  message: string,
  modelId: string | null,
  signal: AbortSignal,
): AsyncGenerator<ServerEvent> {
  return streamEvents(
    "/api/v1/chat/stream",
    { session_id: sessionId, message, model_id: modelId },
    signal,
  )
}

export function sendConfirmation(
  sessionId: string,
  confirmationId: string,
  approved: boolean,
  modelId: string | null,
  signal: AbortSignal,
): AsyncGenerator<ServerEvent> {
  return streamEvents(
    '/api/v1/chat/confirmations',
    { session_id: sessionId, confirmation_id: confirmationId, approved, model_id: modelId },
    signal,
  )
}
