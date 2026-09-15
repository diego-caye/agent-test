# Open questions

Bloqueos, decisiones que los specs no cubren del todo, y prerrequisitos pendientes del humano. Se resuelven antes de que la fase correspondiente los necesite; no bloquean F0.

## Prerrequisitos declarados en `00-master-build.md` aún no verificados en esta máquina

Detectado al arrancar F0 (2026-09-15):

- **No había repositorio git.** Se inicializó localmente (`git init -b main`), se creó `develop` y la rama `docs/specs` para F0. **Falta:** repo remoto en GitHub (público) — no se pudo verificar ni crear porque `gh` no está instalado/autenticado en esta máquina. Necesario antes de F1 (el flujo de PR por fase depende de un remoto).
- **`gh` CLI no encontrado** (ni en bash ni en PowerShell). `gh auth login` pendiente. Sin esto no se pueden abrir PRs reales; los merges de fase tendrían que hacerse localmente con `git merge --no-ff` como alternativa temporal, documentándolo en cada PR "simulado".
- **Skills de ADK no instalados** (`npx skills add google/agents-cli` no se ha corrido; no hay carpeta de skills de agentes en este entorno). Necesario antes de F2, donde se verifican firmas de ADK 2.x contra el paquete real.
- **`google-adk` no instalado** (`pip show google-adk` no lo encuentra) y **no hay Python 3.12** disponible en PATH (solo un stub de Microsoft Store; `py --version` reporta 3.14.4 vía launcher, a confirmar si hay un intérprete real detrás). Necesario para F1 (scaffold con `uv`) y F2.
- **Docker, uv, Node** sí están disponibles (Docker 29.8.0, uv 0.10.12, Node 24.14.1) — cumplen el prerrequisito.
- `.local/baseline_n8n.json` está presente y ya cubierto por el `.gitignore` creado en F0 (`.local/`).
- `.env` con `GOOGLE_API_KEY` no verificado — no hay `.env` en el repo aún (se crea `.env.example` en F1; el `.env` real es responsabilidad del humano y ya está en `.gitignore`).

**Acción:** antes de iniciar F1, confirmar con el humano: URL del repo remoto en GitHub, `gh auth login` hecho, `GOOGLE_API_KEY` con billing activo disponible como variable de entorno local. Sin esto, F1 puede avanzar en estructura/specs pero no en CI real contra GitHub Actions ni en pruebas `live` contra Gemini.

## Decisiones técnicas a verificar en F2 (no bloquean F0, documentar en `specs/notes/adk-api.md`)

- Prefijo exacto de scope de usuario en `DatabaseSessionService` de ADK 2.x (spec 06 §1) para persistir el lead a nivel usuario, no sesión.
- Firma exacta de `EventsCompactionConfig` (parámetros de umbral de tokens y de eventos recientes a conservar).
- Estabilidad de la confirmación nativa de tools de ADK 2.x sobre streaming SSE propio (spike de F3, ver ADR-002 cuando se escriba).
- Si el SDK de ADK 2.x expone un parámetro de nivel de "thinking" configurable por env para el modelo del agente (spec 05 §3).
- IDs vigentes de modelos Gemini (`AGENT_MODEL`, `EMBEDDINGS_MODEL` por defecto en `.env.example`) — se confirman contra la documentación oficial al momento de escribir F1, no se fijan hoy.

## Otras decisiones abiertas, no bloqueantes

- Formato exacto de `ADMIN_TOKEN` (bearer estático simple vs. algo más elaborado) — se define en F3 junto con los endpoints admin; un bearer estático por env basta para el alcance del reto.
- Librería de normalización de teléfono peruano (9 dígitos) vs. E.164 — se define en F2 al implementar `guardar_lead`; probablemente una función propia simple, sin dependencia nueva.
