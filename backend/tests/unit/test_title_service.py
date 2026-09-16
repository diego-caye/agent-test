import pytest

from asesor.application.title_service import clean_title, fallback_title


@pytest.mark.parametrize(
    ("crudo", "esperado"),
    [
        ("SUV para la familia", "SUV para la familia"),
        ('"SUV para la familia"', "SUV para la familia"),
        ("Título: Comparar híbridos", "Comparar híbridos"),
        ("title: Test drive el sábado", "Test drive el sábado"),
        ("Consulta sobre GNV\n\nEspero que ayude.", "Consulta sobre GNV"),
        ("  Consumo   en   ciudad  ", "Consumo en ciudad"),
        ("Mantenimiento básico.", "Mantenimiento básico"),
    ],
)
def test_limpia_lo_que_anaden_los_modelos_pequenos(crudo: str, esperado: str) -> None:
    assert clean_title(crudo) == esperado


def test_recorta_titulos_demasiado_largos() -> None:
    assert len(clean_title("palabra " * 40)) <= 48


def test_sin_respuesta_usable_el_titulo_sale_del_mensaje() -> None:
    assert fallback_title("  quiero  una SUV ") == "quiero una SUV"


def test_el_mensaje_largo_se_recorta_con_puntos_suspensivos() -> None:
    titulo = fallback_title("necesito un auto " * 10)

    assert len(titulo) <= 48
    assert titulo.endswith("…")
