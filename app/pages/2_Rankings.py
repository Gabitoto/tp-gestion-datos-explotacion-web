import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.config import MIN_VOTOS_RANKING_CALIFICACION
from src.consultas import vistas

st.title("🏆 Rankings")
n = st.slider("Cantidad (Top N)", 5, 50, 10)
COLS = ["id", "titulo", "tipo", "anio", "calificacion", "votos",
        "puntaje_ponderado", "generos", "director"]


def tabla(filas):
    # reindex evita KeyError si la lista viene vacía o falta algún campo
    return pd.DataFrame(filas).reindex(columns=COLS)


try:
    tab1, tab2, tab3 = st.tabs(["Más votadas", "Mejor calificadas", "Mejor ponderadas"])
    with tab1:
        st.dataframe(tabla(vistas.top_por_votos(n)), width="stretch")
    with tab2:
        st.caption(f"Solo títulos con al menos {MIN_VOTOS_RANKING_CALIFICACION:,} votos.")
        st.dataframe(tabla(vistas.top_por_calificacion(n)), width="stretch")
    with tab3:
        st.caption("Puntaje bayesiano: penaliza notas altas con pocos votos.")
        st.dataframe(tabla(vistas.top_por_ponderado(n)), width="stretch")
except Exception as e:
    st.error(f"No se pudo consultar Redis: {e}")
