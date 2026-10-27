import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.consultas import vistas

st.title("🔎 Explorador")

try:
    generos_disponibles = vistas.lista_generos()
except Exception as e:
    st.error(f"No se pudo consultar Redis: {e}")
    st.stop()

tab1, tab2 = st.tabs(["Por género", "Por ID"])
with tab1:
    genero = st.selectbox("Género", generos_disponibles)
    if genero:
        st.dataframe(pd.DataFrame(vistas.peliculas_por_genero(genero)), width="stretch")
with tab2:
    tconst = st.text_input("ID IMDb (ej. tt0111161)")
    if tconst:
        st.json(vistas.ficha_pelicula(tconst.strip()) or {"error": "No encontrada"})
