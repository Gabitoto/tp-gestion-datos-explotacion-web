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
