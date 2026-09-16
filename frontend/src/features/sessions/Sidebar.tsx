import { useState } from 'react'

import type { SessionSummary } from '../../api/types'
import { ETAPA_LABEL } from '../chat/labels'

function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M2.5 4h11M6.5 4V2.5h3V4M4 4l.6 9a1 1 0 0 0 1 .9h4.8a1 1 0 0 0 1-.9L12 4M6.5 7v4M9.5 7v4"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

type Props = {
  sessions: SessionSummary[]
  activeId: string | null
  onSelect: (sessionId: string) => void
  onCreate: () => void
  onDelete: (sessionId: string) => void
}

export function Sidebar({ sessions, activeId, onSelect, onCreate, onDelete }: Props) {
  const [confirming, setConfirming] = useState<string | null>(null)
  return (
    <nav className="hidden w-60 shrink-0 flex-col border-r border-edge bg-panel md:flex">
      <div className="p-3">
        <button
          type="button"
          onClick={onCreate}
          className="min-h-10 w-full rounded-lg bg-accent px-3 text-sm font-semibold text-accent-ink"
        >
          Nueva conversación
        </button>
      </div>

      <ul className="flex-1 overflow-y-auto px-2 pb-3">
        {sessions.length === 0 && (
          <li className="px-2 py-3 text-xs text-muted">Todavía no tienes conversaciones.</li>
        )}

        {sessions.map((session) => {
          const isActive = session.session_id === activeId
          const isConfirming = confirming === session.session_id

          return (
            <li key={session.session_id} className="group relative">
              <button
                type="button"
                onClick={() => onSelect(session.session_id)}
                aria-current={isActive ? 'true' : undefined}
                className={[
                  'w-full rounded-lg py-2 pr-9 pl-3 text-left',
                  isActive ? 'bg-raised' : 'hover:bg-raised/60',
                ].join(' ')}
              >
                <span className="block truncate text-sm">
                  {new Date(session.last_update_time).toLocaleString('es-PE', {
                    day: '2-digit',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
                <span className="block text-[11px] text-muted">
                  {ETAPA_LABEL[session.etapa] ?? session.etapa}
                </span>
              </button>

              {isConfirming ? (
                <span className="absolute top-1.5 right-1 flex gap-1">
                  <button
                    type="button"
                    onClick={() => {
                      setConfirming(null)
                      onDelete(session.session_id)
                    }}
                    className="rounded bg-danger px-1.5 py-1 text-[11px] font-medium text-surface"
                  >
                    Borrar
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirming(null)}
                    className="rounded border border-edge px-1.5 py-1 text-[11px] text-muted"
                  >
                    No
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirming(session.session_id)}
                  aria-label="Eliminar conversación"
                  title="Eliminar conversación"
                  className="absolute top-2.5 right-2 rounded p-1 text-muted opacity-0 group-hover:opacity-100 focus-visible:opacity-100 hover:text-danger"
                >
                  <TrashIcon />
                </button>
              )}
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
