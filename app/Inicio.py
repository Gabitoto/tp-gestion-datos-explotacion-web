"""Página principal de la app Streamlit. Ejecutar: streamlit run app/Inicio.py"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.consultas import vistas
from src.ui import estilos

estilos.preparar_pagina(
    "Inicio", "🎬",
    "Catálogo IMDb sobre Redis: Hashes, Sets y Sorted Sets consultados en tiempo real.",
    ruta="Cine en Redis",
)

st.markdown(
    '<div style="display:flex;align-items:center;gap:18px;padding:14px 22px;margin-bottom:1.2rem;'
    'border-radius:16px;border:1px solid rgba(255,255,255,.06);'
    'background:linear-gradient(120deg,rgba(245,197,24,.12),rgba(220,56,44,.18));">'
    '<img src="https://upload.wikimedia.org/wikipedia/commons/6/69/IMDB_Logo_2016.svg" height="40" alt="IMDb">'
    '<span style="font-size:1.6rem;opacity:.6">＋</span>'
    '<img src="https://upload.wikimedia.org/wikipedia/commons/e/ee/Redis_logo.svg" height="34" alt="Redis">'
    '<span style="opacity:.75">Títulos de cine consultados en milisegundos.</span></div>',
    unsafe_allow_html=True,
)

try:
    total = vistas.total_peliculas()
    generos = vistas.conteo_por_genero()
    decadas = vistas.conteo_por_decada()
except Exception as e:
    st.error(f"No se pudo conectar a Redis o no hay datos cargados: {e}")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Total de producciones", f"{total:,}")
c2.metric("Géneros distintos", f"{len(generos):,}")
c3.metric("Décadas cubiertas", f"{len(decadas):,}")

st.markdown("### ¿Qué querés hacer?")
col1, col2, col3 = st.columns(3)
with col1, st.container(border=True):
    st.markdown("#### 📊 Dashboard")
    st.write("Cuatro visualizaciones con filtros por año, género, nota y votos.")
with col2, st.container(border=True):
    st.markdown("#### 🏆 Rankings")
    st.write("Más votadas, mejor calificadas y ponderadas, por género, década y tipo.")
with col3, st.container(border=True):
    st.markdown("#### 🔎 Explorador")
    st.write("Buscá por género, ID, director, actor, duración, nota y más.")

st.caption("Usá el menú lateral para navegar entre las vistas.")
