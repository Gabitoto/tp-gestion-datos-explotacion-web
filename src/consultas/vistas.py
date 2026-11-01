"""Consultas de solo lectura sobre Redis. Cada función = una 'vista' de datos."""
from itertools import islice
from uuid import uuid4

from src.config import (
    K_PELICULA, K_FILTRO_GENERO, K_RANKING_VOTOS, K_RANKING_CALIFICACION,
    K_RANKING_PONDERADO, K_KPI_TOTAL, K_KPI_GENEROS, K_KPI_DECADAS,
    K_FILTRO_DECADA, K_FILTRO_DIRECTOR, K_FILTRO_ACTOR,
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


# ====================================================================
# Consultas avanzadas (dashboard, rankings filtrados y explorador)
# ====================================================================

TIPOS_CONTENIDO = ["Película", "Serie", "Miniserie", "Película para TV"]
_RANKINGS = {
    "votos": K_RANKING_VOTOS,
    "calificacion": K_RANKING_CALIFICACION,
    "ponderado": K_RANKING_PONDERADO,
}
# Tope de candidatos que se traen de Redis cuando hay que filtrar en Python.
CANDIDATOS_MAX = 3000


def _num(valor, tipo=float, defecto=0):
    try:
        return tipo(float(valor)) if tipo is int else tipo(valor)
    except (TypeError, ValueError):
        return defecto


def normalizar_ficha(ficha: dict) -> dict:
    """Convierte los strings del Hash a tipos numéricos y 'generos' a lista."""
    f = dict(ficha)
    f["anio"] = _num(f.get("anio"), int)
    f["duracion"] = _num(f.get("duracion"), int)
    f["votos"] = _num(f.get("votos"), int)
    f["calificacion"] = _num(f.get("calificacion"), float, 0.0)
    f["puntaje_ponderado"] = _num(f.get("puntaje_ponderado"), float, 0.0)
    f["generos"] = [g for g in (f.get("generos") or "").split(", ") if g]
    return f


def lista_decadas() -> list[str]:
    return list(conteo_por_decada().keys())


def muestra_peliculas(limite: int = 3000) -> list[dict]:
    """Muestra acotada (las `limite` más votadas) con fichas normalizadas.

    Alimenta dispersión y mapa de calor sin recorrer los millones de claves.
    """
    ids = get_redis().zrevrange(K_RANKING_VOTOS, 0, max(limite, 1) - 1)
    return [normalizar_ficha(f) for f in _fichas(ids) if f]


def _ids_ordenados(clave_ranking: str, conjuntos: list[str], cap: int):
    """IDs ordenados por score desc, restringidos a la intersección de `conjuntos`.

    Con conjuntos usa ZINTERSTORE contra un ZSet temporal (peso 0 para los Sets,
    así el score sigue siendo el del ranking) que expira solo.
    Devuelve lista de (id, score).
    """
    r = get_redis()
    if not conjuntos:
        return r.zrevrange(clave_ranking, 0, cap - 1, withscores=True)
    tmp = f"tmp:interseccion:{uuid4().hex}"
    try:
        pesos = {clave_ranking: 1, **{c: 0 for c in conjuntos}}
        if not r.zinterstore(tmp, pesos):
            return []
        r.expire(tmp, 30)
        return r.zrevrange(tmp, 0, cap - 1, withscores=True)
    finally:
        r.delete(tmp)


def _a_filas(items) -> list[dict]:
    fichas = _fichas([i for i, _ in items])
    filas = []
    for (tconst, score), ficha in zip(items, fichas):
        if not ficha:
            continue
        f = normalizar_ficha(ficha)
        f.setdefault("id", tconst)
        f["score"] = score
        filas.append(f)
    return filas


def top_filtrado(ranking: str = "votos", n: int = 10, genero: str | None = None,
                 decada: str | None = None, tipo: str | None = None,
                 min_votos: int = 0) -> list[dict]:
    """Ranking ('votos' | 'calificacion' | 'ponderado') con filtros opcionales.

    genero/decada se resuelven en Redis (intersección de Sets); tipo y min_votos
    se aplican sobre los candidatos recuperados (hasta CANDIDATOS_MAX).
    """
    clave = _RANKINGS[ranking]
    conjuntos = []
    if genero:
        conjuntos.append(K_FILTRO_GENERO.format(valor=genero))
    if decada:
        conjuntos.append(K_FILTRO_DECADA.format(valor=decada))
    post = bool(tipo) or min_votos > 0
    items = _ids_ordenados(clave, conjuntos, CANDIDATOS_MAX if post else n)
    filas = _a_filas(items)
    if tipo:
        filas = [f for f in filas if f.get("tipo") == tipo]
    if min_votos > 0:
        filas = [f for f in filas if f["votos"] >= min_votos]
    return filas[:n]


def _patron_insensible(texto: str) -> str:
    """'ford' -> '[fF][oO][rR][dD]' para MATCH sin distinguir mayúsculas."""
    out = []
    for ch in texto.strip():
        if ch.isalpha():
            out.append(f"[{ch.lower()}{ch.upper()}]")
        elif ch in "*?[]\\":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def buscar_nombres(rol: str, texto: str, limite: int = 15) -> list[str]:
    """Nombres de 'director' o 'actor' que contienen `texto` (SCAN, corta al llegar al límite)."""
    plantilla = {"director": K_FILTRO_DIRECTOR, "actor": K_FILTRO_ACTOR}[rol]
    if not texto or not texto.strip():
        return []
    prefijo = plantilla.format(valor="")
    patron = prefijo + "*" + _patron_insensible(texto) + "*"
    claves = islice(get_redis().scan_iter(match=patron, count=5000), limite)
    return sorted(c[len(prefijo):] for c in claves)


def buscar_peliculas(genero: str | None = None, director: str | None = None,
                     actor: str | None = None, decada: str | None = None,
                     tipo: str | None = None, duracion: tuple | None = None,
                     calif_min: float = 0.0, votos_min: int = 0,
                     texto: str | None = None, limite: int = 100) -> list[dict]:
    """Búsqueda multicriterio. Resultados ordenados por votos (desc).

    Género/director/actor/década se cruzan en Redis con ZINTERSTORE sobre
    `ranking:votos`; duración, nota, votos, tipo y texto se filtran sobre los
    primeros CANDIDATOS_MAX candidatos.
    """
    conjuntos = []
    if genero:
        conjuntos.append(K_FILTRO_GENERO.format(valor=genero))
    if decada:
        conjuntos.append(K_FILTRO_DECADA.format(valor=decada))
    if director:
        conjuntos.append(K_FILTRO_DIRECTOR.format(valor=director))
    if actor:
        conjuntos.append(K_FILTRO_ACTOR.format(valor=actor))
    filas = _a_filas(_ids_ordenados(K_RANKING_VOTOS, conjuntos, CANDIDATOS_MAX))
    if tipo:
        filas = [f for f in filas if f.get("tipo") == tipo]
    if duracion:
        lo, hi = duracion
        filas = [f for f in filas if f["duracion"] > 0 and lo <= f["duracion"] <= hi]
    if calif_min > 0:
        filas = [f for f in filas if f["calificacion"] >= calif_min]
    if votos_min > 0:
        filas = [f for f in filas if f["votos"] >= votos_min]
    if texto and texto.strip():
        t = texto.strip().lower()
        filas = [f for f in filas if t in (f.get("titulo") or "").lower()]
    return filas[:limite]
