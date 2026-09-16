import { useState } from 'react'
import { Moon, Sun } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { type Theme, getInitialTheme, setStoredTheme } from '@/lib/theme'

export function ThemeToggle() {
  // El valor inicial real ya lo aplicó el script inline de index.html antes
  // de este primer render; esto solo sincroniza qué ícono mostrar. Guardar
  // recién al cambiar (no en un efecto disparado por el estado inicial) evita
  // fijar en localStorage una preferencia que el usuario nunca eligió: hasta
  // que no toca el botón, la app sigue seleccionado el tema del sistema.
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  function toggle() {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    setStoredTheme(next)
    setTheme(next)
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="icon-sm"
      onClick={toggle}
      aria-label={theme === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro'}
      title={theme === 'dark' ? 'Modo claro' : 'Modo oscuro'}
    >
      {theme === 'dark' ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </Button>
  )
}
