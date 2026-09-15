import { CANAL_LABEL, MOTIVO_LABEL } from '../chat/labels'
import type { Confirmation, Handoff } from '../chat/reducer'

type Props = {
  confirmation: Confirmation
  busy: boolean
  onAnswer: (approved: boolean) => void
}

export function ConfirmationCard({ confirmation, busy, onAnswer }: Props) {
  const motivo = MOTIVO_LABEL[confirmation.motivo] ?? 'hablar con un asesor'
  const canal = confirmation.canal_preferido
    ? (CANAL_LABEL[confirmation.canal_preferido] ?? confirmation.canal_preferido)
    : null

  return (
    <section className="mx-auto max-w-2xl rounded-xl border border-accent/60 bg-raised p-4">
      <h2 className="text-[15px] font-semibold">¿Te derivamos con un asesor?</h2>
      <p className="mt-1 text-sm text-muted">
        Luis quiere pasar tu caso a una persona para {motivo}.
      </p>

      <p className="mt-3 rounded-lg bg-panel px-3 py-2 text-sm">{confirmation.resumen}</p>

      {canal && <p className="mt-2 text-xs text-muted">Te contactarían por {canal}.</p>}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => onAnswer(true)}
          disabled={busy}
          className="min-h-10 rounded-lg bg-accent px-4 text-sm font-semibold text-accent-ink disabled:opacity-60"
        >
          Confirmar solicitud
        </button>
        <button
          type="button"
          onClick={() => onAnswer(false)}
          disabled={busy}
          className="min-h-10 rounded-lg border border-edge px-4 text-sm text-muted disabled:opacity-60"
        >
          Ahora no
        </button>
      </div>
    </section>
  )
}

export function HandoffNotice({ handoff }: { handoff: Handoff }) {
  return (
    <p
      className="mx-auto max-w-2xl rounded-lg border border-ok/40 bg-panel px-4 py-2.5 text-sm text-ok"
      role="status"
    >
      {handoff.ya_existia ? 'Ya tenías una solicitud en curso' : 'Solicitud enviada'} ·{' '}
      <span className="tabular font-semibold">{handoff.ticket}</span>
    </p>
  )
}
