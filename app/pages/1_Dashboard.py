import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.consultas import vistas

st.title("📊 Dashboard")

try:
    generos = vistas.conteo_por_genero()
    decadas = vistas.conteo_por_decada()
except Exception as e:
    st.error(f"No se pudo consultar Redis: {e}")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Producciones por género")
    st.bar_chart(pd.Series(generos, dtype="int64").head(20))
with col2:
    st.subheader("Producciones por década")
    st.line_chart(pd.Series(decadas, dtype="int64"))
