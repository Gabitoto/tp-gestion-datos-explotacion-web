from src.exploracion.contar_filas import contar
from src.exploracion.explorar_columnas import explorar
from src.validacion.auditar_jsonl import auditar


def test_explorar_devuelve_columnas(tmp_path, escribir_tsv_gz, capsys):
    ruta = escribir_tsv_gz(tmp_path / "a.tsv.gz", ["tconst", "numVotes"],
                           [["tt1", "10"], ["tt2", "20"], ["tt3", "30"], ["tt4", "40"]])
    columnas = explorar([ruta], filas_ejemplo=2)
    salida = capsys.readouterr().out
    assert columnas == {"a.tsv.gz": ["tconst", "numVotes"]}
    assert "tt2" in salida and "tt3" not in salida


def test_contar_excluye_encabezado(tmp_path, escribir_tsv_gz, capsys):
    a = escribir_tsv_gz(tmp_path / "a.tsv.gz", ["x"], [["1"], ["2"], ["3"]])
    b = escribir_tsv_gz(tmp_path / "b.tsv.gz", ["x"], [])
    assert contar([a, b]) == {"a.tsv.gz": 3, "b.tsv.gz": 0}


def test_auditar_archivo_inexistente(tmp_path, capsys):
    assert auditar(tmp_path / "no_existe.jsonl") is None
    assert "Error" in capsys.readouterr().out


def test_auditar_jsonl_valido(jsonl_ejemplo, capsys):
    resultado = auditar(jsonl_ejemplo)
    assert resultado["registros"] == 3
    assert resultado["mb"] > 0
    assert resultado["primer_registro"]["titulo"] == "Matrix"


def test_auditar_jsonl_vacio(tmp_path, capsys):
    vacio = tmp_path / "vacio.jsonl"
    vacio.write_text("", encoding="utf-8")
    resultado = auditar(vacio)
    assert resultado["registros"] == 0
    assert resultado["primer_registro"] is None
