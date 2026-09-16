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

async function* streamEvents(
  path: string,
  body: unknown,
  signal: AbortSignal,
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

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    for (const frame of parse(decoder.decode(value, { stream: true }))) {
      const event = toServerEvent(frame)
      if (event) yield event
    }
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
