from uuid import uuid4

import pytest

from asesor.infrastructure.db.engine import SessionFactory
from asesor.infrastructure.db.session_title_repository import SqlSessionTitleRepository

pytestmark = pytest.mark.usefixtures("clean_database")


@pytest.fixture
def repo(session_factory: SessionFactory) -> SqlSessionTitleRepository:
    return SqlSessionTitleRepository(session_factory)


async def test_get_de_una_sesion_sin_titulo_devuelve_none(repo: SqlSessionTitleRepository) -> None:
    assert await repo.get("no-existe") is None


async def test_upsert_y_luego_get_devuelven_el_mismo_titulo(
    repo: SqlSessionTitleRepository,
) -> None:
    await repo.upsert("sesion-1", uuid4(), "SUV para la familia")

    assert await repo.get("sesion-1") == "SUV para la familia"


async def test_upsert_repetido_sobre_la_misma_sesion_reemplaza_el_titulo(
    repo: SqlSessionTitleRepository,
) -> None:
    user = uuid4()
    await repo.upsert("sesion-1", user, "primer titulo")
    await repo.upsert("sesion-1", user, "titulo corregido")

    assert await repo.get("sesion-1") == "titulo corregido"


async def test_get_many_trae_solo_las_sesiones_pedidas(repo: SqlSessionTitleRepository) -> None:
    user = uuid4()
    await repo.upsert("sesion-1", user, "primera")
    await repo.upsert("sesion-2", user, "segunda")
    await repo.upsert("sesion-3", user, "tercera")

    result = await repo.get_many(["sesion-1", "sesion-3", "no-existe"])

    assert result == {"sesion-1": "primera", "sesion-3": "tercera"}


async def test_get_many_con_lista_vacia_no_pega_a_la_base(
    repo: SqlSessionTitleRepository,
) -> None:
    assert await repo.get_many([]) == {}


async def test_delete_quita_el_titulo(repo: SqlSessionTitleRepository) -> None:
    await repo.upsert("sesion-1", uuid4(), "SUV para la familia")

    await repo.delete("sesion-1")

    assert await repo.get("sesion-1") is None


async def test_delete_de_una_sesion_sin_titulo_no_falla(repo: SqlSessionTitleRepository) -> None:
    await repo.delete("no-existe")
