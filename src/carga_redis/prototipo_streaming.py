"""Prototipo: carga directa a Redis en streaming desde IMDb (sin pasar por el ETL).

ATENCIÓN: usa un esquema distinto al de cargar_redis.py (tipos en inglés, sin
calificaciones) y escribe sobre las mismas claves pelicula:{id}. No combinar
ambas cargas en la misma base.
"""
import urllib.request
import gzip
import csv
import io
import redis

from src.config import REDIS_HOST, REDIS_PORT

URL_IMDB = "https://datasets.imdbws.com/title.basics.tsv.gz"
LIMITE = 200000  # Muestra de 200.000 títulos para prueba rápida


def cargar_muestra(limite=LIMITE):
    # Conexión local a Redis
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    print("Conectando a IMDb y procesando en streaming...")
    req = urllib.request.Request(URL_IMDB, headers={'User-Agent': 'Mozilla/5.0'})

    pipe = r.pipeline(transaction=False)
    contador = 0

    with urllib.request.urlopen(req) as respuesta_web:
        with gzip.GzipFile(fileobj=respuesta_web) as gz:
            lector = csv.reader(io.TextIOWrapper(gz, encoding='utf-8'), delimiter='\t')
            next(lector)  # Saltar cabecera

            for fila in lector:
                # fila: [tconst, titleType, primaryTitle, originalTitle, isAdult, startYear, endYear, runtimeMinutes, genres]
                if len(fila) < 9:
                    continue

                tconst = fila[0]
                tipo = fila[1]
                titulo = fila[2]
                anio = fila[5]
                duracion = fila[7]
                generos = fila[8].split(',') if fila[8] != '\\N' else []

                # 1. Guardar la entidad en Redis (Hash)
                pipe.hset(f"pelicula:{tconst}", mapping={
                    "id": tconst,
                    "titulo": titulo,
                    "tipo": tipo,
                    "anio": anio if anio != '\\N' else "N/A",
                    "duracion": duracion if duracion != '\\N' else "N/A",
                    "generos": ", ".join(generos) if generos else "N/A"
                })

                # 2. Índices para filtros
                if tipo != '\\N':
                    pipe.sadd(f"filtro:tipo:{tipo}", tconst)
                    pipe.hincrby("kpi:conteo_tipos", tipo, 1)

                if anio != '\\N' and len(anio) == 4 and anio.isdigit():
                    decada = f"{anio[:3]}0s"
                    pipe.sadd(f"filtro:decada:{decada}", tconst)

                for g in generos:
                    pipe.sadd(f"filtro:genero:{g}", tconst)
                    pipe.hincrby("kpi:conteo_generos", g, 1)

                # 3. KPI general
                pipe.incr("kpi:total_titulos")
                contador += 1

                if contador % 5000 == 0:
                    pipe.execute()
                    print(f" -> Procesadas {contador} peliculas...")

                if contador >= limite:
                    break

            pipe.execute()

    print(f"\n¡Carga de IMDb finalizada! Total cargado: {contador} registros.")
    return contador


if __name__ == "__main__":
    cargar_muestra()
