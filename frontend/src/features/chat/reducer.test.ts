import { describe, expect, it } from 'vitest'

import type { ServerEvent } from '../../api/types'
import { type ChatState, chatReducer, initialChatState } from './reducer'

function apply(state: ChatState, ...events: ServerEvent[]): ChatState {
  return events.reduce((acc, event) => chatReducer(acc, { type: 'server', event }), state)
}

describe('chatReducer', () => {
  it('acumula los deltas en una sola burbuja del agente', () => {
    const state = apply(
      initialChatState,
      { type: 'message.delta', delta: 'Hola ' },
      { type: 'message.delta', delta: 'Diego' },
    )

    expect(state.messages).toHaveLength(1)
    expect(state.messages[0]?.content).toBe('Hola Diego')
    expect(state.messages[0]?.streaming).toBe(true)
  })

  it('cierra la burbuja y guarda las métricas al completar el turno', () => {
    const streamed = apply(initialChatState, { type: 'message.delta', delta: 'Hola' })
    const state = apply(streamed, {
      type: 'message.completed',
      message_id: 'evt-1',
      trace_id: 'trace-1',
      latency_ms: 340,
      tokens_in: 1200,
      tokens_out: 80,
      model: 'gemini-3.8-flash',
    })

    expect(state.messages[0]?.streaming).toBe(false)
    expect(state.messages[0]?.id).toBe('evt-1')
    expect(state.streaming).toBe(false)
    expect(state.metrics?.latency_ms).toBe(340)
    expect(state.metrics?.trace_id).toBe('trace-1')
  })

  it('no mezcla el mensaje del usuario con el del agente', () => {
    const sent = chatReducer(initialChatState, { type: 'user-sent', content: 'Busco un SUV' })
    const state = apply(sent, { type: 'message.delta', delta: 'Buena elección' })

    expect(state.messages.map((m) => m.role)).toEqual(['user', 'agent'])
    expect(state.messages[0]?.content).toBe('Busco un SUV')
  })

  it('marca la actividad de una tool como terminada', () => {
    const state = apply(
      initialChatState,
      { type: 'tool.started', name: 'guardar_lead' },
      { type: 'tool.finished', name: 'guardar_lead', status: 'ok', duration_ms: 12 },
    )

    expect(state.activity).toEqual([{ name: 'guardar_lead', done: true }])
  })

  it('limpia la actividad cuando el turno termina', () => {
    const state = apply(
      initialChatState,
      { type: 'tool.started', name: 'search_knowledge_base' },
      {
        type: 'message.completed',
        message_id: 'e',
        trace_id: 't',
        latency_ms: 1,
        tokens_in: 1,
        tokens_out: 1,
        model: null,
      },
    )

    expect(state.activity).toEqual([])
  })

  it('actualiza ficha y etapa con lead.updated', () => {
    const state = apply(initialChatState, {
      type: 'lead.updated',
      lead: { nombre: 'Diego', consentimiento_contacto: false },
      etapa: 'DESCUBRIMIENTO',
    })

    expect(state.lead?.nombre).toBe('Diego')
    expect(state.etapa).toBe('DESCUBRIMIENTO')
  })

  it('deja la confirmación pendiente y detiene el streaming', () => {
    const state = apply(initialChatState, {
      type: 'hitl.confirmation_required',
      confirmation_id: 'conf-1',
      motivo: 'TEST_DRIVE',
      resumen: 'Quiere agendar un test drive',
      canal_preferido: 'WHATSAPP',
      urgencia: null,
    })

    expect(state.pendingConfirmation?.confirmation_id).toBe('conf-1')
    expect(state.streaming).toBe(false)
  })

  it('reemplaza la confirmación por el handoff creado', () => {
    const pending = apply(initialChatState, {
      type: 'hitl.confirmation_required',
      confirmation_id: 'conf-1',
      motivo: 'TEST_DRIVE',
      resumen: 'x',
      canal_preferido: null,
      urgencia: null,
    })
    const state = apply(pending, {
      type: 'handoff.created',
      handoff_id: 1,
      ticket: 'TICK-00001',
      motivo: 'TEST_DRIVE',
      status: 'OPEN',
      ya_existia: false,
    })

    expect(state.pendingConfirmation).toBeNull()
    expect(state.handoff?.ticket).toBe('TICK-00001')
  })

  it('expone el error y recuerda el último mensaje para reintentar', () => {
    const sent = chatReducer(initialChatState, { type: 'user-sent', content: 'hola' })
    const state = apply(sent, {
      type: 'error',
      code: 'UPSTREAM_UNAVAILABLE',
      message: 'No pudimos conectar con el asesor.',
      retryable: true,
    })

    expect(state.error?.retryable).toBe(true)
    expect(state.lastUserMessage).toBe('hola')
    expect(state.streaming).toBe(false)
  })

  it('descarta la burbuja a medio escribir si el turno falla', () => {
    const streaming = apply(initialChatState, { type: 'message.delta', delta: 'a medio' })
    const state = chatReducer(streaming, { type: 'turn-failed', message: 'se cayó' })

    expect(state.messages).toEqual([])
    expect(state.error?.message).toBe('se cayó')
  })

  it('ofrece reintentar al cargar una conversación que terminó sin respuesta', () => {
    const state = chatReducer(initialChatState, {
      type: 'load',
      messages: [
        { id: 'stored-0', role: 'user', content: 'hola', streaming: false },
        { id: 'stored-1', role: 'user', content: 'q tal?', streaming: false },
      ],
      lead: null,
      etapa: 'NUEVO',
      unansweredMessage: 'q tal?',
    })

    expect(state.error?.retryable).toBe(true)
    expect(state.lastUserMessage).toBe('q tal?')
    // El mensaje sigue en la lista tal cual venía del backend: la señal de
    // "hay que reintentar" es aparte, no reemplaza el historial.
    expect(state.messages).toHaveLength(2)
  })

  it('no muestra el aviso de reintento si el último mensaje ya tiene respuesta', () => {
    const state = chatReducer(initialChatState, {
      type: 'load',
      messages: [
        { id: 'stored-0', role: 'user', content: 'hola', streaming: false },
        { id: 'stored-1', role: 'agent', content: '¡Hola!', streaming: false },
      ],
      lead: null,
      etapa: 'NUEVO',
      unansweredMessage: null,
    })

    expect(state.error).toBeNull()
    expect(state.lastUserMessage).toBeNull()
  })
})
