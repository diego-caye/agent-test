import { type FormEvent, useState } from 'react'

type Props = {
  disabled: boolean
  onSend: (text: string) => void
}

export function Composer({ disabled, onSend }: Props) {
  const [text, setText] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    setText('')
    onSend(trimmed)
  }

  return (
    <form onSubmit={submit} className="mx-auto flex w-full max-w-2xl gap-2">
      <label className="sr-only" htmlFor="composer">
        Escribe tu mensaje
      </label>
      <input
        id="composer"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Escribe tu mensaje"
        maxLength={2000}
        autoComplete="off"
        className="min-h-11 flex-1 rounded-xl border border-edge bg-raised px-4 text-[15px] placeholder:text-muted"
      />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="min-h-11 rounded-xl bg-accent px-4 text-sm font-semibold text-accent-ink disabled:opacity-50"
      >
        Enviar
      </button>
    </form>
  )
}
