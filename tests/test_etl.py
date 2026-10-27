import json

import pytest

from src.etl import etl


# ---------- Funciones puras ----------

@pytest.mark.parametrize("minutos,esperado", [
    (0, "No especificada"),
    (-5, "No especificada"),
    (59, "Corta (< 60m)"),
    (60, "Estándar (60-120m)"),
    (120, "Estándar (60-120m)"),
    (121, "Larga (120-180m)"),
    (180, "Larga (120-180m)"),
    (181, "Épica (> 180m)"),
])
def test_clasificar_duracion(minutos, esperado):
    assert etl.clasificar_duracion(minutos) == esperado


@pytest.mark.parametrize("votos,esperado", [
    (1, "Baja (1-100)"),
    (100, "Baja (1-100)"),
    (101, "Media (101-5K)"),
    (5000, "Media (101-5K)"),
    (5001, "Alta (5K-50K)"),
    (50000, "Alta (5K-50K)"),
    (50001, "Blockbuster (> 50K)"),
])
def test_clasificar_popularidad_respeta_etiquetas(votos, esperado):
    assert etl.clasificar_popularidad(votos) == esperado


def test_puntaje_ponderado_sin_votos_es_promedio_global():
    assert etl.calcular_puntaje_ponderado(10.0, 0) == etl.C_PROMEDIO_GLOBAL


def test_puntaje_ponderado_valor_conocido():
    # (1000/1025)*8.0 + (25/1025)*6.9 = 7.973...
    assert etl.calcular_puntaje_ponderado(8.0, 1000) == 7.97


def test_puntaje_ponderado_con_muchos_votos_tiende_a_la_nota():
    assert etl.calcular_puntaje_ponderado(9.3, 3_000_000) == pytest.approx(9.3, abs=0.01)


@pytest.mark.parametrize("nota,votos", [(10.0, 1), (1.0, 5), (8.5, 300), (2.0, 10_000)])
def test_puntaje_ponderado_queda_entre_nota_y_promedio(nota, votos):
    wr = etl.calcular_puntaje_ponderado(nota, votos)
    assert min(nota, etl.C_PROMEDIO_GLOBAL) - 0.01 <= wr <= max(nota, etl.C_PROMEDIO_GLOBAL) + 0.01


def test_diccionarios_de_traduccion():
    assert etl.MAPEO_TIPOS["movie"] == "Película"
    assert etl.DICC_GENEROS["Sci-Fi"] == "Ciencia ficción"
    assert etl.DICC_GENEROS["Thriller"] == "Suspenso"
    assert len(etl.DICC_GENEROS) == 22


# ---------- Pipeline completo con datasets en miniatura ----------

@pytest.fixture
def datasets_mini(tmp_path, escribir_tsv_gz, monkeypatch):
    raw = tmp_path / "raw"
    salida = tmp_path / "processed" / "peliculas_limpias.jsonl"  # carpeta inexistente a propósito

    escribir_tsv_gz(raw / "ratings.tsv.gz", ["tconst", "averageRating", "numVotes"], [
        ["tt1", "8.0", "1000"],
        ["tt2", "5.0", "10"],
        ["tt3", "9.0", "0"],      # sin votos -> excluido
        ["tt4", "7.0", "50"],     # tipo 'short' -> excluido
        ["tt5", "6.5", "200"],    # adulto -> incluido
    ])
    escribir_tsv_gz(raw / "basics.tsv.gz",
        ["tconst", "titleType", "primaryTitle", "originalTitle", "isAdult",
         "startYear", "endYear", "runtimeMinutes", "genres"], [
        ["tt1", "movie", "Peli Uno", "Peli Uno Orig", "0", "1999", "\\N", "136", "Action,Sci-Fi"],
        ["tt2", "tvSeries", "Serie Dos", "Serie Dos", "0", "2010", "2015", "45", "Drama"],
        ["tt3", "movie", "Sin Votos", "Sin Votos", "0", "2000", "\\N", "90", "Comedy"],
        ["tt4", "short", "Corto", "Corto", "0", "2001", "\\N", "5", "Animation"],
        ["tt5", "movie", "Adulta", "Adulta", "1", "2005", "\\N", "\\N", "\\N"],
        ["tt6", "movie", "Sin Rating", "Sin Rating", "0", "2006", "\\N", "100", "Drama"],
    ])
    principals = [
        ["tt1", "1", "nm1", "director", "\\N", "\\N"],
        ["tt1", "2", "nm2", "director", "\\N", "\\N"],
        ["tt1", "3", "nm3", "director", "\\N", "\\N"],  # 3er director -> ignorado
        ["tt1", "4", "nm4", "writer", "\\N", "\\N"],
        ["tt1", "5", "nm5", "producer", "\\N", "\\N"],  # rol no usado
    ]
    principals += [["tt1", str(10 + i), f"nm{10 + i}", "actor" if i % 2 else "actress", "\\N", "\\N"]
                   for i in range(7)]  # 7 actores -> se guardan 6
    principals += [["tt2", "1", "nm10", "actor", "\\N", "\\N"],
                   ["tt3", "1", "nm11", "actor", "\\N", "\\N"]]
    escribir_tsv_gz(raw / "principals.tsv.gz",
                    ["tconst", "ordering", "nconst", "category", "job", "characters"], principals)

    nombres = [["nm1", "Dir Uno"], ["nm2", "Dir Dos"], ["nm3", "Dir Tres"],
               ["nm4", "Guion Uno"], ["nm5", "Prod"]]
    nombres += [[f"nm{10 + i}", f"Actor {10 + i}"] for i in range(7)]
    escribir_tsv_gz(raw / "names.tsv.gz", ["nconst", "primaryName", "birthYear"],
                    [n + ["\\N"] for n in nombres])

    monkeypatch.setattr(etl, "ARCH_RATINGS", raw / "ratings.tsv.gz")
    monkeypatch.setattr(etl, "ARCH_BASICS", raw / "basics.tsv.gz")
    monkeypatch.setattr(etl, "ARCH_PRINCIPALS", raw / "principals.tsv.gz")
    monkeypatch.setattr(etl, "ARCH_NAMES", raw / "names.tsv.gz")
    monkeypatch.setattr(etl, "ARCH_SALIDA", salida)
    return salida


