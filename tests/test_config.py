import importlib

import pytest

from src import config


def test_rutas_dentro_del_proyecto():
    assert config.DIR_RAW == config.RAIZ / "data" / "raw"
    assert config.DIR_PROCESADOS == config.RAIZ / "data" / "processed"
    assert config.ARCH_JSONL.parent == config.DIR_PROCESADOS
    assert all(a.parent == config.DIR_RAW for a in config.ARCHIVOS_RAW)


def test_cuatro_datasets_de_imdb():
    nombres = [a.name for a in config.ARCHIVOS_RAW]
    assert nombres == [
        "title.ratings.tsv.gz",
        "title.basics.tsv.gz",
        "title.principals.tsv.gz",
        "name.basics.tsv.gz",
    ]


@pytest.fixture
def config_recargable(monkeypatch):
    yield monkeypatch
    # Al terminar, se vuelve a cargar con el entorno original
    monkeypatch.undo()
    importlib.reload(config)


def test_redis_por_defecto(config_recargable):
    config_recargable.delenv("REDIS_HOST", raising=False)
    config_recargable.delenv("REDIS_PORT", raising=False)
    importlib.reload(config)
    assert config.REDIS_HOST == "localhost"
    assert config.REDIS_PORT == 6379


def test_redis_desde_variables_de_entorno(config_recargable):
    """Docker Compose inyecta REDIS_HOST=redis."""
    config_recargable.setenv("REDIS_HOST", "redis")
    config_recargable.setenv("REDIS_PORT", "6380")
    importlib.reload(config)
    assert config.REDIS_HOST == "redis"
    assert config.REDIS_PORT == 6380


def test_plantillas_de_claves():
    assert config.K_PELICULA.format(id="tt1") == "pelicula:tt1"
    assert config.K_FILTRO_GENERO.format(valor="Drama") == "filtro:genero:Drama"
    assert config.K_FILTRO_DECADA.format(valor="1990s") == "filtro:decada:1990s"
    assert config.K_FILTRO_DIRECTOR.format(valor="X") == "filtro:director:X"
    assert config.K_FILTRO_ACTOR.format(valor="Y") == "filtro:actor:Y"


def test_claves_unicas():
    claves = [
        config.K_RANKING_VOTOS, config.K_RANKING_CALIFICACION,
        config.K_RANKING_PONDERADO, config.K_KPI_TOTAL,
        config.K_KPI_GENEROS, config.K_KPI_DECADAS,
    ]
    assert len(set(claves)) == len(claves)
