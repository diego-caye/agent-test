import type { LeadDto, TurnMetrics } from '../../api/types'
import { ETAPA_LABEL, LEAD_FIELDS } from '../chat/labels'

type Props = {
  lead: LeadDto | null
  etapa: string
  metrics: TurnMetrics | null
  onClose: () => void
}

const LANGFUSE_PROJECT = import.meta.env['VITE_LANGFUSE_PROJECT_ID'] as string | undefined

export function DevPanel({ lead, etapa, metrics, onClose }: Props) {
  const record = (lead ?? {}) as Record<string, unknown>

  return (
    <aside className="hidden w-70 shrink-0 flex-col gap-5 border-l border-edge bg-panel p-4 lg:flex">
      <div className="flex items-center justify-between">
        <Label>Panel dev</Label>
        <button
          type="button"
          onClick={onClose}
          className="rounded px-1.5 text-xs text-muted hover:text-ink"
          aria-label="Ocultar panel dev"
        >
          ✕
        </button>
      </div>

      <section>
        <Label>Etapa</Label>
        <p className="mt-1.5 inline-block rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium">
          {ETAPA_LABEL[etapa] ?? etapa}
        </p>
      </section>

      <section>
        <Label>Ficha del lead</Label>
        <dl className="mt-1.5 flex flex-col gap-1">
          {LEAD_FIELDS.map((field) => {
            const value = record[field.key]
            return (
              <div key={field.key} className="flex justify-between gap-2 text-xs">
                <dt className="text-muted">{field.label}</dt>
                <dd className={value ? 'text-ink' : 'text-muted'}>
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
          <p className="mt-1.5 text-xs text-muted">Sin turnos todavía.</p>
        )}

        {metrics && LANGFUSE_PROJECT && (
          <a
            className="mt-2 inline-block text-xs text-accent underline underline-offset-2"
            href={`https://cloud.langfuse.com/project/${LANGFUSE_PROJECT}/traces/${metrics.trace_id}`}
            target="_blank"
            rel="noreferrer"
          >
            Ver traza en Langfuse
          </a>
        )}
      </section>
    </aside>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-[11px] font-medium tracking-[0.04em] text-muted uppercase">{children}</h2>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <dt className="text-muted">{label}</dt>
      <dd className="tabular">{value}</dd>
    </div>
  )
}
