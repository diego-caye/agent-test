import { useEffect, useState } from 'react'

type BackendStatus = 'loading' | 'ok' | 'down'

const LABELS: Record<BackendStatus, string> = {
  loading: 'Consultando…',
  ok: 'Backend conectado',
  down: 'Backend no disponible',
}

export default function App() {
  const [status, setStatus] = useState<BackendStatus>('loading')

  useEffect(() => {
    const controller = new AbortController()

    fetch('/healthz', { signal: controller.signal })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error('unhealthy'))))
      .then((body: { status?: string }) => setStatus(body.status === 'ok' ? 'ok' : 'down'))
      .catch(() => {
        if (!controller.signal.aborted) setStatus('down')
      })

    return () => controller.abort()
  }, [])

  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col justify-center gap-3 px-6 py-10">
      <h1 className="text-xl font-semibold">Asesor automotriz virtual</h1>
      <p className="text-sm opacity-70">
        Scaffold de F1. La interfaz de chat se implementa en F4.
      </p>
      <p className="text-sm" role="status">
        {LABELS[status]}
      </p>
    </main>
  )
}
