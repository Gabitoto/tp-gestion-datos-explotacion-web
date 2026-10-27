"""Smoke tests de la app Streamlit con AppTest (sin navegador ni servidor)."""
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

import redis  # noqa: E402

from src.consultas import conexion  # noqa: E402

APP = Path(__file__).resolve().parent.parent / "app"


def correr(script):
    return AppTest.from_file(str(APP / script), default_timeout=30).run()


def test_inicio_muestra_total(redis_cargado):
    at = correr("Inicio.py")
    assert not at.exception
    assert at.metric[0].value == "3"


class RedisCaido:
    def __getattr__(self, nombre):
        def falla(*a, **k):
            raise redis.ConnectionError("Redis apagado")
        return falla


def test_inicio_sin_redis_muestra_error(monkeypatch):
    monkeypatch.setattr(conexion, "_cliente", RedisCaido())
    at = correr("Inicio.py")
    assert not at.exception
    assert len(at.error) == 1


@pytest.mark.parametrize("pagina", ["pages/1_Dashboard.py", "pages/2_Rankings.py", "pages/3_Explorador.py"])
def test_paginas_sin_redis_no_explotan(pagina, monkeypatch):
    monkeypatch.setattr(conexion, "_cliente", RedisCaido())
    at = correr(pagina)
    assert not at.exception
    assert len(at.error) >= 1


def test_dashboard_renderiza(redis_cargado):
    at = correr("pages/1_Dashboard.py")
    assert not at.exception
    assert not at.error


def test_rankings_tres_tablas(redis_cargado):
    at = correr("pages/2_Rankings.py")
    assert not at.exception
    assert len(at.dataframe) == 3


def test_explorador_lista_generos(redis_cargado):
    at = correr("pages/3_Explorador.py")
    assert not at.exception
    assert set(at.selectbox[0].options) == {"Acción", "Drama", "Ciencia ficción"}
