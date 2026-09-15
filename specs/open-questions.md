# Open questions

Bloqueos, decisiones que los specs no cubren del todo, y prerrequisitos pendientes del humano. Se resuelven antes de que la fase correspondiente los necesite; no bloquean F0.

## Prerrequisitos · estado

Detectado al arrancar F0 (2026-09-15) y actualizado al cerrar F1.

### Resuelto

- **Repositorio git.** Se inicializó localmente en F0 (`git init -b main`) con `main`, `develop` y una rama por fase.
- **Python 3.12.** Sí existe, aunque no en PATH: `uv` resuelve `cpython-3.12.11`. El proyecto lo pinea con `requires-python = ">=3.12,<3.13"` y `uv sync` lo usa automáticamente. No hace falta instalar nada más.
- **`google-adk`.** Instalado y verificado en F1: **2.9.1** (pineado exacto en `backend/pyproject.toml`), importa correctamente en Python 3.12.11.
- **IDs de modelos Gemini.** Confirmados contra la documentación oficial el 2026-09-15 y fijados en `.env.example`: `gemini-3.8-flash` (agente), `gemini-3.5-flash-lite` (guardrail L2), `gemini-3.5-flash` (eval), `gemini-3.7-flash` (fallback, a propósito de otra generación que el principal), `gemini-embedding-001` (768 dims, estable; `gemini-embedding-2-preview` sigue en preview y es el que no acepta `task_type`).
- **Docker, uv, Node.** Docker 29.8.0 / Compose v5.5.1, uv 0.10.12, Node 24.14.1.
- `.local/baseline_n8n.json` presente y cubierto por `.gitignore`; `.env` local creado en F1 y también ignorado (verificado con `git check-ignore`).

### Abierto

- **`gh` CLI no instalado** y sin repo remoto en GitHub. Los merges de fase se están haciendo localmente con `git merge --no-ff`, usando el cuerpo del merge commit como descripción de PR (qué, por qué, cómo probar, AT cubiertos). **Acción del humano:** crear el repo público, `gh auth login`, `git remote add origin ...` y `git push` de `main` y `develop`. Sin esto, el CI de GitHub Actions (`.github/workflows/ci.yml`) nunca corre y el entregable "repo público" queda pendiente.
- **Skills de ADK no instalados** (`npx skills add google/agents-cli`). Necesario al empezar F2 para verificar firmas de ADK 2.x.
- **`GOOGLE_API_KEY` real.** El `.env` local tiene un placeholder que solo satisface la validación de arranque. F2 necesita una key con billing activo para cualquier prueba contra el modelo real.
- **GNU `make` no está instalado en Windows** (sí Chocolatey). El `Makefile` es la interfaz canónica y funciona en CI, Docker y Linux/macOS. En esta máquina los comandos se corren directamente (`cd backend && uv run pytest`, etc.). **Opcional:** `choco install make -y` desde una consola con privilegios de administrador.
- **Puertos ocupados en esta máquina.** Otros contenedores del usuario ya usan 8000 y 5173. `docker-compose.yml` publica puertos configurables (`BACKEND_PORT`, `FRONTEND_PORT`, `POSTGRES_PORT`) y el `.env` local los desplaza a 8008 y 5174. Los defaults del repo siguen siendo 8000/5173 para quien lo clone.

- **Otro Postgres nativo en el host.** Hay un servicio `postgresql-x64-18` escuchando en 0.0.0.0:5432, así que el contenedor del proyecto solo pudo bindear IPv6 y `localhost:5432` iba al Postgres nativo (fallaba la autenticación). El compose ahora publica `POSTGRES_PORT=5442` vía `.env`. En CI y en una máquina limpia el default sigue siendo 5432.

## Resuelto en F2 (documentado en `specs/notes/adk-api.md`)

- Prefijo de scope de usuario: es `user:` (también existen `app:` y `temp:`). Decisión tomada: **no** se usa para el lead — la tabla `leads` es la única fuente de verdad (spec 06 §1).
- `EventsCompactionConfig(token_threshold=..., event_retention_size=..., summarizer=...)`, verificado. Está cableado; falta afinar umbrales con conversaciones largas (F7).
- Inyección de estado en la instrucción: `instruction` acepta un callable `(ReadonlyContext) -> str | Awaitable[str]`. Se usa esa vía en lugar de placeholders `{state_key}`, porque la ficha del lead es JSON y sus llaves colisionan con el templating.

## Sigue abierto para F3 y más adelante

- Estabilidad de la confirmación nativa de tools de ADK 2.x (`ToolContext.request_confirmation`, `EventActions.requested_tool_confirmations` — ambos existen) sobre nuestro streaming SSE. Spike de F3 y ADR-002.
- Si el SDK de ADK 2.x expone un nivel de "thinking" configurable por env para el modelo del agente (spec 05 §3). No se investigó en F2: no bloquea, es una optimización de latencia.
- `App(name=...)` debe coincidir con el directorio del agente para que `adk eval` encuentre las sesiones. Nuestra estructura no sigue la convención de directorios de ADK; revisar al montar el evalset en F7.

## Otras decisiones abiertas, no bloqueantes

- Formato exacto de `ADMIN_TOKEN` (bearer estático simple vs. algo más elaborado) — se define en F3 junto con los endpoints admin; un bearer estático por env basta para el alcance del reto.
- Librería de normalización de teléfono peruano (9 dígitos) vs. E.164 — se define en F2 al implementar `guardar_lead`; probablemente una función propia simple, sin dependencia nueva.
