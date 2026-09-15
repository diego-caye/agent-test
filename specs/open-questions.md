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

## Decisiones técnicas a verificar en F2 (documentar en `specs/notes/adk-api.md`)

- Prefijo exacto de scope de usuario en `DatabaseSessionService` de ADK 2.x (spec 06 §1) para persistir el lead a nivel usuario, no sesión.
- Firma exacta de `EventsCompactionConfig` (parámetros de umbral de tokens y de eventos recientes a conservar).
- Estabilidad de la confirmación nativa de tools de ADK 2.x sobre streaming SSE propio (spike de F3, ver ADR-002 cuando se escriba).
- Si el SDK de ADK 2.x expone un parámetro de nivel de "thinking" configurable por env para el modelo del agente (spec 05 §3).

## Otras decisiones abiertas, no bloqueantes

- Formato exacto de `ADMIN_TOKEN` (bearer estático simple vs. algo más elaborado) — se define en F3 junto con los endpoints admin; un bearer estático por env basta para el alcance del reto.
- Librería de normalización de teléfono peruano (9 dígitos) vs. E.164 — se define en F2 al implementar `guardar_lead`; probablemente una función propia simple, sin dependencia nueva.
