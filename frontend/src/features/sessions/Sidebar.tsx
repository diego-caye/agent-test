import type { SessionSummary } from '../../api/types'
import { ETAPA_LABEL } from '../chat/labels'

type Props = {
  sessions: SessionSummary[]
  activeId: string | null
  onSelect: (sessionId: string) => void
  onCreate: () => void
}

export function Sidebar({ sessions, activeId, onSelect, onCreate }: Props) {
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
          return (
            <li key={session.session_id}>
              <button
                type="button"
                onClick={() => onSelect(session.session_id)}
                aria-current={isActive ? 'true' : undefined}
                className={[
                  'w-full rounded-lg px-3 py-2 text-left',
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
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
