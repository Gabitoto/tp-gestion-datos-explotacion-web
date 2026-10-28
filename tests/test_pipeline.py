import io
import re
import socket
from pathlib import Path

import pytest

import pipeline

RAIZ = Path(__file__).resolve().parent.parent


# ---------- CLI ----------

@pytest.mark.parametrize("flag", ["--descargar", "--explorar", "--etl", "--auditar",
                                  "--cargar-redis", "--todo", "--estado"])
def test_parser_acepta_flags(flag):
    pipeline.construir_parser().parse_args([flag])


def test_flags_documentados_en_readme_existen():
    """Todo comando 'pipeline.py --x' que figure en el README debe ser válido."""
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    flags = set(re.findall(r"pipeline\.py\s+(--[a-z-]+)", readme))
    assert flags, "El README no documenta ningún comando de pipeline.py"
    parser = pipeline.construir_parser()
    for flag in flags:
        parser.parse_args([flag])


def test_flag_invalido_sale_con_error():
    with pytest.raises(SystemExit):
        pipeline.construir_parser().parse_args(["--no-existe"])


class Registro(list):
    """Lista de llamadas que además guarda el resultado simulado de la auditoría."""
    auditoria_ok = None


@pytest.fixture
def llamadas(monkeypatch):
    """Reemplaza cada fase por un registrador de llamadas."""
    registro = Registro()
    auditoria_ok = {"valor": True}

    monkeypatch.setattr(pipeline, "descargar_archivos_raw", lambda: registro.append("descargar"))
    monkeypatch.setattr(pipeline, "ejecutar_exploracion", lambda: registro.append("explorar"))
    monkeypatch.setattr(pipeline, "ejecutar_etl", lambda: registro.append("etl"))
    monkeypatch.setattr(pipeline, "ejecutar_carga_redis", lambda: registro.append("cargar"))
    monkeypatch.setattr(pipeline, "verificar_estado", lambda: registro.append("estado"))

    def auditar():
        registro.append("auditar")
        return auditoria_ok["valor"]

    monkeypatch.setattr(pipeline, "ejecutar_auditoria", auditar)
    registro.auditoria_ok = auditoria_ok
    return registro


def test_sin_argumentos_muestra_estado(llamadas, capsys):
    assert pipeline.main([]) == 0
    assert llamadas == ["estado"]


def test_todo_ejecuta_fases_en_orden(llamadas):
    assert pipeline.main(["--todo"]) == 0
    assert llamadas == ["descargar", "etl", "auditar", "cargar", "estado"]


def test_todo_no_carga_si_la_auditoria_falla(llamadas, capsys):
    llamadas.auditoria_ok["valor"] = False
    assert pipeline.main(["--todo"]) == 1
    assert "cargar" not in llamadas


def test_fases_combinadas_respetan_el_orden(llamadas):
    pipeline.main(["--cargar-redis", "--etl", "--descargar"])
    assert llamadas == ["descargar", "etl", "cargar"]


def test_explorar_ejecuta_exploracion(llamadas):
    pipeline.main(["--explorar"])
    assert llamadas == ["explorar"]


# ---------- Fases reales (sin red) ----------

def test_descarga_omite_archivos_existentes(tmp_path, monkeypatch, capsys):
    existente = tmp_path / "title.ratings.tsv.gz"
    existente.write_bytes(b"datos")

    def no_llamar(*a, **k):
        raise AssertionError("No debería descargar")

    monkeypatch.setattr(pipeline, "DIR_RAW", tmp_path)
    monkeypatch.setattr(pipeline, "URLS_IMDB", {existente: "https://ejemplo/x"})
    monkeypatch.setattr(pipeline.urllib.request, "urlopen", no_llamar)
    pipeline.descargar_archivos_raw()
    assert "Ya existe" in capsys.readouterr().out


class RespuestaFalsa(io.BytesIO):
    def info(self):
        return {"Content-Length": str(len(self.getvalue()))}


def test_descarga_archivo_faltante(tmp_path, monkeypatch, capsys):
    destino = tmp_path / "name.basics.tsv.gz"
    monkeypatch.setattr(pipeline, "DIR_RAW", tmp_path)
    monkeypatch.setattr(pipeline, "URLS_IMDB", {destino: "https://ejemplo/y"})
    monkeypatch.setattr(pipeline.urllib.request, "urlopen", lambda req: RespuestaFalsa(b"contenido"))
    pipeline.descargar_archivos_raw()
    assert destino.read_bytes() == b"contenido"
    assert not (tmp_path / "name.basics.tsv.gz.part").exists()


def test_descarga_interrumpida_no_deja_archivo_corrupto(tmp_path, monkeypatch, capsys):
    destino = tmp_path / "title.basics.tsv.gz"

    class RespuestaQueFalla(RespuestaFalsa):
        def read(self, *a):
            raise ConnectionResetError("corte de red")

    monkeypatch.setattr(pipeline, "DIR_RAW", tmp_path)
    monkeypatch.setattr(pipeline, "URLS_IMDB", {destino: "https://ejemplo/z"})
    monkeypatch.setattr(pipeline.urllib.request, "urlopen", lambda req: RespuestaQueFalla(b"x"))
    with pytest.raises(ConnectionResetError):
        pipeline.descargar_archivos_raw()
    assert not destino.exists()
    assert not (tmp_path / "title.basics.tsv.gz.part").exists()


def test_auditoria_falla_sin_jsonl(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pipeline, "ARCH_JSONL", tmp_path / "no.jsonl")
    assert pipeline.ejecutar_auditoria() is False


def test_auditoria_ok_con_jsonl(jsonl_ejemplo, monkeypatch, capsys):
    monkeypatch.setattr(pipeline, "ARCH_JSONL", jsonl_ejemplo)
    assert pipeline.ejecutar_auditoria() is True


@pytest.fixture
def sin_red(monkeypatch):
    def rechazar(*a, **k):
        raise ConnectionRefusedError()
    monkeypatch.setattr(socket, "create_connection", rechazar)


def test_redis_disponible_false_si_no_hay_servidor(sin_red):
    assert pipeline.redis_disponible() is False


def test_estado_reporta_faltantes_y_redis_caido(tmp_path, monkeypatch, sin_red, capsys):
    for nombre in ["ARCH_RATINGS", "ARCH_BASICS", "ARCH_PRINCIPALS", "ARCH_NAMES"]:
        monkeypatch.setattr(pipeline, nombre, tmp_path / f"{nombre}.gz")
    monkeypatch.setattr(pipeline, "ARCH_JSONL", tmp_path / "x.jsonl")
    pipeline.verificar_estado()
    salida = capsys.readouterr().out
    assert salida.count("FALTA") == 5
    assert "No se pudo conectar a Redis" in salida
