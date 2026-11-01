"""Estilos y componentes visuales compartidos por todas las páginas de Streamlit."""
import streamlit as st

_CSS = """
<style>
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }
h1, h2, h3 { letter-spacing: -0.01em; }

/* Tarjetas de métricas (KPI) */
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #1b2130 0%, #141926 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-left: 4px solid #E50914;
    border-radius: 14px;
    padding: 14px 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.35);
}
[data-testid="stMetricLabel"] p { opacity: .75; font-size: .85rem; }
[data-testid="stMetricValue"] { font-weight: 700; }

/* Contenedores con borde (tarjetas de gráficos y fichas) */
[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
    border-color: rgba(255,255,255,0.08) !important;
    background: rgba(255,255,255,0.02);
}

/* Encabezado de página */
.pagina-encabezado {
    background: linear-gradient(120deg, rgba(229,9,20,.22), rgba(229,9,20,0) 70%);
    border-radius: 16px; padding: 18px 24px; margin-bottom: 1.2rem;
    border: 1px solid rgba(255,255,255,0.06);
}
.pagina-encabezado .ruta { font-size: .78rem; opacity: .6; text-transform: uppercase; letter-spacing: .08em; }
.pagina-encabezado h1 { margin: .15rem 0 .1rem 0; padding: 0; font-size: 2rem; }
.pagina-encabezado .sub { opacity: .75; margin: 0; }

/* Badges de género */
.badge { display:inline-block; padding: 2px 10px; margin: 0 4px 4px 0; border-radius: 999px;
         background: rgba(229,9,20,.18); border: 1px solid rgba(229,9,20,.45);
         font-size: .75rem; }

/* Ficha de película */
.ficha-titulo { font-size: 1.15rem; font-weight: 700; margin-bottom: 2px; }
.ficha-meta { opacity: .7; font-size: .85rem; margin-bottom: 8px; }
.ficha-nota { font-size: 1.6rem; font-weight: 800; color: #F5C518; }
.ficha-linea { font-size: .85rem; opacity: .85; margin: 2px 0; }

/* Barra lateral */
[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.06); }
</style>
"""


def preparar_pagina(titulo: str, icono: str, subtitulo: str = "", ruta: str = "Catálogo IMDb"):
    """Configura la página, inyecta el CSS y dibuja el encabezado.

    Debe ser la primera llamada a Streamlit de cada página.
    """
    st.set_page_config(page_title=f"{titulo} · Cine en Redis", page_icon=icono, layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    sub = f'<p class="sub">{subtitulo}</p>' if subtitulo else ""
    st.markdown(
        f'<div class="pagina-encabezado"><div class="ruta">{ruta} › {titulo}</div>'
        f"<h1>{icono} {titulo}</h1>{sub}</div>",
        unsafe_allow_html=True,
    )


def badges_generos(generos) -> str:
    """HTML con una 'pastilla' por género."""
    return "".join(f'<span class="badge">{g}</span>' for g in generos)


def aviso_sin_datos(mensaje: str = "No hay resultados con los filtros actuales."):
    st.info(f"🔍 {mensaje} Probá ampliar los rangos o quitar algún filtro.")

