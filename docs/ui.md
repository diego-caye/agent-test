# Spec de UI · Asesor automotriz

Plan de diseño previo al código (F4), actualizado en F6 al adoptar shadcn/ui y de nuevo al pasar de una paleta azul + ámbar a blanco y negro con modo claro/oscuro. El objetivo es que se lea como una herramienta de asesoría con la que un peruano conversaría con confianza, no como una demo genérica de IA.

## 0. Base de componentes

Los componentes vienen de **shadcn/ui** (preset `radix-nova`, primitivas de Radix, iconos de Lucide), instalados en `src/components/ui/` y versionados con el repo: no es una dependencia opaca, es código propio que se puede leer y modificar. Lo que aporta y no íbamos a rehacer bien a mano es el comportamiento accesible de los overlays — el `Select` del selector de modelo y el `AlertDialog` de borrado necesitan foco atrapado, cierre con Escape, navegación con teclado y `aria-*` correctos.

La paleta de la sección 2 **no** se mantiene aparte: se expresa directamente en los tokens semánticos de shadcn (`--primary`, `--muted-foreground`, `--border`…), de modo que cualquier componente que se añada después salga ya con la identidad del producto. Tener dos sistemas de color conviviendo era la forma segura de que se desincronizaran.

Un componente propio, no de shadcn, controla el modo: `ThemeToggle` alterna la clase `.dark` en `<html>` y persiste la elección en `localStorage`. Un script inline en `index.html` la aplica antes del primer render para no mostrar un parpadeo del tema equivocado, y hasta que la persona no toca el botón la app sigue el tema del sistema operativo.

## 1. Principios

1. **La conversación manda.** El chat ocupa el centro y el ancho cómodo de lectura (~68 caracteres). Todo lo demás es soporte y puede plegarse.
2. **El trabajo del agente es visible, no ruidoso.** Cuando Luis consulta la guía técnica o guarda datos, se ve un chip discreto en la línea de tiempo, no un modal ni un spinner a pantalla completa.
3. **Nada se decide por el usuario.** La derivación a un asesor humano siempre pasa por una tarjeta de confirmación con botones explícitos.
4. **Los errores dicen qué pasó y qué hacer.** Nunca un código crudo ni un stack trace.
5. **Peso visual bajo.** Una sola familia tipográfica, bordes de 1px, sombras casi ausentes. La jerarquía viene del color y del espacio, no de cajas.

### Anti-patrones que evitamos a propósito

Fondo crema con acento terracota; negro con acento neón; kit de tarjetas SaaS idénticas con la misma sombra; etiquetas en mayúsculas sobre cada título; flechas "→" decorativas en los botones; gradientes morados; ilustraciones de robot.

## 2. Color

Blanco y negro puros, sin acento de color: el propio contraste tipográfico hace de jerarquía y nada compite por la atención con lo que dice Luis. `--primary` se invierte entre modos (negro sobre blanco en claro, blanco sobre negro en oscuro) en vez de ser un tono fijo, que es como shadcn resuelve un "botón principal" en una paleta neutra. El éxito de un handoff y los errores conservan un color discreto porque son estado, no decoración — perderlos del todo le habría costado claridad a la interfaz.

| Token | Claro | Oscuro | Rol |
|---|---|---|---|
| `--background` | `#FFFFFF` | `#0A0A0A` | Fondo de la aplicación |
| `--card` | `#FFFFFF` | `#171717` | Burbuja del agente, panel dev |
| `--sidebar` | `#FAFAFA` | `#141414` | Barra lateral |
| `--popover` / `--secondary` | `#F2F2F2` | `#262626` | Menú del selector, tarjeta HITL |
| `--border` / `--input` | `#E2E2E2` | `#2B2B2B` | Separadores y bordes de 1px |
| `--foreground` | `#0A0A0A` | `#F2F2F2` | Texto principal |
| `--muted-foreground` | `#6B6B6B` | `#A3A3A3` | Metadatos, timestamps, chips |
| `--primary` / `--ring` | `#171717` | `#F2F2F2` | Botón primario, punto de actividad, foco |
| `--primary-foreground` | `#FAFAFA` | `#171717` | Texto sobre el botón primario |
| `--color-accent-soft`, `--color-user-bubble` | = `--secondary` | = `--secondary` | Fondo de chip de actividad, burbuja del usuario |
| `--color-ok` | `#1A7A42` | `#4ADE80` | Handoff confirmado |
| `--destructive` | `#C0362C` | `#E5645A` | Errores y borrado |

