import { useState } from 'react'

import { Composer } from './features/chat/Composer'
import { MessageList } from './features/chat/MessageList'
import { useChat } from './features/chat/useChat'
import { DevPanel } from './features/devpanel/DevPanel'
import { ConfirmationCard, HandoffNotice } from './features/hitl/ConfirmationCard'
import { Sidebar } from './features/sessions/Sidebar'

const DEV_PANEL_KEY = 'asesor.devpanel'

export default function App() {
  const {
    state,
    sessions,
    sessionId,
    send,
    retry,
    createSession,
    openSession,
    removeSession,
    answerConfirmation,
  } = useChat()
  const [showDevPanel, setShowDevPanel] = useState(readDevPanelPreference)

  function toggleDevPanel(next: boolean) {
    setShowDevPanel(next)
    try {
      localStorage.setItem(DEV_PANEL_KEY, String(next))
    } catch {
      // Preferencia accesoria: si el almacenamiento falla, solo no se recuerda.
    }
  }

  return (
    <div className="flex h-full">
      <Sidebar
        sessions={sessions}
        activeId={sessionId}
        onSelect={(id) => void openSession(id)}
        onCreate={() => void createSession()}
        onDelete={(id) => void removeSession(id)}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-edge px-4 py-3 sm:px-8">
          <h1 className="text-[15px] font-semibold">
            Luis <span className="font-normal text-muted">· asesor automotriz</span>
          </h1>
          {!showDevPanel && (
            <button
              type="button"
              onClick={() => toggleDevPanel(true)}
              className="rounded-lg border border-edge px-2.5 py-1 text-xs text-muted"
            >
              Panel dev
            </button>
          )}
        </header>

        {state.messages.length === 0 && (
          <p className="mx-auto mt-10 max-w-md px-6 text-center text-sm text-muted">
            Cuéntale a Luis qué buscas: para qué usarás el auto, qué carrocería te llama o
            cualquier duda técnica. Te orienta sin presionarte.
          </p>
        )}

        <MessageList
          messages={state.messages}
          activity={state.activity}
          streaming={state.streaming}
        />

        <div className="flex flex-col gap-3 border-t border-edge px-4 py-4 sm:px-8">
          {state.pendingConfirmation && (
            <ConfirmationCard
              confirmation={state.pendingConfirmation}
              busy={state.streaming}
              onAnswer={(approved) => void answerConfirmation(approved)}
            />
          )}

          {state.handoff && <HandoffNotice handoff={state.handoff} />}

          {state.error && (
            <div className="mx-auto flex w-full max-w-2xl items-center justify-between gap-3 rounded-lg border border-danger/50 bg-panel px-4 py-2.5">
              <p className="text-sm text-danger">{state.error.message}</p>
              {state.error.retryable && state.lastUserMessage && (
                <button
                  type="button"
                  onClick={() => void retry()}
                  className="shrink-0 rounded-lg border border-edge px-3 py-1.5 text-xs"
                >
                  Reintentar
                </button>
              )}
            </div>
          )}

          <Composer disabled={state.streaming} onSend={(text) => void send(text)} />
        </div>
      </main>

      {showDevPanel && (
        <DevPanel
          lead={state.lead}
          etapa={state.etapa}
          metrics={state.metrics}
          onClose={() => toggleDevPanel(false)}
        />
      )}
    </div>
  )
}

function readDevPanelPreference(): boolean {
  try {
    return localStorage.getItem(DEV_PANEL_KEY) !== 'false'
  } catch {
    return true
  }
}
