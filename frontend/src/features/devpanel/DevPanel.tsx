import { X } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Sidebar, SidebarContent, SidebarHeader } from '@/components/ui/sidebar'

import type { LeadDto, TurnMetrics } from '../../api/types'
import { ETAPA_LABEL, LEAD_FIELDS } from '../chat/labels'

type Props = {
  lead: LeadDto | null
  etapa: string
  metrics: TurnMetrics | null
  onClose: () => void
}

const LANGFUSE_PROJECT = import.meta.env['VITE_LANGFUSE_PROJECT_ID'] as string | undefined
// Sin esto, un plan que no vive en el cloud.langfuse.com por defecto (p. ej.
// una region HIPAA con host propio) arma el link contra el host equivocado y
// se queda "Loading..." para siempre (visto en vivo).
const LANGFUSE_HOST =
  (import.meta.env['VITE_LANGFUSE_HOST'] as string | undefined) || 'https://cloud.langfuse.com'

export function DevPanel({ lead, etapa, metrics, onClose }: Props) {
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
