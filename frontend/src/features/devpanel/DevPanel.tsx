import { useEffect, useState } from 'react'
import { ThumbsDown, ThumbsUp, X } from 'lucide-react'

import { api } from '../../api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Sidebar, SidebarContent, SidebarHeader } from '@/components/ui/sidebar'

import type { FeedbackDto, LeadDto, TurnMetrics } from '../../api/types'
import { ETAPA_LABEL, LEAD_FIELDS } from '../chat/labels'

type Props = {
  lead: LeadDto | null
  etapa: string
  metrics: TurnMetrics | null
  onClose: () => void
  onOpenSession: (sessionId: string) => void
}

const ADMIN_TOKEN_KEY = 'asesor.admin_token'

const LANGFUSE_PROJECT = import.meta.env['VITE_LANGFUSE_PROJECT_ID'] as string | undefined
// Sin esto, un plan que no vive en el cloud.langfuse.com por defecto (p. ej.
// una region HIPAA con host propio) arma el link contra el host equivocado y
// se queda "Loading..." para siempre (visto en vivo).
const LANGFUSE_HOST =
  (import.meta.env['VITE_LANGFUSE_HOST'] as string | undefined) || 'https://cloud.langfuse.com'

export function DevPanel({ lead, etapa, metrics, onClose, onOpenSession }: Props) {
  const record = (lead ?? {}) as Record<string, unknown>

  return (
    <Sidebar side="right" collapsible="offcanvas">
      <SidebarHeader className="flex-row items-center justify-between p-4 pb-0">
        <Label>Panel dev</Label>
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          onClick={onClose}
          aria-label="Ocultar panel dev"
          className="text-muted-foreground hover:text-foreground"
        >
          <X aria-hidden="true" />
        </Button>
      </SidebarHeader>

      <SidebarContent className="gap-4 p-4 pt-2">
        <Separator />

        <section>
          <Label>Etapa</Label>
          <Badge variant="secondary" className="mt-1.5">
            {ETAPA_LABEL[etapa] ?? etapa}
          </Badge>
        </section>

        <section>
          <Label>Ficha del lead</Label>
          <dl className="mt-1.5 flex flex-col gap-1">
            {LEAD_FIELDS.map((field) => {
              const value = record[field.key]
              return (
                <div key={field.key} className="flex justify-between gap-2 text-xs">
                  <dt className="text-muted-foreground">{field.label}</dt>
                  <dd className={value ? 'text-foreground' : 'text-muted-foreground'}>
                    {typeof value === 'string' && value ? value : '—'}
                  </dd>
                </div>
              )
            })}
          </dl>
        </section>

        <section>
          <Label>Último turno</Label>
          {metrics ? (
            <dl className="mt-1.5 flex flex-col gap-1 text-xs">
              <Row label="Latencia" value={`${metrics.latency_ms} ms`} />
              <Row label="Tokens in" value={String(metrics.tokens_in)} />
              <Row label="Tokens out" value={String(metrics.tokens_out)} />
              <Row label="Modelo" value={metrics.model ?? '—'} />
            </dl>
          ) : (
            <p className="text-muted-foreground mt-1.5 text-xs">Sin turnos todavía.</p>
          )}

          {metrics && LANGFUSE_PROJECT && (
            <Button asChild variant="link" size="xs" className="mt-2 px-0">
              <a
                href={`${LANGFUSE_HOST}/project/${LANGFUSE_PROJECT}/traces/${metrics.trace_id}`}
                target="_blank"
                rel="noreferrer"
              >
                Ver traza en Langfuse
              </a>
            </Button>
          )}
        </section>

        <Separator />

        <FeedbackSection onOpenSession={onOpenSession} />
      </SidebarContent>
    </Sidebar>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-muted-foreground text-[11px] font-medium tracking-[0.04em] uppercase">
      {children}
    </h2>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="tabular">{value}</dd>
    </div>
  )
}

function readStoredAdminToken(): string {
  try {
    return localStorage.getItem(ADMIN_TOKEN_KEY) ?? ''
  } catch {
    return ''
  }
}

// Sección aparte, gated por admin_token (spec 02/03, mismo mecanismo que
// /handoffs): cruza sesiones ajenas, así que no puede vivir detrás del
// X-User-Id normal del usuario que tiene el panel dev abierto.
function FeedbackSection({ onOpenSession }: { onOpenSession: (sessionId: string) => void }) {
  const [token, setToken] = useState(readStoredAdminToken)
  const [tokenDraft, setTokenDraft] = useState('')
  const [entries, setEntries] = useState<FeedbackDto[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Si ya se recordó un token de una vez anterior, carga sola al abrir el
  // panel dev, en vez de dejar el clic de "Actualizar" como único disparador.
  useEffect(() => {
    if (token) void load(token)
    // Solo al montar: token cambia dentro de load() mismo, no hay que reaccionar a eso.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function load(withToken: string) {
    setLoading(true)
    setError(null)
    try {
      const list = await api.listFeedback(withToken)
      setEntries(list)
      try {
        localStorage.setItem(ADMIN_TOKEN_KEY, withToken)
      } catch {
        // Solo comodidad: si no se puede recordar, se vuelve a pedir la próxima vez.
      }
      setToken(withToken)
    } catch {
      setError('Token inválido o sin acceso.')
      setEntries(null)
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <section>
        <Label>Feedback</Label>
        <form
          className="mt-1.5 flex gap-1.5"
          onSubmit={(event) => {
            event.preventDefault()
            if (tokenDraft.trim()) void load(tokenDraft.trim())
          }}
        >
          <Input
            type="password"
            placeholder="Admin token"
            value={tokenDraft}
            onChange={(event) => setTokenDraft(event.target.value)}
            className="h-7 text-xs"
          />
          <Button type="submit" size="xs" variant="outline" disabled={loading}>
            Ver
          </Button>
        </form>
        {error && <p className="text-destructive mt-1 text-xs">{error}</p>}
      </section>
    )
  }

  return (
    <section>
      <div className="flex items-center justify-between">
        <Label>Feedback</Label>
        <Button
          type="button"
          size="xs"
          variant="ghost"
          className="text-muted-foreground h-5 px-1.5 text-[11px]"
          onClick={() => void load(token)}
          disabled={loading}
        >
          Actualizar
        </Button>
      </div>

      {error && <p className="text-destructive mt-1 text-xs">{error}</p>}

      {!entries && !error && (
        <p className="text-muted-foreground mt-1.5 text-xs">Cargando…</p>
      )}

      {entries && entries.length === 0 && (
        <p className="text-muted-foreground mt-1.5 text-xs">Sin feedback todavía.</p>
      )}

      {entries && entries.length > 0 && (
        <ul className="mt-1.5 flex flex-col gap-1.5">
          {entries.map((entry) => (
            <li key={entry.id}>
              <button
                type="button"
                onClick={() => onOpenSession(entry.session_id)}
                className="bg-card hover:bg-accent w-full rounded-md border px-2 py-1.5 text-left"
              >
                <div className="flex items-center gap-1.5">
                  {entry.score === 1 ? (
                    <ThumbsUp className="text-ok size-3 shrink-0" aria-hidden="true" />
                  ) : (
                    <ThumbsDown className="text-destructive size-3 shrink-0" aria-hidden="true" />
                  )}
                  <span className="text-muted-foreground text-[10px] tabular">
                    {new Date(entry.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="mt-0.5 line-clamp-2 text-xs">{entry.message}</p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