`:root` lleva el tema claro y `.dark` el oscuro; cuál de los dos se aplica lo decide `ThemeToggle` (sección 0), no una media query — así una elección explícita no queda pisada por el sistema operativo.

Contraste en ambos modos: `--foreground` sobre `--background` ≈ 19:1 (claro) y ≈ 17:1 (oscuro); `--muted-foreground` sobre `--card`/`--sidebar` por encima de 4.5:1. El botón primario usa `--primary-foreground` sobre `--primary`, nunca texto de un tono sobre fondo del mismo tono.

## 3. Tipografía

Una sola familia, **Geist Variable**, servida desde el propio bundle (`@fontsource-variable/geist`) y no desde un CDN, para que no dependa de la red ni filtre visitas a terceros. Cae al stack del sistema si por lo que sea no carga:

```
font-family: "Geist Variable", "Segoe UI", system-ui, sans-serif
```

| Rol | Tamaño / peso |
|---|---|
| Nombre del agente en la cabecera | 15px / 600 |
| Texto de conversación | 15px / 400, interlineado 1.55 |
| Chips de actividad y metadatos | 12px / 500 |
| Selector de modelo | 12px / 500 |
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

- **Sidebar (240px).** Botón "Nueva conversación" y lista de sesiones. Cada fila muestra el **título de la conversación** en la primera línea y fecha + etapa en la segunda; el título lo genera el modelo ligero en segundo plano a partir del primer mensaje, así que hasta que llega se lee "Conversación nueva". El icono de papelera aparece al pasar el cursor (y con foco de teclado) y abre un `AlertDialog` que aclara que se pierden los mensajes pero no la ficha del lead. Se colapsa bajo 900px a un botón en la cabecera.
- **Panel de chat (flexible).** Cabecera fina con el nombre del agente y el estado de conexión; lista de mensajes; campo de entrada anclado abajo.
- **Panel dev (280px, plegable).** Ficha del lead y etapa en vivo, latencia y tokens del último turno, link a la traza en Langfuse. Se pliega con un botón y su estado se recuerda en `localStorage`.

### Responsive

Bajo 900px el panel dev se oculta por completo y la sidebar pasa a un drawer. Bajo 600px las burbujas ocupan el 92% del ancho. El campo de entrada nunca se despega del borde inferior.

## 5. Componentes clave

### Burbuja de mensaje
Agente a la izquierda sobre `--card`, usuario a la derecha sobre `--color-user-bubble`. Radio 14px con la esquina del lado del hablante a 4px. Sin avatar: el alineamiento ya distingue quién habla.

**Sobre el streaming (revisado en F6).** El texto del agente llega en un solo evento, no token a token. No es una simplificación: el filtro de salida L4 necesita ver la respuesta completa antes de que salga, y un delta ya transmitido no se puede retirar del navegador — razonado en `specs/02-api-contract.md` §4. Lo que sí ocurre en vivo, y es de donde viene la sensación de que el asesor está trabajando, son los chips de actividad de las tools, la ficha del lead y la tarjeta HITL.

**Indicador de escritura.** Como la burbuja del agente no existe hasta que llega la respuesta completa, entre el envío y la respuesta no habría nada en pantalla: con un modelo local en frío eso son decenas de segundos y la interfaz parece colgada. Tres puntos animados ocupan ese hueco desde el primer instante, y a los 8 segundos se añade una línea de texto. Consciente del proveedor del modelo elegido en el selector: con uno de Ollama dice que los modelos locales a veces tardan más de lo normal; con uno de la API (Gemini) el texto es genérico ("esto puede tardar unos segundos"), porque ahí la demora no tiene nada que ver con cargar un modelo en la GPU de esta máquina. Respeta `prefers-reduced-motion`.

