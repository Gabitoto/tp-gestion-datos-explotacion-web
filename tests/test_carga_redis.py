import pytest

from src.carga_redis import cargar_redis
from src.carga_redis.cargar_redis import cargar_a_redis, decada_de


@pytest.mark.parametrize("anio,esperado", [
    (1999, "1990s"), (2000, "2000s"), (1895, "1890s"), (0, None), (-1, None), (None, None),
])
def test_decada_de(anio, esperado):
    assert decada_de(anio) == esperado


@pytest.fixture
def cargado(fake_redis, jsonl_ejemplo, capsys):
    total = cargar_a_redis(r=fake_redis, archivo=jsonl_ejemplo)
    capsys.readouterr()
    return fake_redis, total


def test_devuelve_cantidad_y_contador_global(cargado):
    r, total = cargado
    assert total == 3
    assert r.get("kpi:total_peliculas") == "3"


def test_hash_de_pelicula(cargado):
    r, _ = cargado
    ficha = r.hgetall("pelicula:tt0000001")
    assert ficha["titulo"] == "Matrix"
    assert ficha["tipo"] == "Película"
    assert ficha["votos"] == "2000000"
    assert ficha["generos"] == "Acción, Ciencia ficción"
    assert ficha["director"] == "Lana Wachowski, Lilly Wachowski"


def test_filtros_por_genero_y_kpi(cargado):
    r, _ = cargado
    assert r.smembers("filtro:genero:Acción") == {"tt0000001", "tt0000003"}
    assert r.smembers("filtro:genero:Drama") == {"tt0000002", "tt0000003"}
    assert r.hgetall("kpi:generos:conteo") == {"Acción": "2", "Ciencia ficción": "1", "Drama": "2"}


def test_decadas_ignoran_anio_desconocido(cargado):
    r, _ = cargado
    assert r.smembers("filtro:decada:1990s") == {"tt0000001"}
    assert r.smembers("filtro:decada:2010s") == {"tt0000002"}
    assert not r.exists("filtro:decada:0s")
    assert r.hgetall("kpi:decadas:conteo") == {"1990s": "1", "2010s": "1"}


def test_filtros_por_persona(cargado):
    r, _ = cargado
    assert r.smembers("filtro:director:Lana Wachowski") == {"tt0000001"}
    assert r.smembers("filtro:actor:Keanu Reeves") == {"tt0000001", "tt0000002"}
    assert not r.exists("filtro:director:Desconocido")
    assert not r.exists("filtro:actor:Desconocido")


def test_ranking_por_votos(cargado):
    r, _ = cargado
    assert r.zrevrange("ranking:votos", 0, -1) == ["tt0000001", "tt0000003", "tt0000002"]


def test_ranking_calificacion_exige_minimo_de_votos(cargado):
    r, _ = cargado
    # tt0000002 tiene nota 9.8 pero solo 12 votos: no debe encabezar el ranking
    assert r.zrevrange("ranking:calificacion", 0, -1) == ["tt0000001", "tt0000003"]


def test_ranking_ponderado_incluye_todo(cargado):
    r, _ = cargado
    assert r.zcard("ranking:ponderado") == 3
    assert r.zscore("ranking:ponderado", "tt0000002") == pytest.approx(7.84)


def test_limpiar_borra_datos_previos(fake_redis, jsonl_ejemplo, capsys):
    fake_redis.set("basura", "1")
    cargar_a_redis(r=fake_redis, archivo=jsonl_ejemplo, limpiar=True)
    assert not fake_redis.exists("basura")


def test_sin_limpiar_conserva_datos_previos(fake_redis, jsonl_ejemplo, capsys):
    fake_redis.set("previo", "1")
    cargar_a_redis(r=fake_redis, archivo=jsonl_ejemplo, limpiar=False)
    assert fake_redis.get("previo") == "1"


def test_lotes_pequenos_no_pierden_datos(fake_redis, jsonl_ejemplo, monkeypatch, capsys):
    monkeypatch.setattr(cargar_redis, "TAMANIO_LOTE", 1)
    assert cargar_a_redis(r=fake_redis, archivo=jsonl_ejemplo) == 3
    assert fake_redis.zcard("ranking:votos") == 3


def test_ignora_lineas_vacias(fake_redis, jsonl_ejemplo, capsys):
    with open(jsonl_ejemplo, "a", encoding="utf-8") as f:
        f.write("\n\n")
    assert cargar_a_redis(r=fake_redis, archivo=jsonl_ejemplo) == 3
