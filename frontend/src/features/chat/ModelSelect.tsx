import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

import type { ModelOption } from '../../api/types'

const PROVIDER_LABEL: Record<string, string> = {
  ollama: 'local',
  gemini: 'API',
}

type Props = {
  models: ModelOption[]
  value: string | null
  disabled: boolean
  onChange: (modelId: string) => void
}

export function ModelSelect({ models, value, disabled, onChange }: Props) {
  // Con una sola opción el selector no aporta nada: el modelo ya se ve en el
  // panel dev, en las métricas del turno.
  if (models.length < 2) return null

  const current = models.find((model) => model.id === value) ?? models[0]
  if (!current) return null

  return (
    <Select value={current.id} disabled={disabled} onValueChange={onChange}>
      <SelectTrigger
        size="sm"
        aria-label="Modelo"
        title={`${current.model} · ${current.provider}`}
        className="min-w-[9.5rem]"
      >
        <SelectValue />
      </SelectTrigger>
      {/* "item-aligned" (el valor por defecto) superpone el menú sobre el
          disparador para alinear la opción elegida, como un <select> nativo;
          en una cabecera angosta eso tapaba el propio selector. "popper"
          lo abre debajo, como cualquier otro menú desplegable. */}
      <SelectContent position="popper" align="start" sideOffset={6}>
        {models.map((model) => (
          // Las opciones sin configurar se muestran deshabilitadas en vez de
          // ocultarse: así se ve qué hay disponible y por qué no se puede usar.
          <SelectItem key={model.id} value={model.id} disabled={!model.available}>
            <span className="flex items-center gap-2">
              {model.label}
              <Badge variant="outline" className="text-[10px]">
                {PROVIDER_LABEL[model.provider] ?? model.provider}
              </Badge>
              {!model.available && (
                <span className="text-muted-foreground text-[10px]">sin configurar</span>
              )}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