**Reintentar y editar (bajo el mensaje, no al pie de la pantalla).** Cuando el último mensaje se quedó sin respuesta, el mensaje del usuario que corresponde muestra dos botones de texto pequeños justo debajo — nunca en medio de la conversación, solo en el último, porque es el único que puede necesitarlo:

- **"↻ Reintentar"** reenvía ese mismo texto sin duplicar la burbuja.
- **"✎ Editar"** convierte esa misma burbuja en un campo editable, con foco puesto ahí — no manda el texto al campo de entrada principal de abajo. Al confirmar ("Guardar y enviar"), la burbuja queda con el texto corregido y se reenvía; no se agrega un mensaje aparte. "Cancelar" o Escape descartan el cambio sin tocar nada.

Antes vivía como un botón grande al pie de la pantalla junto al banner de error; con más de un mensaje en la conversación no quedaba claro qué iba a reintentar, así que se movió a pegado al mensaje concreto.

### Chip de actividad
Línea propia, fondo `--color-accent-soft`, texto `--muted-foreground`, punto en `--primary` a la izquierda. Aparece al recibir `tool.started` y se resuelve al llegar `tool.finished`.

| Tool | Texto |
|---|---|
| `search_knowledge_base` | "Consultando la guía técnica…" |
| `guardar_lead` | "Guardando tus datos…" |
| `solicitar_contacto_humano` | "Preparando tu solicitud…" |

### Tarjeta HITL
Se dispara con `hitl.confirmation_required`. Fondo elevado, borde `--primary` de 1px. Muestra motivo en lenguaje natural (no el enum), el resumen del requerimiento y el canal si se conoce. Dos botones: **"Confirmar solicitud"** (primario) y **"Ahora no"** (fantasma). Al confirmar, la tarjeta se reemplaza por una línea de éxito en `--color-ok`: "Solicitud enviada · TICK-00042".

Motivos en lenguaje natural: `TEST_DRIVE` → "agendar un test drive"; `COTIZACION_FORMAL` → "una cotización formal"; `COMPRA_INMEDIATA` → "avanzar con la compra"; `DISCONFORMIDAD` → "atender un reclamo"; `FUERA_DE_ALCANCE` → "hablar con un especialista".

### Selector de modelo
En la cabecera, a la izquierda del botón del panel dev. Un `Select` que lista el catálogo de `GET /api/v1/models` con una insignia por proveedor ("local" o "API"). El modelo elegido se manda en cada turno y se recuerda en `localStorage`; **no** se ata a la conversación, de modo que se puede cambiar de modelo a media charla sin perder el historial ni la ficha del lead — es la forma más directa de enseñar la misma conversación con Gemma 4, Qwen3 y Gemini. Se oculta si solo hay una opción configurada y se deshabilita mientras un turno está en vuelo. Las opciones cuyo proveedor no está configurado (Gemini sin API key) salen deshabilitadas con la nota "sin configurar" en vez de ocultarse, para que se vea qué hay y por qué no se puede usar.

### Título de la conversación
Lo genera `GUARDRAIL_MODEL` (el modelo pequeño) a partir del primer mensaje del usuario, en segundo plano y después del turno, para no sumarle latencia a la respuesta. De tres a seis palabras, máximo 48 caracteres. Si el modelo devuelve algo inservible se usa el propio mensaje recortado: una conversación siempre tiene que poder distinguirse de las demás en la lista.

### Error
Banda sobre el campo de entrada, borde `--destructive`, solo con el texto de qué pasó — sin botón propio. El botón "Reintentar" vive junto al mensaje concreto que se reenvía (ver Burbuja de mensaje), no aquí: uno solo al pie de la pantalla no dejaba claro qué se iba a reintentar cuando ya había varios mensajes en la conversación. Se dispara en tres casos: el backend manda un evento `error`; la conexión SSE se corta sin ningún evento de cierre (crash del backend, red caída — no hay forma de distinguirlo de un turno legítimo salvo notando que nunca llegó nada definitivo); o el turno queda en silencio total más de tres minutos, que es el timeout de inactividad del lado del cliente. Los tres casos usan la misma señal porque desde el punto de vista de quien espera una respuesta son el mismo problema: no llegó nada y hay que poder reintentar sin recargar la página.

