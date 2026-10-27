"""Configuración central: rutas, conexión a Redis y nombres de claves."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# --- Datos ---
DIR_RAW = RAIZ / "data" / "raw"
DIR_PROCESADOS = RAIZ / "data" / "processed"

ARCH_RATINGS = DIR_RAW / "title.ratings.tsv.gz"
ARCH_BASICS = DIR_RAW / "title.basics.tsv.gz"
ARCH_PRINCIPALS = DIR_RAW / "title.principals.tsv.gz"
ARCH_NAMES = DIR_RAW / "name.basics.tsv.gz"
ARCHIVOS_RAW = [ARCH_RATINGS, ARCH_BASICS, ARCH_PRINCIPALS, ARCH_NAMES]

ARCH_JSONL = DIR_PROCESADOS / "peliculas_limpias.jsonl"

# --- Redis (configurable por variables de entorno, p. ej. en Docker) ---
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# --- Reglas de negocio ---
# Solo entran al ranking por nota los títulos con suficientes votos
# (evita que una obra con 1 voto de 10 encabece el ranking).
MIN_VOTOS_RANKING_CALIFICACION = 100_000

# --- Convención de claves (modelo clave-valor) ---
K_PELICULA = "pelicula:{id}"                 # Hash
K_FILTRO_GENERO = "filtro:genero:{valor}"    # Set
K_FILTRO_DECADA = "filtro:decada:{valor}"    # Set
K_FILTRO_DIRECTOR = "filtro:director:{valor}"  # Set
K_FILTRO_ACTOR = "filtro:actor:{valor}"      # Set
K_RANKING_VOTOS = "ranking:votos"            # ZSet
K_RANKING_CALIFICACION = "ranking:calificacion"  # ZSet (filtrado por votos)
K_RANKING_PONDERADO = "ranking:ponderado"    # ZSet (puntaje bayesiano)
K_KPI_TOTAL = "kpi:total_peliculas"          # String
K_KPI_GENEROS = "kpi:generos:conteo"         # Hash
K_KPI_DECADAS = "kpi:decadas:conteo"         # Hash
