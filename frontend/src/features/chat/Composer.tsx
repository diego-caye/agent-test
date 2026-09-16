import { type FormEvent, type KeyboardEvent, useState } from 'react'
import { SendHorizontal } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

type Props = {
  disabled: boolean
  onSend: (text: string) => void
}

export function Composer({ disabled, onSend }: Props) {
  const [text, setText] = useState('')

  function submit(event?: FormEvent) {
    event?.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    setText('')
    onSend(trimmed)
  }

  // Enter envía y Shift+Enter hace salto de línea, que es lo que la gente ya
  // espera de un chat. Con un <input> no había forma de escribir varias líneas.
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto flex w-full max-w-2xl items-end gap-2">
      <label className="sr-only" htmlFor="composer">
        Escribe tu mensaje
      </label>
      <Textarea
        id="composer"
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Escribe tu mensaje"
        maxLength={2000}
        rows={1}
        autoComplete="off"
        className="max-h-40 min-h-11 flex-1 resize-none py-3 text-[15px]"
      />
      <Button
        type="submit"
        size="lg"
        disabled={disabled || !text.trim()}
        className="h-11 px-4"
      >
        <SendHorizontal aria-hidden="true" />
        Enviar
      </Button>
    </form>
  )
}
