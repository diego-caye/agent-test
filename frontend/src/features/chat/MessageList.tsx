import { type KeyboardEvent, useEffect, useRef, useState } from 'react'
import { Pencil, RotateCcw, ThumbsDown, ThumbsUp } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

import type { Activity, Message } from './reducer'
import { TOOL_ACTIVITY } from './labels'

type Props = {
  messages: Message[]
  activity: Activity[]
  streaming: boolean
  // Se ofrece reintentar cuando el último turno no llegó a tener respuesta,
  // sea por un fallo en vivo o porque se cargó así una conversación vieja.
  retryable: boolean
  onRetry: () => void
  onEdit: (text: string) => void
  // El aviso de "el modelo local tarda" no tiene sentido con Gemini: ahí la
  // demora es de la API, no de cargar un modelo en la GPU de esta máquina.
  isLocalModel: boolean
  // trace_id del último turno completado (spec 08 §4): sin él no hay a qué
  // trace adjuntarle el score en Langfuse, así que no se ofrece feedback.
  traceId: string | null
  onFeedback: (traceId: string, score: 1 | -1) => void
}

export function MessageList({
  messages,
  activity,
  streaming,
  retryable,
  onRetry,
  onEdit,
  isLocalModel,
  traceId,
  onFeedback,
}: Props) {
  const endRef = useRef<HTMLDivElement>(null)
  const lastMessage = messages.at(-1)

  // El texto llega en un solo evento ya filtrado por L4, así que entre el envío
  // y la respuesta no hay burbuja que mostrar. Sin este indicador la interfaz
  // se ve congelada, y con un modelo local en frío eso son decenas de segundos.
  const pendingReply = streaming && lastMessage?.role !== 'agent'

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, activity, streaming])

  return (
    <div
      className="flex-1 overflow-y-auto px-4 py-6 sm:px-8"
      aria-live="polite"
      aria-label="Conversación"
    >
      <div className="mx-auto flex max-w-2xl flex-col gap-3">
        {messages.map((message) => (
          <Bubble
            key={message.id}
            message={message}
            // Solo el último mensaje puede necesitar reintento: es el único
            // que se quedó sin respuesta. Uno de en medio ya la tiene.
            showRetry={retryable && message.id === lastMessage?.id}
            retryDisabled={streaming}
            onRetry={onRetry}
            onEdit={onEdit}
            // Mismo criterio de "es el último": solo la respuesta más reciente
            // tiene sentido calificar, no una de en medio de la conversación.
            showFeedback={
              !streaming && message.role === 'agent' && message.id === lastMessage?.id && Boolean(traceId)
            }
            onFeedback={(score) => traceId && onFeedback(traceId, score)}
          />
        ))}

        {activity
          .filter((item) => !item.done)
          .map((item) => (
            <ActivityChip key={item.name} name={item.name} />
          ))}

        {pendingReply && <TypingIndicator isLocalModel={isLocalModel} />}

        <div ref={endRef} />
      </div>
    </div>
  )
}

