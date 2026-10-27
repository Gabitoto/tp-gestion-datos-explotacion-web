"""Página principal de la app Streamlit. Ejecutar: streamlit run app/Inicio.py"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.consultas import vistas

st.set_page_config(page_title="Cine en Redis", page_icon="🎬", layout="wide")
st.title("🎬 Catálogo IMDb sobre Redis")
st.caption("Visualización de un modelo clave-valor: Hashes, Sets y Sorted Sets.")

try:
    st.metric("Total de producciones", f"{vistas.total_peliculas():,}")
except Exception as e:
    st.error(f"No se pudo conectar a Redis o no hay datos cargados: {e}")
    st.stop()

st.info("Usá el menú lateral: Dashboard, Rankings y Explorador.")
