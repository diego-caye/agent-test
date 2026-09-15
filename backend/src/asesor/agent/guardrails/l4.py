import re
import unicodedata
from dataclasses import dataclass

SAFE_PRICING_REPLY = (
    "No manejo precios ni condiciones de financiamiento, para no darte un dato "
    "equivocado 😊 Si quieres, puedo pasar tu consulta a un asesor que te dé cifras "
    "exactas. ¿Te parece?"
)

_PRICING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(s/\.?|pen|usd|us\$|\$)\s?\d"),
    re.compile(r"\b\d[\d.,]{2,}\s?(soles|dolares|dollars|usd|pen)\b"),
    re.compile(r"\bcuesta\s+(aproximadamente\s+|cerca\s+de\s+|unos\s+)?\d"),
    re.compile(r"\b(precio|costo|valor)\s+(de\s+lista|final|aproximado|referencial)\b"),
    re.compile(r"\b\d+\s*cuotas?\s+de\b"),
    re.compile(r"\b(cuota|letra)\s+mensual\s+de\s+\d"),
    re.compile(r"\b(tasa|tea|tcea)\s+(de\s+|es\s+|del\s+|queda\s+en\s+)?\d"),
    re.compile(r"\bdescuento\s+de\s+\d+\s*%"),
    re.compile(r"\bhay\s+\d+\s+unidades?\s+(en\s+)?stock\b"),
)


@dataclass(frozen=True, slots=True)
class L4Verdict:
    blocked: bool
    category: str | None = None
    replacement: str | None = None


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def inspect_reply(text: str, canary_token: str, jailbreak_reply: str) -> L4Verdict:
    """Revisa la respuesta completa del modelo antes de entregarla al usuario."""
    if canary_token and canary_token.casefold() in text.casefold():
        return L4Verdict(True, "canary_leak", jailbreak_reply)

    haystack = _fold(text)
    for pattern in _PRICING_PATTERNS:
        if pattern.search(haystack):
            return L4Verdict(True, "pricing_leak", SAFE_PRICING_REPLY)

    return L4Verdict(False)
