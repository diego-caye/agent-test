import pytest

from asesor.domain.contact import InvalidPhoneError, normalize_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("987654321", "987654321"),
        ("987 654 321", "987654321"),
        ("987-654-321", "987654321"),
        ("+51 987 654 321", "+51987654321"),
        ("51987654321", "+51987654321"),
        ("0051987654321", "+51987654321"),
        ("+34 600 123 456", "+34600123456"),
    ],
)
def test_normalizes_valid_numbers(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["12345", "887654321", "no-es-un-numero", "", "+0123456789"],
)
def test_rejects_invalid_numbers(raw: str) -> None:
    with pytest.raises(InvalidPhoneError):
        normalize_phone(raw)