### Panel dev
Ficha del lead campo por campo (los vacíos en `--muted-foreground` con un guion), etapa como insignia, y del último turno: latencia en ms, tokens in/out y link a la traza si hay `LANGFUSE_PROJECT_ID`. El selector de fault injection se añade en F6, junto con la funcionalidad que lo respalda.

### Rutas y creación diferida de la sesión
Cada conversación vive en su propia URL, `/c/:id`, navegable de verdad: se puede recargar, pegar en otra pestaña o abrir con Ctrl/Cmd+clic sin perder el lugar. `/` es el borrador — la conversación todavía sin crear en el backend.

El botón "Nueva conversación" solo vuelve al borrador (`/`) y limpia el estado local; no llama a la API. La sesión se crea recién cuando se envía el primer mensaje de verdad, así que un clic repetido en el botón no dejaba una fila vacía por clic — ni tampoco al recargar la página con el borrador sin usar, que era la causa real de la acumulación de "Conversación nueva" en la barra lateral (dos correcciones previas habían tapado sólo dos síntomas del mismo problema: los clics simultáneos y los clics normales repetidos, pero no la creación anticipada en sí).

Al entrar directo a `/c/:id` (un link, un refresh, atrás/adelante del navegador) se carga esa conversación; si el `id` no existe o no es de este usuario, se cae al borrador en vez de dejar la pantalla colgada.

### Conversación que se quedó sin respuesta
El backend no persiste que un turno falló, solo el intercambio en sí (guardar un "esto no funcionó" complicaría el modelo de datos por algo que ADK ya resuelve dejando, sencillamente, nada escrito). Si al cargar una conversación el último mensaje guardado es del usuario, no hubo respuesta — el modelo falló, la conexión se cortó a medias, lo que sea. Se reconstruye la misma señal de reintento que un fallo en vivo: aparece el ícono "Reintentar" bajo ese mensaje y reenvía su texto a la misma conversación, sin duplicar la burbuja que ya está en pantalla.

Motivo real detrás de esto, encontrado inspeccionando la base de datos en vivo: un turno cuya conexión se corta a medias hace que ADK cancele la tarea del agente (`Root node <agent> was cancelled`) antes de escribir ningún evento — ni siquiera uno de error. Antes de este arreglo, recargar una conversación así dejaba el mensaje del usuario ahí colgado sin ninguna pista de que se podía reintentar.

## 6. Accesibilidad y calidad

- Foco visible en todo elemento interactivo: anillo `--ring`, que se invierte con el tema igual que el resto de la paleta. Nunca `outline: none` sin reemplazo.
- El campo de entrada es un `textarea`: Enter envía y Shift+Enter hace salto de línea, que es lo que ya se espera de un chat.
- La lista de mensajes es `aria-live="polite"` para que un lector de pantalla anuncie las respuestas conforme llegan.
- Los chips de actividad y el estado de conexión se anuncian con `role="status"`.
- `prefers-reduced-motion`: desaparecen el parpadeo del cursor y las transiciones de entrada de burbuja.
- Objetivos táctiles de 40px mínimo en los botones de la tarjeta HITL.
- TypeScript strict con `noUncheckedIndexedAccess`; los tipos de la API se generan del `/openapi.json` del backend, no se escriben a mano.
- Tests con vitest del parser de SSE y del reducer del chat: son la lógica con estado real de la UI y donde un bug sería invisible a simple vista.

## 7. Qué queda fuera de F4

Botones de feedback 👍/👎 (llegan en F7, junto con el endpoint que los respalda) y el selector de fault injection (F6). Se documentan aquí para que el diseño ya les reserve lugar: el feedback va bajo cada respuesta del agente y el selector, al pie del panel dev.
