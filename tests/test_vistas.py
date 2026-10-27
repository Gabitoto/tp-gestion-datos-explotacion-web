import pytest

from src.consultas import conexion, vistas


def test_total_peliculas(redis_cargado):
    assert vistas.total_peliculas() == 3


def test_total_con_base_vacia(fake_redis, monkeypatch):
    monkeypatch.setattr(conexion, "_cliente", fake_redis)
    assert vistas.total_peliculas() == 0
    assert vistas.conteo_por_genero() == {}
    assert vistas.conteo_por_decada() == {}
    assert vistas.top_por_votos() == []


def test_conteo_por_genero_ordenado_desc(redis_cargado):
    conteo = vistas.conteo_por_genero()
    assert conteo == {"Acción": 2, "Drama": 2, "Ciencia ficción": 1}
    assert list(conteo.values()) == sorted(conteo.values(), reverse=True)


def test_conteo_por_decada_ordenado_cronologicamente(redis_cargado):
    assert list(vistas.conteo_por_decada().items()) == [("1990s", 1), ("2010s", 1)]


def test_top_por_votos(redis_cargado):
    top = vistas.top_por_votos(2)
    assert [f["id"] for f in top] == ["tt0000001", "tt0000003"]
    assert top[0]["titulo"] == "Matrix"
    assert top[0]["score"] == 2000000


def test_top_por_calificacion_excluye_pocos_votos(redis_cargado):
    ids = [f["id"] for f in vistas.top_por_calificacion(10)]
    assert ids == ["tt0000001", "tt0000003"]


def test_top_por_ponderado(redis_cargado):
    ids = [f["id"] for f in vistas.top_por_ponderado(10)]
    assert ids == ["tt0000001", "tt0000002", "tt0000003"]


def test_ficha_pelicula(redis_cargado):
    assert vistas.ficha_pelicula("tt0000002")["titulo"] == "Serie Rara"
    assert vistas.ficha_pelicula("tt9999999") == {}


def test_peliculas_por_genero_respeta_limite(redis_cargado):
    assert len(vistas.peliculas_por_genero("Drama", limite=1)) == 1
    titulos = {f["titulo"] for f in vistas.peliculas_por_genero("Drama")}
    assert titulos == {"Serie Rara", "Sin Año"}
    assert vistas.peliculas_por_genero("Inexistente") == []


def test_lista_generos(redis_cargado):
    assert set(vistas.lista_generos()) == {"Acción", "Drama", "Ciencia ficción"}


def test_get_redis_reutiliza_cliente_y_tiene_timeout(monkeypatch):
    monkeypatch.setattr(conexion, "_cliente", None)
    cliente = conexion.get_redis()
    assert conexion.get_redis() is cliente
    kwargs = cliente.connection_pool.connection_kwargs
    assert kwargs["socket_connect_timeout"] is not None
    assert kwargs["decode_responses"] is True
