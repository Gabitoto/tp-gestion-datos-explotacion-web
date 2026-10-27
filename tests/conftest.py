"""Fixtures compartidos. Ningún test usa red, Redis real ni los datasets de IMDb."""
import copy
import gzip
import json

import pytest

REGISTROS_EJEMPLO = [
    {
        "id": "tt0000001", "tipo": "Película", "titulo": "Matrix",
        "titulo_original": "The Matrix", "es_adulto": False, "anio": 1999,
        "anio_fin": 0, "duracion": 136, "rango_duracion": "Larga (120-180m)",
        "calificacion": 8.7, "votos": 2000000, "puntaje_ponderado": 8.7,
        "nivel_popularidad": "Blockbuster (> 50K)",
        "generos": ["Acción", "Ciencia ficción"],
        "director": "Lana Wachowski, Lilly Wachowski",
        "guionista": "Lilly Wachowski",
        "actores": "Keanu Reeves, Carrie-Anne Moss",
    },
    {
        "id": "tt0000002", "tipo": "Serie", "titulo": "Serie Rara",
        "titulo_original": "Serie Rara", "es_adulto": False, "anio": 2015,
        "anio_fin": 2017, "duracion": 45, "rango_duracion": "Corta (< 60m)",
        "calificacion": 9.8, "votos": 12, "puntaje_ponderado": 7.84,
        "nivel_popularidad": "Baja (1-100)", "generos": ["Drama"],
        "director": "Desconocido", "guionista": "Desconocido",
        "actores": "Keanu Reeves",
    },
    {
        "id": "tt0000003", "tipo": "Película", "titulo": "Sin Año",
        "titulo_original": "Sin Año", "es_adulto": False, "anio": 0,
        "anio_fin": 0, "duracion": 0, "rango_duracion": "No especificada",
        "calificacion": 6.0, "votos": 150000, "puntaje_ponderado": 6.0,
        "nivel_popularidad": "Blockbuster (> 50K)",
        "generos": ["Drama", "Acción"], "director": "Ana Directora",
        "guionista": "Desconocido", "actores": "Desconocido",
    },
]


@pytest.fixture
def registros():
    return copy.deepcopy(REGISTROS_EJEMPLO)


@pytest.fixture
def jsonl_ejemplo(tmp_path, registros):
    ruta = tmp_path / "peliculas_limpias.jsonl"
    with open(ruta, "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return ruta


@pytest.fixture
def escribir_tsv_gz():
    """Factory: escribe un .tsv.gz con encabezado + filas (listas de strings)."""
    def _escribir(ruta, encabezado, filas):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(ruta, "wt", encoding="utf-8") as f:
            f.write("\t".join(encabezado) + "\n")
            for fila in filas:
                f.write("\t".join(fila) + "\n")
        return ruta
    return _escribir


@pytest.fixture
def fake_redis():
    fakeredis = pytest.importorskip("fakeredis")
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def redis_cargado(fake_redis, jsonl_ejemplo, monkeypatch, capsys):
    """Redis falso con los 3 registros de ejemplo, inyectado en la capa de consultas."""
    from src.carga_redis.cargar_redis import cargar_a_redis
    from src.consultas import conexion

    cargar_a_redis(r=fake_redis, archivo=jsonl_ejemplo)
    capsys.readouterr()  # descarta la salida de la carga
    monkeypatch.setattr(conexion, "_cliente", fake_redis)
    return fake_redis
