from google.genai import types


def visible_text(content: types.Content | None) -> str:
    """Texto que se le muestra al usuario, sin el razonamiento del modelo.

    Los modelos con "thinking" (Gemini, y Gemma 4 vía Ollama) devuelven su
    razonamiento como partes marcadas con thought=True. Concatenar todas las
    partes le mostraría al usuario el monólogo interno del modelo.
    """
    if content is None or not content.parts:
        return ""

    return "".join(part.text or "" for part in content.parts if not part.thought)
