import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import altair as alt
import pandas as pd
import streamlit as st

from src.consultas import vistas
from src.ui import estilos

estilos.preparar_pagina(
    "Dashboard", "📊",
    "Cuatro visualizaciones interactivas. Los filtros de la barra lateral se aplican a todas.",
)

try:
    total = vistas.total_peliculas()
    generos_all = vistas.conteo_por_genero()
    decadas_all = vistas.conteo_por_decada()
except Exception as e:
    st.error(f"No se pudo consultar Redis: {e}")
    st.stop()

# ----------------------------------------------------------------- filtros
anios_dec = [int(d.rstrip("s")) for d in decadas_all if d.rstrip("s").isdigit()]
ANIO_MIN = min(anios_dec) if anios_dec else 1900
ANIO_MAX = max(anios_dec) + 9 if anios_dec else 2030

with st.sidebar:
    st.header("🎛️ Filtros")
    rango_anios = st.slider("Rango de años", ANIO_MIN, ANIO_MAX, (ANIO_MIN, ANIO_MAX))
    generos_sel = st.multiselect(
        "Géneros", list(generos_all), placeholder="Todos los géneros",
        help="Vacío = todos. Aplica a las cuatro visualizaciones.",
    )
    rango_nota = st.slider("Calificación", 1.0, 10.0, (1.0, 10.0), step=0.1)
    votos_min = st.select_slider(
        "Mínimo de votos", options=[0, 1_000, 10_000, 50_000, 100_000, 250_000, 500_000, 1_000_000],
        value=0, format_func=lambda v: f"{v:,}",
    )
    tam_muestra = st.slider(
        "Tamaño de la muestra", 500, 5000, 2000, step=500,
        help="Dispersión y mapa de calor usan las N producciones más votadas "
             "(evita recorrer los millones de claves de Redis).",
    )

# ------------------------------------------------- datos (barras y líneas)
# Contadores exactos pre-agregados en Redis (KPI).
generos_vis = {g: c for g, c in generos_all.items() if not generos_sel or g in generos_sel}
decadas_vis = {
    d: c for d, c in decadas_all.items()
    if d.rstrip("s").isdigit() and rango_anios[0] - 9 <= int(d.rstrip("s")) <= rango_anios[1]
}

# ---------------------------------------- datos (dispersión y mapa de calor)
with st.spinner("Consultando Redis…"):
    try:
        muestra = vistas.muestra_peliculas(tam_muestra)
    except Exception as e:
        st.error(f"No se pudo consultar Redis: {e}")
        st.stop()

df = pd.DataFrame(muestra)
if not df.empty:
    df = df[
        (df["anio"].between(rango_anios[0], rango_anios[1]))
        & (df["calificacion"].between(rango_nota[0], rango_nota[1]))
        & (df["votos"] >= votos_min)
    ]
    if generos_sel:
        df = df[df["generos"].apply(lambda gs: any(g in generos_sel for g in gs))]

df_gen = df.explode("generos").rename(columns={"generos": "genero"}) if not df.empty else df
if generos_sel and not df_gen.empty:
    df_gen = df_gen[df_gen["genero"].isin(generos_sel)]
df_gen = df_gen.dropna(subset=["genero"]) if not df_gen.empty else df_gen

# -------------------------------------------------------------------- KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Producciones en Redis", f"{total:,}")
k2.metric("En la muestra filtrada", f"{len(df):,}")
k3.metric("Nota media", f"{df['calificacion'].mean():.2f}" if len(df) else "—")
k4.metric("Votos medios", f"{df['votos'].mean():,.0f}" if len(df) else "—")

st.write("")

# ------------------------------------------------------------ visualizaciones
fila1 = st.columns(2)
fila2 = st.columns(2)

with fila1[0], st.container(border=True):
    st.subheader("Producciones por género")
    st.caption("Conteo exacto sobre todo el catálogo (top 20).")
    if generos_vis:
        d = pd.DataFrame({"genero": list(generos_vis), "producciones": list(generos_vis.values())}).head(20)
        st.altair_chart(
            alt.Chart(d).mark_bar(cornerRadiusEnd=4, color="#E50914").encode(
                x=alt.X("producciones:Q", title="Producciones"),
                y=alt.Y("genero:N", sort="-x", title=None),
                tooltip=["genero", alt.Tooltip("producciones:Q", format=",")],
            ).properties(height=380),
            width="stretch",
        )
    else:
        estilos.aviso_sin_datos()

