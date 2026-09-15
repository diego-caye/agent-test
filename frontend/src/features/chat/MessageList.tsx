import { useEffect, useRef } from 'react'

import type { Activity, Message } from './reducer'
import { TOOL_ACTIVITY } from './labels'

type Props = {
  messages: Message[]
  activity: Activity[]
}

export function MessageList({ messages, activity }: Props) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, activity])

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
            : 'rounded-[14px] rounded-bl-[4px] bg-panel',
          message.streaming ? 'caret' : '',
        ].join(' ')}
      >
        {message.content}
      </p>
    </div>
  )
}

function ActivityChip({ name }: { name: string }) {
  return (
    <div className="flex justify-start" role="status">
      <span className="inline-flex items-center gap-2 rounded-full bg-accent-soft px-3 py-1.5 text-xs font-medium text-muted">
        <span className="size-1.5 rounded-full bg-accent" aria-hidden="true" />
        {TOOL_ACTIVITY[name] ?? 'Trabajando…'}
      </span>
    </div>
  )
}
