"""Carga masiva de peliculas_limpias.jsonl a Redis (modelo clave-valor)."""
import json
import time

import redis

from src.config import (
    ARCH_JSONL, REDIS_HOST, REDIS_PORT, K_PELICULA, K_FILTRO_GENERO,
    K_FILTRO_DECADA, K_FILTRO_DIRECTOR, K_FILTRO_ACTOR, K_RANKING_VOTOS,
    K_RANKING_CALIFICACION, K_RANKING_PONDERADO, K_KPI_TOTAL, K_KPI_GENEROS,
    K_KPI_DECADAS, MIN_VOTOS_RANKING_CALIFICACION,
)

TAMANIO_LOTE = 2500


def decada_de(anio):
    """1999 -> '1990s'. Devuelve None si el año es desconocido (0 o negativo)."""
    if not anio or anio <= 0:
        return None
    return f"{(anio // 10) * 10}s"


def cargar_a_redis(r=None, archivo=ARCH_JSONL, limpiar=True):
    """Carga el JSONL en Redis. Devuelve la cantidad de registros cargados."""
    print("=== CARGA MASIVA A REDIS (MODELO CLAVE-VALOR EN ESPAÑOL) ===")
    if r is None:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    if limpiar:
        print("Limpiando base de datos previa...")
        r.flushdb()

    pipe = r.pipeline(transaction=False)
    contador = 0
    t_inicio = time.time()

    with open(archivo, "r", encoding="utf-8") as f:
        for linea in f:
            if not linea.strip():
                continue
            p = json.loads(linea)
            tconst = p["id"]

            # 1. Hash con la ficha completa
            pipe.hset(K_PELICULA.format(id=tconst), mapping={
                "id": tconst,
                "titulo": p["titulo"],
                "tipo": p["tipo"],
                "anio": str(p["anio"]),
                "duracion": str(p["duracion"]),
                "calificacion": str(p["calificacion"]),
                "votos": str(p["votos"]),
                "puntaje_ponderado": str(p["puntaje_ponderado"]),
                "generos": ", ".join(p["generos"]),
                "director": p["director"],
                "actores": p["actores"],
            })

            # 2. Sets para filtros rápidos
            for gen in p["generos"]:
                pipe.sadd(K_FILTRO_GENERO.format(valor=gen), tconst)
                pipe.hincrby(K_KPI_GENEROS, gen, 1)
            decada = decada_de(p["anio"])
            if decada:
                pipe.sadd(K_FILTRO_DECADA.format(valor=decada), tconst)
                pipe.hincrby(K_KPI_DECADAS, decada, 1)
            if p["director"] != "Desconocido":
                for nombre in p["director"].split(", "):
                    pipe.sadd(K_FILTRO_DIRECTOR.format(valor=nombre), tconst)
            if p["actores"] != "Desconocido":
                for nombre in p["actores"].split(", "):
                    pipe.sadd(K_FILTRO_ACTOR.format(valor=nombre), tconst)

            # 3. Métricas y rankings
            pipe.incr(K_KPI_TOTAL)
            pipe.zadd(K_RANKING_VOTOS, {tconst: p["votos"]})
            pipe.zadd(K_RANKING_PONDERADO, {tconst: p["puntaje_ponderado"]})
            if p["votos"] >= MIN_VOTOS_RANKING_CALIFICACION:
                pipe.zadd(K_RANKING_CALIFICACION, {tconst: p["calificacion"]})

            contador += 1
            if contador % TAMANIO_LOTE == 0:
                pipe.execute()
                print(f"-> {contador:,} películas cargadas...")
        pipe.execute()

    print(f"\n¡Carga finalizada en {time.time() - t_inicio:.2f} s!")
    print(f"Total ingresado: {contador:,} | Claves en Redis: {r.dbsize():,}")
    return contador


if __name__ == "__main__":
    cargar_a_redis()
