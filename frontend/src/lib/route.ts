/**
 * Router mínimo a mano: la app solo tiene dos formas de URL, así que traer
 * una librería de rutas completa sería más código que resolver, no menos.
 *
 *   /            conversación en borrador, todavía sin crear en el backend
 *   /c/:id       una conversación existente, navegable y para compartir
 */

const SESSION_PATH_RE = /^\/c\/([^/]+)\/?$/

export function sessionIdFromPath(pathname: string): string | null {
  const match = SESSION_PATH_RE.exec(pathname)
  return match?.[1] ? decodeURIComponent(match[1]) : null
}

export function sessionPath(sessionId: string): string {
  return `/c/${encodeURIComponent(sessionId)}`
}

/**
 * Cambia la URL sin recargar la página, pero deja una URL real (para
 * compartir, marcar como favorita o usar atrás/adelante) en vez de solo
 * estado de React. pushState no dispara 'popstate' por sí mismo, así que se
 * emite a mano para que los oyentes de la ruta se enteren del cambio.
 */
export function navigate(path: string): void {
  if (window.location.pathname === path) return
  window.history.pushState(null, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}
