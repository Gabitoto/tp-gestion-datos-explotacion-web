import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.config import MIN_VOTOS_RANKING_CALIFICACION
from src.consultas import vistas
from src.ui import estilos

estilos.preparar_pagina(
    "Rankings", "🏆",
    "Compará distintos rankings y acotalos por género, década y tipo de contenido.",
)

try:
    generos = vistas.lista_generos()
    decadas = vistas.lista_decadas()
except Exception as e:
    st.error(f"No se pudo consultar Redis: {e}")
    st.stop()

# ----------------------------------------------------------------- filtros
with st.sidebar:
    st.header("🎛️ Filtros")
    n = st.select_slider("Cantidad (Top N)", options=[5, 10, 25, 50, 100], value=10)
    genero = st.selectbox("Género", generos, index=None, placeholder="Todos los géneros")
    decada = st.selectbox("Década / época", decadas, index=None, placeholder="Todas las décadas")
    tipo = st.selectbox("Tipo de contenido", vistas.TIPOS_CONTENIDO, index=None,
                        placeholder="Todos los tipos")
    min_votos_cal = st.select_slider(
        "Votos mínimos (mejor calificadas)",
        options=[MIN_VOTOS_RANKING_CALIFICACION, 250_000, 500_000, 1_000_000],
        value=MIN_VOTOS_RANKING_CALIFICACION, format_func=lambda v: f"{v:,}",
        help=f"El ranking por nota solo contiene títulos con ≥ {MIN_VOTOS_RANKING_CALIFICACION:,} votos.",
    )

COLS = ["id", "titulo", "tipo", "anio", "calificacion", "votos",
        "puntaje_ponderado", "generos", "director"]
CONFIG = {
    "id": st.column_config.TextColumn("ID", width="small"),
    "titulo": st.column_config.TextColumn("Título", width="large"),
    "tipo": st.column_config.TextColumn("Tipo"),
    "anio": st.column_config.NumberColumn("Año", format="%d"),
    "calificacion": st.column_config.ProgressColumn("Nota", min_value=0, max_value=10, format="%.1f"),
    "votos": st.column_config.NumberColumn("Votos", format="%d"),
    "puntaje_ponderado": st.column_config.ProgressColumn(
        "Ponderado", min_value=0, max_value=10, format="%.2f"),
    "generos": st.column_config.ListColumn("Géneros"),
    "director": st.column_config.TextColumn("Director"),
}


def tabla(filas):
    # reindex evita KeyError si la lista viene vacía o falta algún campo
    return pd.DataFrame(filas).reindex(columns=COLS)


def mostrar(ranking, min_votos=0):
    with st.spinner("Consultando Redis…"):
        filas = vistas.top_filtrado(ranking, n, genero, decada, tipo, min_votos)
    df = tabla(filas)
    if df.empty:
        estilos.aviso_sin_datos()
    c1, c2 = st.columns([4, 1])
    c1.caption(f"{len(df)} resultado(s)")
    if not df.empty:
        c2.download_button("⬇️ CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name=f"ranking_{ranking}.csv", mime="text/csv",
                           key=f"csv_{ranking}")
    st.dataframe(df, column_config=CONFIG, hide_index=True, width="stretch")


filtros_activos = [f for f in (genero, decada, tipo) if f]
if filtros_activos:
    st.markdown("**Filtros activos:** " + " ".join(f'<span class="badge">{f}</span>' for f in filtros_activos),
                unsafe_allow_html=True)

try:
    tab1, tab2, tab3 = st.tabs(["🔥 Más votadas", "⭐ Mejor calificadas", "⚖️ Mejor ponderadas"])
    with tab1:
        st.caption("Popularidad masiva: ordenadas por cantidad de votos.")
        mostrar("votos")
    with tab2:
        st.caption(f"Nota promedio pura. Solo títulos con al menos {min_votos_cal:,} votos.")
        mostrar("calificacion", min_votos_cal)
    with tab3:
        st.caption("Puntaje bayesiano: penaliza notas altas con pocos votos.")
        mostrar("ponderado")
except Exception as e:
    st.error(f"No se pudo consultar Redis: {e}")