with fila1[1], st.container(border=True):
    st.subheader("Producciones por década")
    st.caption("Evolución temporal del catálogo en el rango de años elegido.")
    if decadas_vis:
        d = pd.DataFrame({"decada": list(decadas_vis), "producciones": list(decadas_vis.values())})
        base = alt.Chart(d).encode(
            x=alt.X("decada:O", sort=None, title="Década"),
            y=alt.Y("producciones:Q", title="Producciones"),
            tooltip=["decada", alt.Tooltip("producciones:Q", format=",")],
        )
        st.altair_chart(
            (base.mark_area(opacity=0.25, color="#E50914") + base.mark_line(color="#E50914", point=True))
            .properties(height=380),
            width="stretch",
        )
    else:
        estilos.aviso_sin_datos()

with fila2[0], st.container(border=True):
    st.subheader("Dispersión: puntaje por género")
    st.caption(f"Cada punto es una producción (muestra de las {tam_muestra:,} más votadas). "
               "Color y tamaño = votos.")
    if df_gen.empty:
        estilos.aviso_sin_datos()
    else:
        puntos = df_gen if len(df_gen) <= 2500 else df_gen.sample(2500, random_state=1)
        puntos = puntos[puntos["votos"] > 0]
        st.altair_chart(
            alt.Chart(puntos[["titulo", "anio", "calificacion", "votos", "genero"]])
            .transform_calculate(jitter="random()")
            .mark_circle(opacity=0.65)
            .encode(
                x=alt.X("calificacion:Q", scale=alt.Scale(zero=False), title="Puntaje"),
                y=alt.Y("genero:N", title=None),
                yOffset=alt.YOffset("jitter:Q", scale=alt.Scale(domain=[0, 1])),
                size=alt.Size("votos:Q", scale=alt.Scale(range=[15, 220]), legend=None),
                color=alt.Color("votos:Q", scale=alt.Scale(type="log", scheme="inferno"),
                                title="Votos"),
                tooltip=["titulo", "anio", "genero", "calificacion",
                         alt.Tooltip("votos:Q", format=",")],
            ).properties(height=420),
            width="stretch",
        )

with fila2[1], st.container(border=True):
    st.subheader("Mapa de calor: género × década")
    st.caption("Color = puntaje promedio (calificación) por género en cada década.")
    if df_gen.empty:
        estilos.aviso_sin_datos()
    else:
        df_calor = df_gen[df_gen["anio"] > 0].copy()
        if df_calor.empty:
            estilos.aviso_sin_datos()
        else:
            df_calor["decada_num"] = (df_calor["anio"] // 10) * 10
            df_calor["decada"] = df_calor["decada_num"].astype(str) + "s"
            mapa = (
                df_calor.groupby(["genero", "decada", "decada_num"], as_index=False)
                .agg(
                    puntaje_promedio=("calificacion", "mean"),
                    producciones=("calificacion", "count"),
                )
            )
            mapa["puntaje_promedio"] = mapa["puntaje_promedio"].round(2)
            decadas_ordenadas = sorted(
                mapa["decada"].unique(),
                key=lambda d: int(d.rstrip("s")) if d.rstrip("s").isdigit() else 0,
            )
            celdas = alt.Chart(mapa).encode(
                x=alt.X("decada:O", sort=decadas_ordenadas, title="Década"),
                y=alt.Y("genero:N", title="Género"),
            )
            st.altair_chart(
                (celdas.mark_rect(cornerRadius=3).encode(
                    color=alt.Color(
                        "puntaje_promedio:Q",
                        scale=alt.Scale(zero=False, scheme="inferno"),
                        title="Puntaje prom.",
                    ),
                    tooltip=[
                        alt.Tooltip("genero:N", title="Género"),
                        alt.Tooltip("decada:O", title="Década"),
                        alt.Tooltip("puntaje_promedio:Q", format=".2f", title="Puntaje promedio"),
                        alt.Tooltip("producciones:Q", format=",", title="Producciones"),
                    ],
                ) + celdas.mark_text(fontSize=10, fontWeight="bold").encode(
                    text=alt.Text("puntaje_promedio:Q", format=".1f"),
                    color=alt.condition(
                        alt.datum.puntaje_promedio > mapa["puntaje_promedio"].mean(),
                        alt.value("white"),
                        alt.value("#d0d0d0"),
                    ),
                )).properties(height=420),
                width="stretch",
            )
