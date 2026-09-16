import { MessageSquarePlus, Trash2 } from 'lucide-react'

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'

import type { SessionSummary } from '../../api/types'
import { ETAPA_LABEL } from '../chat/labels'

type Props = {
  sessions: SessionSummary[]
  activeId: string | null
  onSelect: (sessionId: string) => void
  onCreate: () => void
  onDelete: (sessionId: string) => void
}

export function Sidebar({ sessions, activeId, onSelect, onCreate, onDelete }: Props) {
  return (
    <nav className="bg-sidebar border-sidebar-border hidden w-60 shrink-0 flex-col border-r md:flex">
      <div className="p-3">
        <Button type="button" onClick={onCreate} className="h-10 w-full font-semibold">
          <MessageSquarePlus aria-hidden="true" />
          Nueva conversación
        </Button>
      </div>

      <ScrollArea className="flex-1">
        <ul className="px-2 pb-3">
          {sessions.length === 0 && (
            <li className="text-muted-foreground px-2 py-3 text-xs">
              Todavía no tienes conversaciones.
            </li>
          )}

          {sessions.map((session) => {
            const isActive = session.session_id === activeId

            return (
              <li key={session.session_id} className="group relative">
                <button
                  type="button"
                  onClick={() => onSelect(session.session_id)}
                  aria-current={isActive ? 'true' : undefined}
                  className={[
                    'w-full rounded-lg py-2 pr-9 pl-3 text-left transition-colors',
                    isActive ? 'bg-sidebar-accent' : 'hover:bg-sidebar-accent/60',
                  ].join(' ')}
                >
                  {/* El título lo genera el modelo ligero en segundo plano; hasta
                      que llega, la conversación ya tiene que poder distinguirse. */}
                  <span className="block truncate text-sm">
                    {session.titulo || 'Conversación nueva'}
                  </span>
                  <span className="text-muted-foreground block truncate text-[11px]">
                    {new Date(session.last_update_time).toLocaleString('es-PE', {
                      day: '2-digit',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                    {' · '}
                    {ETAPA_LABEL[session.etapa] ?? session.etapa}
                  </span>
                </button>

                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-xs"
                      aria-label="Eliminar conversación"
                      title="Eliminar conversación"
                      className="text-muted-foreground hover:text-destructive absolute top-2.5 right-2 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                    >
                      <Trash2 aria-hidden="true" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>¿Eliminar esta conversación?</AlertDialogTitle>
                      <AlertDialogDescription>
                        Se borran los mensajes de «{session.titulo || 'Conversación nueva'}». Tu
                        ficha de datos no se pierde: vive a nivel de usuario, no de conversación.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancelar</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => onDelete(session.session_id)}
                        className="bg-destructive/10 text-destructive hover:bg-destructive/20"
                      >
                        Eliminar
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </li>
            )
          })}
        </ul>
      </ScrollArea>
    </nav>
  )
}
