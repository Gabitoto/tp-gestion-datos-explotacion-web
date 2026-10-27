"""Consultas de solo lectura sobre Redis. Cada función = una 'vista' de datos."""
from itertools import islice

from src.config import (
    K_PELICULA, K_FILTRO_GENERO, K_RANKING_VOTOS, K_RANKING_CALIFICACION,
    K_RANKING_PONDERADO, K_KPI_TOTAL, K_KPI_GENEROS, K_KPI_DECADAS,
)
from src.consultas.conexion import get_redis


def total_peliculas() -> int:
    return int(get_redis().get(K_KPI_TOTAL) or 0)


def conteo_por_genero() -> dict:
    datos = get_redis().hgetall(K_KPI_GENEROS)
    return dict(sorted(((k, int(v)) for k, v in datos.items()), key=lambda x: -x[1]))


def _orden_decada(decada: str) -> int:
    try:
        return int(decada.rstrip("s"))
    except ValueError:
        return 10**9


def conteo_por_decada() -> dict:
    # Se lee un Hash pre-agregado en la carga: O(n décadas), sin SCAN sobre toda la base.
    datos = get_redis().hgetall(K_KPI_DECADAS)
    return {k: int(v) for k, v in sorted(datos.items(), key=lambda kv: _orden_decada(kv[0]))}


def ficha_pelicula(tconst: str) -> dict:
    return get_redis().hgetall(K_PELICULA.format(id=tconst))


def _fichas(ids: list) -> list[dict]:
    """Trae varias fichas en un solo viaje de red (pipeline)."""
    pipe = get_redis().pipeline(transaction=False)
    for tconst in ids:
        pipe.hgetall(K_PELICULA.format(id=tconst))
    return pipe.execute() if ids else []


def _top(clave_zset: str, n: int) -> list[dict]:
    items = get_redis().zrevrange(clave_zset, 0, n - 1, withscores=True)
    fichas = _fichas([tconst for tconst, _ in items])
    filas = []
    for (tconst, score), ficha in zip(items, fichas):
        ficha = dict(ficha)
        ficha.setdefault("id", tconst)
        ficha["score"] = score
        filas.append(ficha)
    return filas


def top_por_votos(n: int = 10) -> list[dict]:
    return _top(K_RANKING_VOTOS, n)


def top_por_calificacion(n: int = 10) -> list[dict]:
    return _top(K_RANKING_CALIFICACION, n)


def top_por_ponderado(n: int = 10) -> list[dict]:
    return _top(K_RANKING_PONDERADO, n)


def peliculas_por_genero(genero: str, limite: int = 50) -> list[dict]:
    r = get_redis()
    # islice corta el iterador: no recorre todo el Set (Drama puede tener cientos de miles)
    ids = list(islice(r.sscan_iter(K_FILTRO_GENERO.format(valor=genero), count=limite), limite))
    return _fichas(ids)


def lista_generos() -> list[str]:
    return list(conteo_por_genero().keys())
