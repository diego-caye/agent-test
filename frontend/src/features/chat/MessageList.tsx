import { useEffect, useRef, useState } from 'react'

import { Badge } from '@/components/ui/badge'

import type { Activity, Message } from './reducer'
import { TOOL_ACTIVITY } from './labels'

type Props = {
  messages: Message[]
  activity: Activity[]
  streaming: boolean
}

export function MessageList({ messages, activity, streaming }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  // El texto llega en un solo evento ya filtrado por L4, así que entre el envío
  // y la respuesta no hay burbuja que mostrar. Sin este indicador la interfaz
  // se ve congelada, y con un modelo local en frío eso son decenas de segundos.
  const pendingReply = streaming && messages.at(-1)?.role !== 'agent'

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
          <Bubble key={message.id} message={message} />
        ))}

        {activity
          .filter((item) => !item.done)
          .map((item) => (
            <ActivityChip key={item.name} name={item.name} />
          ))}

        {pendingReply && <TypingIndicator />}

        <div ref={endRef} />
      </div>
    </div>
  )
}

function Bubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={isUser ? 'flex justify-end' : 'flex justify-start'}>
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
    </div>
  )
}

const SLOW_REPLY_MS = 8000

function TypingIndicator() {
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
          El modelo local está cargando, suele tardar la primera vez…
        </span>
      )}
    </div>
  )
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="size-1.5 animate-bounce rounded-full bg-muted"
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
