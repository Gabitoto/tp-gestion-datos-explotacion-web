from src.consultas import vistas


def test_normalizar_ficha(redis_cargado):
    f = vistas.normalizar_ficha(vistas.ficha_pelicula("tt0000001"))
    assert f["anio"] == 1999 and f["votos"] == 2000000
    assert f["calificacion"] == 8.7
    assert f["generos"] == ["Acción", "Ciencia ficción"]


def test_muestra_peliculas(redis_cargado):
    m = vistas.muestra_peliculas(2)
    assert [f["id"] for f in m] == ["tt0000001", "tt0000003"]


def test_lista_decadas(redis_cargado):
    assert vistas.lista_decadas() == ["1990s", "2010s"]


def test_top_filtrado_por_genero(redis_cargado):
    ids = [f["id"] for f in vistas.top_filtrado("votos", 10, genero="Drama")]
    assert ids == ["tt0000003", "tt0000002"]
    assert redis_cargado.keys("tmp:*") == []  # limpia el ZSet temporal


def test_top_filtrado_genero_y_decada(redis_cargado):
    ids = [f["id"] for f in vistas.top_filtrado("ponderado", 10, genero="Drama", decada="2010s")]
    assert ids == ["tt0000002"]


def test_top_filtrado_tipo_y_min_votos(redis_cargado):
    assert [f["id"] for f in vistas.top_filtrado("ponderado", 10, tipo="Serie")] == ["tt0000002"]
    assert [f["id"] for f in vistas.top_filtrado("calificacion", 10, min_votos=500_000)] == ["tt0000001"]
    assert vistas.top_filtrado("votos", 10, genero="Inexistente") == []


def test_buscar_peliculas_por_director_actor(redis_cargado):
    assert [f["id"] for f in vistas.buscar_peliculas(director="Ana Directora")] == ["tt0000003"]
    ids = [f["id"] for f in vistas.buscar_peliculas(actor="Keanu Reeves")]
    assert ids == ["tt0000001", "tt0000002"]


def test_buscar_peliculas_filtros_de_rango(redis_cargado):
    assert [f["id"] for f in vistas.buscar_peliculas(duracion=(100, 200))] == ["tt0000001"]
    assert [f["id"] for f in vistas.buscar_peliculas(calif_min=9.0)] == ["tt0000002"]
    assert [f["id"] for f in vistas.buscar_peliculas(votos_min=1_000_000)] == ["tt0000001"]
    assert [f["id"] for f in vistas.buscar_peliculas(texto="matr")] == ["tt0000001"]
    assert len(vistas.buscar_peliculas(limite=2)) == 2
    assert vistas.buscar_peliculas(genero="Drama", director="Nadie") == []


def test_buscar_nombres_insensible_a_mayusculas(redis_cargado):
    assert vistas.buscar_nombres("actor", "keanu") == ["Keanu Reeves"]
    assert vistas.buscar_nombres("director", "WACHOWSKI") == ["Lana Wachowski", "Lilly Wachowski"]
    assert vistas.buscar_nombres("actor", "") == []

