import { useCallback, useEffect, useReducer, useRef, useState } from 'react'

import { api, sendConfirmation, sendMessage } from '../../api/client'
import type { ModelOption, ServerEvent, SessionSummary } from '../../api/types'
import { type Message, chatReducer, initialChatState } from './reducer'

const GENERIC_ERROR = 'No pudimos conectar con el asesor. Reintenta en unos segundos.'

const MODEL_KEY = 'asesor.model_id'

function readStoredModel(): string | null {
  try {
    return localStorage.getItem(MODEL_KEY)
  } catch {
    return null
  }
}

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, initialChatState)
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [models, setModels] = useState<ModelOption[]>([])
  const [modelId, setModelIdState] = useState<string | null>(readStoredModel)
  const abortRef = useRef<AbortController | null>(null)

  const setModelId = useCallback((id: string) => {
    setModelIdState(id)
    try {
      localStorage.setItem(MODEL_KEY, id)
    } catch {
      // Preferencia accesoria: si el almacenamiento falla, solo no se recuerda.
    }
  }, [])

  const refreshSessions = useCallback(async () => {
    try {
      setSessions(await api.listSessions())
    } catch {
      // La lista es accesoria: si falla, el chat sigue usable.
    }
  }, [])

  const consume = useCallback(
    async (events: AsyncGenerator<ServerEvent>) => {
      dispatch({ type: 'turn-start' })
      try {
        for await (const event of events) {
          dispatch({ type: 'server', event })
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') return
        dispatch({ type: 'turn-failed', message: GENERIC_ERROR })
      }
    },
    [dispatch],
  )

  const createSession = useCallback(async () => {
    abortRef.current?.abort()
    const { session_id } = await api.createSession()
    setSessionId(session_id)
    dispatch({ type: 'reset' })
    await refreshSessions()
    return session_id
  }, [refreshSessions])

  const openSession = useCallback(async (id: string) => {
    abortRef.current?.abort()
    setSessionId(id)

    const [messages, lead] = await Promise.all([api.listMessages(id), api.getLead(id)])
    dispatch({
      type: 'load',
      messages: messages.map(
        (message, index): Message => ({
          id: `stored-${index}`,
          role: message.role === 'user' ? 'user' : 'agent',
          content: message.content,
          streaming: false,
        }),
      ),
      lead: lead.lead,
      etapa: lead.etapa as never,
    })
  }, [])

  const send = useCallback(
    async (text: string) => {
      const id = sessionId ?? (await createSession())
      dispatch({ type: 'user-sent', content: text })

      const controller = new AbortController()
      abortRef.current = controller
      await consume(sendMessage(id, text, modelId, controller.signal))
      await refreshSessions()
    },
    [sessionId, modelId, createSession, consume, refreshSessions],
  )

  const answerConfirmation = useCallback(
    async (approved: boolean) => {
      const pending = state.pendingConfirmation
      if (!sessionId || !pending) return

      const controller = new AbortController()
      abortRef.current = controller
      await consume(
        sendConfirmation(sessionId, pending.confirmation_id, approved, modelId, controller.signal),
      )
      await refreshSessions()
    },
    [sessionId, state.pendingConfirmation, modelId, consume, refreshSessions],
  )

  const removeSession = useCallback(
    async (id: string) => {
      await api.deleteSession(id)

      if (id === sessionId) {
        abortRef.current?.abort()
        setSessionId(null)
        dispatch({ type: 'reset' })
      }

      await refreshSessions()
    },
    [sessionId, refreshSessions],
  )

  const retry = useCallback(async () => {
    if (state.lastUserMessage) await send(state.lastUserMessage)
  }, [state.lastUserMessage, send])

  useEffect(() => {
    void refreshSessions()

    void api
      .listModels()
      .then((available) => {
        setModels(available)
        // Si el modelo recordado ya no está en el catálogo (o dejó de estar
        // configurado), se cae al que el backend marca por defecto.
        setModelIdState((current) => {
          const usable = available.find((m) => m.id === current && m.available)
          return usable?.id ?? available.find((m) => m.is_default)?.id ?? null
        })
      })
      .catch(() => setModels([]))

    return () => abortRef.current?.abort()
  }, [refreshSessions])

  return {
    state,
    sessions,
    sessionId,
    models,
    modelId,
    setModelId,
    send,
    retry,
    createSession,
    openSession,
    removeSession,
    answerConfirmation,
  }
}
