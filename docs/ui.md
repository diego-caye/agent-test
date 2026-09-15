# Spec de UI · Asesor automotriz

Plan de diseño previo al código (F4). El objetivo es que se lea como una herramienta de asesoría con la que un peruano conversaría con confianza, no como una demo genérica de IA.

## 1. Principios

1. **La conversación manda.** El chat ocupa el centro y el ancho cómodo de lectura (~68 caracteres). Todo lo demás es soporte y puede plegarse.
2. **El trabajo del agente es visible, no ruidoso.** Cuando Luis consulta la guía técnica o guarda datos, se ve un chip discreto en la línea de tiempo, no un modal ni un spinner a pantalla completa.
3. **Nada se decide por el usuario.** La derivación a un asesor humano siempre pasa por una tarjeta de confirmación con botones explícitos.
4. **Los errores dicen qué pasó y qué hacer.** Nunca un código crudo ni un stack trace.
5. **Peso visual bajo.** Una sola familia tipográfica, bordes de 1px, sombras casi ausentes. La jerarquía viene del color y del espacio, no de cajas.

### Anti-patrones que evitamos a propósito

Fondo crema con acento terracota; negro con acento neón; kit de tarjetas SaaS idénticas con la misma sombra; etiquetas en mayúsculas sobre cada título; flechas "→" decorativas en los botones; gradientes morados; ilustraciones de robot.

## 2. Color

Superficie azul noche, ligeramente desaturada hacia el azul, con un ámbar cálido como único acento. El ámbar evoca la luz de tablero de un auto y se reserva para lo accionable y para la actividad del agente, así que el ojo aprende rápido qué es interactivo.

| Token | Hex | Rol |
|---|---|---|
| `--surface` | `#12161F` | Fondo de la aplicación |
| `--panel` | `#1A202C` | Sidebar, panel dev, burbuja del agente |
| `--panel-raised` | `#222A38` | Campo de entrada, tarjeta HITL |
| `--border` | `#2C3544` | Separadores y bordes de 1px |
| `--text` | `#E7EAF0` | Texto principal |
| `--text-muted` | `#94A0B4` | Metadatos, timestamps, chips |
| `--accent` | `#E8A33D` | Botón primario, chips de tool, foco |
| `--accent-ink` | `#1A1206` | Texto sobre ámbar |
| `--accent-soft` | `#3B3020` | Fondo de chip de actividad |
| `--user-bubble` | `#2A3547` | Burbuja del usuario |
| `--success` | `#4FA87B` | Handoff confirmado |
| `--danger` | `#D8695C` | Errores |

Contraste: `--text` sobre `--surface` ≈ 13:1 y `--text-muted` sobre `--panel` ≈ 5.1:1, ambos por encima de AA. El ámbar se usa como fondo con texto oscuro (`--accent-ink`), nunca como texto claro sobre oscuro en tamaño pequeño.

## 3. Tipografía

Una sola familia con stack del sistema, para que cargue instantáneo y se vea nativa en Windows, macOS y Android:

```
font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif
```

| Rol | Tamaño / peso |
|---|---|
| Nombre del agente en la cabecera | 15px / 600 |
| Texto de conversación | 15px / 400, interlineado 1.55 |
| Chips de actividad y metadatos | 12px / 500 |
| Etiquetas del panel dev | 11px / 500, `letter-spacing: .04em` |
| Números del panel dev (latencia, tokens) | 12px / 500, tabular (`font-variant-numeric: tabular-nums`) para que no bailen al actualizarse |

Sin mayúsculas forzadas salvo en las etiquetas del panel dev, donde ayudan a separar dato de valor.

## 4. Layout

```
┌──────────┬────────────────────────────┬────────┐
│ + Nueva  │  Luis · asesor automotriz  │  Dev   │
│──────────│                            │────────│
│ Hoy      │   ┌──────────────────┐     │ Etapa  │
│ · SUV... │   │ Hola 👋 Soy Luis │     │ DESCUB │
│ · Híbr.. │   └──────────────────┘     │        │
│          │        ┌─────────────┐     │ Lead   │
│          │        │ Busco un SUV│     │ nombre │
│          │        └─────────────┘     │ uso    │
│          │   ◦ Consultando la guía…   │        │
│          │                            │ 340 ms │
│          │ ┌────────────────────────┐ │ 1.2k tk│
│          │ │ Escribe tu mensaje     │ │ traza→ │
└──────────┴─┴────────────────────────┴─┴────────┘
   240px            flexible              280px
```