@pytest.fixture
def resultado_etl(datasets_mini, capsys):
    etl.ejecutar_etl(umbral_votos=1)
    capsys.readouterr()
    with open(datasets_mini, encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, f)}


def test_etl_crea_carpeta_de_salida_y_archivo(resultado_etl, datasets_mini):
    assert datasets_mini.exists()


def test_etl_filtra_tipos_votos_y_ratings(resultado_etl):
    assert set(resultado_etl) == {"tt1", "tt2", "tt5"}


def test_etl_esquema_completo(resultado_etl):
    campos = {"id", "tipo", "titulo", "titulo_original", "es_adulto", "anio",
              "anio_fin", "duracion", "rango_duracion", "calificacion", "votos",
              "puntaje_ponderado", "nivel_popularidad", "generos", "director",
              "guionista", "actores"}
    for registro in resultado_etl.values():
        assert set(registro) == campos


def test_etl_transforma_pelicula(resultado_etl):
    p = resultado_etl["tt1"]
    assert p["tipo"] == "Película"
    assert p["titulo"] == "Peli Uno"
    assert p["titulo_original"] == "Peli Uno Orig"
    assert p["anio"] == 1999 and p["anio_fin"] == 0
    assert p["generos"] == ["Acción", "Ciencia ficción"]
    assert p["rango_duracion"] == "Larga (120-180m)"
    assert p["nivel_popularidad"] == "Media (101-5K)"
    assert p["puntaje_ponderado"] == 7.97


def test_etl_limita_directores_y_actores(resultado_etl):
    p = resultado_etl["tt1"]
    assert p["director"] == "Dir Uno, Dir Dos"
    assert p["guionista"] == "Guion Uno"
    assert p["actores"].split(", ") == [f"Actor {10 + i}" for i in range(6)]


def test_etl_serie_sin_director(resultado_etl):
    s = resultado_etl["tt2"]
    assert s["tipo"] == "Serie"
    assert s["anio_fin"] == 2015
    assert s["director"] == "Desconocido"
    assert s["guionista"] == "Desconocido"
    assert s["actores"] == "Actor 10"
    assert s["nivel_popularidad"] == "Baja (1-100)"


def test_etl_incluye_adultos_y_campos_nulos(resultado_etl):
    a = resultado_etl["tt5"]
    assert a["es_adulto"] is True
    assert a["generos"] == []
    assert a["duracion"] == 0
    assert a["rango_duracion"] == "No especificada"
    assert a["actores"] == "Desconocido"


def test_etl_umbral_de_votos(datasets_mini, capsys):
    etl.ejecutar_etl(umbral_votos=500)
    capsys.readouterr()
    with open(datasets_mini, encoding="utf-8") as f:
        ids = {json.loads(l)["id"] for l in f}
    assert ids == {"tt1"}
