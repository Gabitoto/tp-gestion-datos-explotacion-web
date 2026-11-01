import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import streamlit as st

from src.consultas import vistas
from src.ui import estilos

estilos.preparar_pagina(
    "Explorador", "🔎",
    "Buscá producciones combinando género, década, director, actor, duración, nota y más.",
)

try:
    generos_disponibles = vistas.lista_generos()
    decadas_disponibles = vistas.lista_decadas()
except Exception as e:
    st.error(f"No se pudo consultar Redis: {e}")
    st.stop()

DUR_MAX = 400


def tarjeta(f: dict):
    """Tarjeta visual de una producción."""
    with st.container(border=True):
        st.markdown(f'<div class="ficha-titulo">{f.get("titulo", "—")}</div>'
                    f'<div class="ficha-meta">{f.get("tipo", "")} · {f["anio"] or "s/d"} · '
                    f'{str(f["duracion"]) + " min" if f["duracion"] else "duración s/d"}</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns([1, 2])
        c1.markdown(f'<div class="ficha-nota">⭐ {f["calificacion"]:.1f}</div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="ficha-linea">🗳️ {f["votos"]:,} votos</div>'
                    f'<div class="ficha-linea">⚖️ ponderado {f["puntaje_ponderado"]:.2f}</div>',
                    unsafe_allow_html=True)
        st.markdown(estilos.badges_generos(f["generos"]), unsafe_allow_html=True)
        st.markdown(f'<div class="ficha-linea">🎬 {f.get("director", "Desconocido")}</div>'
                    f'<div class="ficha-linea">🎭 {f.get("actores", "Desconocido")}</div>'
                    f'<div class="ficha-linea" style="opacity:.5">{f.get("id", "")}</div>',
                    unsafe_allow_html=True)
        with st.expander("Ver JSON completo"):
            st.json({k: v for k, v in f.items() if k != "score"})


tab_busqueda, tab_id = st.tabs(["🧭 Búsqueda avanzada", "🆔 Por ID"])

# ======================================================= búsqueda avanzada
with tab_busqueda:
    with st.expander("🔤 ¿No sabés el nombre exacto? Buscá directores o actores"):
        cn1, cn2, cn3 = st.columns([1, 2, 1])
        rol = cn1.radio("Buscar", ["director", "actor"], horizontal=True, key="rol_nombre")
        texto_nombre = cn2.text_input("Parte del nombre", key="texto_nombre")
        if cn3.button("Buscar nombres") and texto_nombre.strip():
            with st.spinner("Escaneando Redis…"):
                nombres = vistas.buscar_nombres(rol, texto_nombre)
            if nombres:
                st.success("Copiá el nombre exacto en el formulario:")
                st.code("\n".join(nombres), language=None)
            else:
                st.warning("Sin coincidencias.")

    with st.form("form_busqueda"):
        f1, f2, f3 = st.columns(3)
        genero = f1.selectbox("Género", generos_disponibles, index=None, placeholder="Cualquiera")
        decada = f2.selectbox("Década", decadas_disponibles, index=None, placeholder="Cualquiera")
        tipo = f3.selectbox("Tipo", vistas.TIPOS_CONTENIDO, index=None, placeholder="Cualquiera")

        f4, f5, f6 = st.columns(3)
        director = f4.text_input("Director / autor (nombre exacto)", placeholder="Ej: Christopher Nolan")
        actor = f5.text_input("Actor (nombre exacto)", placeholder="Ej: Leonardo DiCaprio")
        texto = f6.text_input("Título contiene", placeholder="Ej: matrix")

        f7, f8, f9 = st.columns(3)
        duracion = f7.slider("Duración (min)", 0, DUR_MAX, (0, DUR_MAX))
        calif_min = f8.slider("Nota mínima", 0.0, 10.0, 0.0, step=0.1)
        votos_min = f9.select_slider(
            "Votos mínimos", options=[0, 1_000, 10_000, 50_000, 100_000, 500_000, 1_000_000],
            value=0, format_func=lambda v: f"{v:,}")

        limite = st.select_slider("Máximo de resultados", options=[30, 50, 100], value=30)
        enviado = st.form_submit_button("🔎 Buscar", type="primary")

    if enviado or "exp_resultados" not in st.session_state:
        with st.spinner("Buscando en Redis…"):
            try:
                st.session_state["exp_resultados"] = vistas.buscar_peliculas(
                    genero=genero, director=director.strip() or None, actor=actor.strip() or None,
                    decada=decada, tipo=tipo,
                    duracion=None if duracion == (0, DUR_MAX) else duracion,
                    calif_min=calif_min, votos_min=votos_min, texto=texto, limite=limite,
                )
            except Exception as e:
                st.error(f"No se pudo consultar Redis: {e}")
                st.stop()

    resultados = st.session_state["exp_resultados"]
    st.markdown(f"**{len(resultados)} resultado(s)** · ordenados por votos")
    st.caption("Género, década, director y actor se cruzan en Redis; el resto de filtros se "
               f"aplica sobre las {vistas.CANDIDATOS_MAX:,} coincidencias más votadas.")

    if not resultados:
        estilos.aviso_sin_datos()
    else:
        vista = st.radio("Vista", ["Tarjetas", "Tabla"], horizontal=True, label_visibility="collapsed")
        if vista == "Tarjetas":
            for i in range(0, len(resultados), 3):
                cols = st.columns(3)
                for col, f in zip(cols, resultados[i:i + 3]):
                    with col:
                        tarjeta(f)
        else:
            cols = ["id", "titulo", "tipo", "anio", "duracion", "calificacion", "votos",
                    "generos", "director", "actores"]
            st.dataframe(
                pd.DataFrame(resultados).reindex(columns=cols), hide_index=True, width="stretch",
                column_config={
                    "calificacion": st.column_config.ProgressColumn("Nota", min_value=0, max_value=10, format="%.1f"),
                    "duracion": st.column_config.NumberColumn("Min", format="%d"),
                    "generos": st.column_config.ListColumn("Géneros"),
                },
            )

# ================================================================ por ID
with tab_id:
    tconst = st.text_input("ID IMDb (ej. tt0111161)")
    if tconst:
        ficha = vistas.ficha_pelicula(tconst.strip())
        if ficha:
            _, centro, _ = st.columns([1, 2, 1])
            with centro:
                tarjeta(vistas.normalizar_ficha(ficha))
        else:
            st.warning("No se encontró ninguna producción con ese ID.")