function Bubble({
  message,
  showRetry,
  retryDisabled,
  onRetry,
  onEdit,
  showFeedback,
  onFeedback,
}: {
  message: Message
  showRetry: boolean
  retryDisabled: boolean
  onRetry: () => void
  onEdit: (text: string) => void
  showFeedback: boolean
  onFeedback: (score: 1 | -1) => void
}) {
  const isUser = message.role === 'user'
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(message.content)
  // Local: una vez calificado un turno no se puede cambiar de opinión, y el
  // estado no necesita sobrevivir a un refresh (no es información que el
  // usuario espere recuperar, a diferencia del propio mensaje).
  const [feedbackSent, setFeedbackSent] = useState<1 | -1 | null>(null)

  function sendFeedback(score: 1 | -1) {
    if (feedbackSent !== null) return
    setFeedbackSent(score)
    onFeedback(score)
  }

  function startEdit() {
    setDraft(message.content)
    setEditing(true)
  }

  function confirmEdit() {
    const trimmed = draft.trim()
    if (!trimmed) return
    setEditing(false)
    onEdit(trimmed)
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      confirmEdit()
    } else if (event.key === 'Escape') {
      setEditing(false)
    }
  }

  // La edición ocurre en el propio div del mensaje: la burbuja se convierte
  // en un campo editable en su lugar, en vez de mandar el texto al cuadro
  // principal de abajo. Al confirmar, esta misma burbuja queda con el texto
  // corregido (reducer 'edit-last-message') — no se agrega una aparte.
  if (editing) {
    return (
      <div className="flex flex-col items-end">
        <Textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          autoFocus
          rows={2}
          maxLength={2000}
          className="max-w-[92%] resize-none text-[15px] sm:max-w-[80%]"
        />
        <div className="mt-1 flex gap-1">
          <Button type="button" size="xs" onClick={confirmEdit} disabled={!draft.trim()}>
            Guardar y enviar
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={() => setEditing(false)}
            className="text-muted-foreground hover:text-foreground"
          >
            Cancelar
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={isUser ? 'flex flex-col items-end' : 'flex flex-col items-start'}>
      <p
        className={[
          'max-w-[92%] px-4 py-2.5 text-[15px] leading-relaxed whitespace-pre-wrap sm:max-w-[80%]',
          isUser
            ? 'rounded-[14px] rounded-br-[4px] bg-user-bubble'
            : 'rounded-[14px] rounded-bl-[4px] bg-card border',
          message.streaming ? 'caret' : '',
        ].join(' ')}
      >
        {message.content}
      </p>

      {/* Junto al mensaje concreto que se reenvía, no un botón grande y
          ambiguo al pie de la pantalla que no deja claro qué reintenta. */}
      {showRetry && (
        <div className="mt-1 flex gap-1">
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={onRetry}
            disabled={retryDisabled}
            className="text-muted-foreground hover:text-foreground"
          >
            <RotateCcw aria-hidden="true" />
            Reintentar
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="xs"
            onClick={startEdit}
            disabled={retryDisabled}
            className="text-muted-foreground hover:text-foreground"
          >
            <Pencil aria-hidden="true" />
            Editar
          </Button>
        </div>
      )}

      {showFeedback && (
        <div className="mt-1 flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            onClick={() => sendFeedback(1)}
            disabled={feedbackSent !== null}
            aria-label="Buena respuesta"
            title="Buena respuesta"
            className={
              feedbackSent === 1
                ? 'text-ok'
                : 'text-muted-foreground hover:text-foreground disabled:opacity-100'
            }
          >
            <ThumbsUp aria-hidden="true" />
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            onClick={() => sendFeedback(-1)}
            disabled={feedbackSent !== null}
            aria-label="Mala respuesta"
            title="Mala respuesta"
            className={
              feedbackSent === -1
                ? 'text-destructive'
                : 'text-muted-foreground hover:text-foreground disabled:opacity-100'
            }
          >
            <ThumbsDown aria-hidden="true" />
          </Button>
          {feedbackSent !== null && (
            <span className="text-muted-foreground text-xs">gracias por el feedback</span>
          )}
        </div>
      )}
    </div>
  )
}

const SLOW_REPLY_MS = 8000

function TypingIndicator({ isLocalModel }: { isLocalModel: boolean }) {
  const [slow, setSlow] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), SLOW_REPLY_MS)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="flex flex-col items-start gap-1.5" role="status" aria-label="Luis está escribiendo">
      <span className="inline-flex items-center gap-1.5 rounded-[14px] rounded-bl-[4px] bg-card border px-4 py-3">
        <Dot delay="0ms" />
        <Dot delay="160ms" />
        <Dot delay="320ms" />
      </span>
      {slow && (
        <span className="px-1 text-xs text-muted-foreground">
          {/* "el modelo local tarda" no tiene sentido con Gemini: ahí la
              demora es de la API (o de un reintento por 429), no de cargar
              un modelo en la GPU de esta máquina. Tampoco se afirma que es
              "la primera vez" para el caso local: no hay forma de saberlo
              desde aquí, y decirlo en la quinta llamada del modelo ya
              caliente confunde más de lo que tranquiliza. */}
          {isLocalModel
            ? 'Los modelos locales a veces tardan más de lo normal…'
            : 'Esto puede tardar unos segundos…'}
        </span>
      )}
    </div>
  )
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      // bg-muted-foreground, no bg-muted: en modo oscuro --muted y --card
      // son literalmente el mismo gris (#171717), así que los puntos quedaban
      // invisibles sobre la burbuja — solo se veía el borde vacío.
      className="size-1.5 animate-bounce rounded-full bg-muted-foreground"
      style={{ animationDelay: delay }}
      aria-hidden="true"
    />
  )
}

function ActivityChip({ name }: { name: string }) {
  return (
    <div className="flex justify-start" role="status">
      <Badge variant="secondary" className="bg-accent-soft text-muted-foreground h-auto py-1.5">
        <span className="bg-primary size-1.5 animate-pulse rounded-full" aria-hidden="true" />
        {TOOL_ACTIVITY[name] ?? 'Trabajando…'}
      </Badge>
    </div>
  )
}
