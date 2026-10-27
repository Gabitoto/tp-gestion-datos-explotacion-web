"""Verifica que el repositorio coincida con lo documentado en el README y que Docker esté bien armado."""
import importlib
import importlib.util
import re
import urllib.request
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

ARCHIVOS_DOCUMENTADOS = [
    "src/config.py",
    "src/exploracion/explorar_columnas.py",
    "src/exploracion/contar_filas.py",
    "src/etl/etl.py",
    "src/validacion/auditar_jsonl.py",
    "src/carga_redis/cargar_redis.py",
    "src/carga_redis/prototipo_streaming.py",
    "src/consultas/conexion.py",
    "src/consultas/vistas.py",
    "app/Inicio.py",
    "app/pages/1_Dashboard.py",
    "app/pages/2_Rankings.py",
    "app/pages/3_Explorador.py",
    "pipeline.py",
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    "requirements.txt",
    "README.md",
]

MODULOS = [
    "src.config",
    "src.exploracion.explorar_columnas",
    "src.exploracion.contar_filas",
    "src.etl.etl",
    "src.validacion.auditar_jsonl",
    "src.carga_redis.cargar_redis",
    "src.carga_redis.prototipo_streaming",
    "src.consultas.conexion",
    "src.consultas.vistas",
]


def leer(ruta):
    return (RAIZ / ruta).read_text(encoding="utf-8")


@pytest.mark.parametrize("ruta", ARCHIVOS_DOCUMENTADOS)
def test_archivo_documentado_existe(ruta):
    assert (RAIZ / ruta).is_file(), f"Falta {ruta}"


def test_carpetas_de_datos_existen():
    assert (RAIZ / "data" / "raw").is_dir()
    assert (RAIZ / "data" / "processed").is_dir()


@pytest.mark.parametrize("modulo", MODULOS)
def test_importar_modulo_no_tiene_efectos_secundarios(modulo, monkeypatch, capsys):
    """Importar no debe descargar nada ni imprimir (todo va detrás de __main__)."""
    def prohibido(*a, **k):
        raise AssertionError(f"{modulo} accede a la red al importarse")

    monkeypatch.setattr(urllib.request, "urlopen", prohibido)
    importlib.reload(importlib.import_module(modulo))
    assert capsys.readouterr().out == ""


def test_modulos_python_m_del_readme_existen():
    readme = leer("README.md")
    for modulo in re.findall(r"python(?:\.exe)?\s+-m\s+(src(?:\.\w+)+)", readme):
        assert importlib.util.find_spec(modulo), f"README referencia {modulo}, que no existe"


def test_requirements():
    reqs = leer("requirements.txt").lower().split()
    for paquete in ("redis", "streamlit", "pandas"):
        assert paquete in reqs


# ---------- Docker ----------

def test_dockerfile():
    df = leer("Dockerfile")
    assert re.search(r"^FROM python:3\.\d+", df, re.M)
    assert "pip install --no-cache-dir -r requirements.txt" in df
    for origen in ("src/", "app/", "pipeline.py"):
        assert f"COPY {origen}" in df
    assert "EXPOSE 8501" in df
    assert "app/Inicio.py" in df
    assert "--server.address=0.0.0.0" in df


def test_docker_compose_servicios_y_red():
    dc = leer("docker-compose.yml")
    assert re.search(r"^  redis:", dc, re.M)
    assert re.search(r"^  app:", dc, re.M)
    assert "REDIS_HOST=redis" in dc
    assert '"8501:8501"' in dc
    assert '"6379:6379"' in dc
    assert "condition: service_healthy" in dc
    assert "redis-cli" in dc
    assert "./data:/app/data" in dc
    assert not re.search(r"^version:", dc, re.M), "El atributo 'version' está obsoleto"


def test_dockerignore_excluye_pesados():
    ignorados = leer(".dockerignore").split()
    for patron in (".venv/", "data/raw/*.tsv.gz", "data/processed/*.jsonl"):
        assert patron in ignorados


def test_gitignore_excluye_datos():
    gi = leer(".gitignore")
    assert "data/raw/*" in gi and "data/processed/*" in gi
