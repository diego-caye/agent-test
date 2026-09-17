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
 * estado de React.
 *
 * NO dispara un 'popstate' a mano: cada quien llama a navigate() ya maneja
 * su propio estado (setSessionId actualiza sessionIdState en el mismo
 * momento; el catch de carga fallida ya hace su propio reset). Antes SÍ se
 * emitía uno sintético "para que los oyentes de la ruta se enteren", pero
 * eso disparaba efectos redundantes al propio oyente (`onPopState` en
 * useChat.ts, que ya se entera por otro lado) -- bug real, encontrado en
 * vivo: al mandar el primer mensaje de una sesión nueva, ese popstate
 * sintético relanzaba loadSessionData() para una sesión que el backend
 * todavía no tenía poblada, y su `load` con `messages: []` pisaba el
 * mensaje recién agregado de forma optimista. El listener de 'popstate'
 * sigue sirviendo para el atrás/adelante REAL del navegador, que sí dispara
 * el evento nativo por su cuenta, sin ayuda de esta función.
 */
export function navigate(path: string): void {
  if (window.location.pathname === path) return
  window.history.pushState(null, '', path)
}
