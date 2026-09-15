import re

from asesor.domain.errors import InvalidPhoneError

_SEPARATORS = re.compile(r"[\s\-().]")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")
_PERU_MOBILE = re.compile(r"^9\d{8}$")


def normalize_phone(raw: str) -> str:
    """Return a Peru 9-digit mobile as-is, or any other number in E.164."""
    candidate = _SEPARATORS.sub("", raw.strip())

    if candidate.startswith("00"):
        candidate = "+" + candidate[2:]

    if _PERU_MOBILE.match(candidate):
        return candidate

    if candidate.startswith("51") and _PERU_MOBILE.match(candidate[2:]):
        return "+" + candidate

    if _E164.match(candidate):
        return candidate

    raise InvalidPhoneError(
        "Phone must be a 9-digit Peruvian mobile (starting with 9) or an E.164 number"
    )