- **Sidebar (240px).** Botón "Nueva conversación" y lista de sesiones con su etapa. Se colapsa bajo 900px a un botón en la cabecera.
- **Panel de chat (flexible).** Cabecera fina con el nombre del agente y el estado de conexión; lista de mensajes; campo de entrada anclado abajo.
- **Panel dev (280px, plegable).** Ficha del lead y etapa en vivo, latencia y tokens del último turno, link a la traza en Langfuse. Se pliega con un botón y su estado se recuerda en `localStorage`.

### Responsive

Bajo 900px el panel dev se oculta por completo y la sidebar pasa a un drawer. Bajo 600px las burbujas ocupan el 92% del ancho. El campo de entrada nunca se despega del borde inferior.

## 5. Componentes clave

### Burbuja de mensaje
Agente a la izquierda sobre `--panel`, usuario a la derecha sobre `--user-bubble`. Radio 14px con la esquina del lado del hablante a 4px. Sin avatar: el alineamiento ya distingue quién habla. El texto se transmite token a token; mientras llega, un cursor de bloque parpadea al final (respeta `prefers-reduced-motion` dejándolo fijo).

### Chip de actividad
Línea propia, fondo `--accent-soft`, texto `--text-muted`, punto ámbar a la izquierda. Aparece al recibir `tool.started` y se resuelve al llegar `tool.finished`.

| Tool | Texto |
|---|---|
| `search_knowledge_base` | "Consultando la guía técnica…" |
| `guardar_lead` | "Guardando tus datos…" |
| `solicitar_contacto_humano` | "Preparando tu solicitud…" |

### Tarjeta HITL
Se dispara con `hitl.confirmation_required`. Fondo `--panel-raised`, borde ámbar de 1px. Muestra motivo en lenguaje natural (no el enum), el resumen del requerimiento y el canal si se conoce. Dos botones: **"Confirmar solicitud"** (ámbar, primario) y **"Ahora no"** (fantasma). Al confirmar, la tarjeta se reemplaza por una línea de éxito en `--success`: "Solicitud enviada · TICK-00042".

Motivos en lenguaje natural: `TEST_DRIVE` → "agendar un test drive"; `COTIZACION_FORMAL` → "una cotización formal"; `COMPRA_INMEDIATA` → "avanzar con la compra"; `DISCONFORMIDAD` → "atender un reclamo"; `FUERA_DE_ALCANCE` → "hablar con un especialista".

### Error
Banda sobre el campo de entrada, borde `--danger`. Texto que dice qué pasó y qué hacer ("No pudimos conectar con el asesor. Reintenta en unos segundos.") y un botón "Reintentar" que reenvía el último mensaje.

### Panel dev
Ficha del lead campo por campo (los vacíos en `--text-muted` con un guion), etapa como chip, y del último turno: latencia en ms, tokens in/out y link a la traza si hay `LANGFUSE_PROJECT_ID`. El selector de fault injection se añade en F6, junto con la funcionalidad que lo respalda.

## 6. Accesibilidad y calidad

- Foco visible en todo elemento interactivo: anillo de 2px en `--accent` con 2px de separación. Nunca `outline: none` sin reemplazo.
- La lista de mensajes es `aria-live="polite"` para que un lector de pantalla anuncie las respuestas conforme llegan.
- Los chips de actividad y el estado de conexión se anuncian con `role="status"`.
- `prefers-reduced-motion`: desaparecen el parpadeo del cursor y las transiciones de entrada de burbuja.
- Objetivos táctiles de 40px mínimo en los botones de la tarjeta HITL.
- TypeScript strict con `noUncheckedIndexedAccess`; los tipos de la API se generan del `/openapi.json` del backend, no se escriben a mano.
- Tests con vitest del parser de SSE y del reducer del chat: son la lógica con estado real de la UI y donde un bug sería invisible a simple vista.

## 7. Qué queda fuera de F4

Botones de feedback 👍/👎 (llegan en F7, junto con el endpoint que los respalda) y el selector de fault injection (F6). Se documentan aquí para que el diseño ya les reserve lugar: el feedback va bajo cada respuesta del agente y el selector, al pie del panel dev.
