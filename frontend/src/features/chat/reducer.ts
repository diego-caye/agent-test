import type { Etapa, LeadDto, ServerEvent, TurnMetrics } from '../../api/types'

export type Message = {
  id: string
  role: 'user' | 'agent'
  content: string
  streaming: boolean
}

export type Activity = { name: string; done: boolean }

export type Confirmation = {
  confirmation_id: string
  motivo: string
  resumen: string
  canal_preferido: string | null
}

export type Handoff = { ticket: string; ya_existia: boolean }

export type ChatState = {
  messages: Message[]
  activity: Activity[]
  pendingConfirmation: Confirmation | null
  handoff: Handoff | null
  lead: LeadDto | null
  etapa: Etapa
  metrics: TurnMetrics | null
  streaming: boolean
  error: { message: string; retryable: boolean } | null
  lastUserMessage: string | null
}

export const initialChatState: ChatState = {
  messages: [],
  activity: [],
  pendingConfirmation: null,
  handoff: null,
  lead: null,
  etapa: 'NUEVO',
  metrics: null,
  streaming: false,
  error: null,
  lastUserMessage: null,
}

export type ChatAction =
  | { type: 'reset' }
  | { type: 'load'; messages: Message[]; lead: LeadDto | null; etapa: Etapa }
  | { type: 'user-sent'; content: string }
  | { type: 'turn-start' }
  | { type: 'server'; event: ServerEvent }
  | { type: 'turn-failed'; message: string }

const AGENT_DRAFT_ID = 'agent-draft'

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'reset':
      return initialChatState

    case 'load':
      return {
        ...initialChatState,
        messages: action.messages,
        lead: action.lead,
        etapa: action.etapa,
      }

    case 'user-sent':
      return {
        ...state,
        error: null,
        handoff: null,
        lastUserMessage: action.content,
        messages: [
          ...state.messages,
          {
            id: `user-${state.messages.length}`,
            role: 'user',
            content: action.content,
            streaming: false,
          },
        ],
      }

    case 'turn-start':
      return { ...state, streaming: true, error: null, activity: [] }

    case 'turn-failed':
      return {
        ...state,
        streaming: false,
        activity: [],
        error: { message: action.message, retryable: true },
        messages: state.messages.filter((message) => message.id !== AGENT_DRAFT_ID),
      }

    case 'server':
      return applyServerEvent(state, action.event)
  }
}

function applyServerEvent(state: ChatState, event: ServerEvent): ChatState {
  switch (event.type) {
    case 'message.delta':
      return { ...state, messages: appendDelta(state.messages, event.delta) }

    case 'message.completed':
      return {
        ...state,
        streaming: false,
        activity: [],
        messages: state.messages.map((message) =>
          message.id === AGENT_DRAFT_ID
            ? { ...message, id: event.message_id || message.id, streaming: false }
            : message,
        ),
        metrics: {
          latency_ms: event.latency_ms,
          tokens_in: event.tokens_in,
          tokens_out: event.tokens_out,
          model: event.model,
          trace_id: event.trace_id,
        },
      }

    case 'tool.started':
      return { ...state, activity: [...state.activity, { name: event.name, done: false }] }

    case 'tool.finished':
      return {
        ...state,
        activity: state.activity.map((item) =>
          item.name === event.name && !item.done ? { ...item, done: true } : item,
        ),
      }

    case 'lead.updated':
      return { ...state, lead: event.lead, etapa: event.etapa }

    case 'hitl.confirmation_required':
      return {
        ...state,
        streaming: false,
        activity: [],
        pendingConfirmation: {
          confirmation_id: event.confirmation_id,
          motivo: event.motivo,
          resumen: event.resumen,
          canal_preferido: event.canal_preferido,
        },
      }

    case 'handoff.created':
      return {
        ...state,
        pendingConfirmation: null,
        handoff: { ticket: event.ticket, ya_existia: event.ya_existia },
      }

    case 'guardrail.triggered':
      return state

    case 'error':
      return {
        ...state,
        streaming: false,
        activity: [],
        error: { message: event.message, retryable: event.retryable },
      }
  }
}

function appendDelta(messages: Message[], delta: string): Message[] {
  const last = messages[messages.length - 1]

  if (last && last.id === AGENT_DRAFT_ID) {
    return [...messages.slice(0, -1), { ...last, content: last.content + delta }]
  }

  return [
    ...messages,
    { id: AGENT_DRAFT_ID, role: 'agent', content: delta, streaming: true },
  ]
}

export function clearConfirmation(state: ChatState): ChatState {
  return { ...state, pendingConfirmation: null }
}
