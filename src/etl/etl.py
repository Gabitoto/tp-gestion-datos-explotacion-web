import gzip
import json
import time
from pathlib import Path

from src.config import (ARCH_RATINGS, ARCH_BASICS, ARCH_PRINCIPALS,
                        ARCH_NAMES, ARCH_JSONL as ARCH_SALIDA)

MAPEO_TIPOS = {
    "movie": "Película",
    "tvSeries": "Serie",
    "tvMiniSeries": "Miniserie",
    "tvMovie": "Película para TV",
    "tvEpisode": "Episodio"
}

DICC_GENEROS = {
    "Action": "Acción",
    "Adventure": "Aventura",
    "Animation": "Animación",
    "Biography": "Biografía",
    "Comedy": "Comedia",
    "Crime": "Crimen",
    "Documentary": "Documental",
    "Drama": "Drama",
    "Family": "Familiar",
    "Fantasy": "Fantasía",
    "Film-Noir": "Cine negro",
    "History": "Historia",
    "Horror": "Terror",
    "Music": "Música",
    "Musical": "Musical",
    "Mystery": "Misterio",
    "Romance": "Romance",
    "Sci-Fi": "Ciencia ficción",
    "Sport": "Deporte",
    "Thriller": "Suspenso",
    "War": "Guerra",
    "Western": "Western"
}

# Constantes para el puntaje ponderado (estimación Bayesiana)
C_PROMEDIO_GLOBAL = 6.9
M_VOTOS_MINIMOS = 25

def clasificar_duracion(minutos):
    if minutos <= 0:
        return "No especificada"
    if minutos < 60:
        return "Corta (< 60m)"
    if minutos <= 120:
        return "Estándar (60-120m)"
    if minutos <= 180:
        return "Larga (120-180m)"
    return "Épica (> 180m)"

def clasificar_popularidad(votos):
    # Límites inclusivos para que coincidan con las etiquetas
    if votos <= 100:
        return "Baja (1-100)"
    if votos <= 5000:
        return "Media (101-5K)"
    if votos <= 50000:
        return "Alta (5K-50K)"
    return "Blockbuster (> 50K)"

def calcular_puntaje_ponderado(calificacion, votos):
    # Fórmula bayesiana ponderada
    wr = (votos / (votos + M_VOTOS_MINIMOS)) * calificacion + (M_VOTOS_MINIMOS / (votos + M_VOTOS_MINIMOS)) * C_PROMEDIO_GLOBAL
    return round(wr, 2)

def ejecutar_etl(umbral_votos=1):
    t_inicio = time.time()
    print("=== PIPELINE ETL COMPLETO CON PONDERACIÓN Y MÉTRICAS DERIVADAS ===")
    print(f"Criterios: Tipos narrativos, incluye adultos, >= {umbral_votos} votos, hasta 6 actores y guionistas.\n")

    # 1. RATINGS
    print(f"1/4 Leyendo calificaciones y votos (umbral >= {umbral_votos})...")
    ratings = {}
    with gzip.open(ARCH_RATINGS, "rt", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        for linea in f:
            cols = linea.strip().split("\t")
            if len(cols) >= 3:
                try:
                    votos = int(cols[2])
                    if votos >= umbral_votos:
                        ratings[cols[0]] = (float(cols[1]), votos)
                except ValueError:
                    continue
    print(f"-> {len(ratings):,} obras superaron los {umbral_votos} votos.")

    # 2. BASICS
    print("\n2/4 Filtrando catálogo completo...")
    producciones = {}
    with gzip.open(ARCH_BASICS, "rt", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        for linea in f:
            cols = linea.strip().split("\t")
            if len(cols) < 9:
                continue

            tconst = cols[0]
            tipo_raw = cols[1]
            es_adulto = (cols[4] == "1")

            # Admitimos tipos narrativos y no excluimos contenido adulto
            if tipo_raw not in MAPEO_TIPOS or tconst not in ratings:
                continue

            anio_inicio = int(cols[5]) if cols[5].isdigit() else 0
            anio_fin = int(cols[6]) if cols[6].isdigit() else 0
            duracion = int(cols[7]) if cols[7].isdigit() else 0

            generos_crudos = [g.strip() for g in cols[8].split(",") if g and g != "\\N"]
            generos_esp = [DICC_GENEROS.get(g, g) for g in generos_crudos]

            calificacion, votos = ratings[tconst]

            producciones[tconst] = {
                "id": tconst,
                "tipo": MAPEO_TIPOS[tipo_raw],
                "titulo": cols[2].strip(),
                "titulo_original": cols[3].strip(),
                "es_adulto": es_adulto,
                "anio": anio_inicio,
                "anio_fin": anio_fin,
                "duracion": duracion,
                "rango_duracion": clasificar_duracion(duracion),
                "calificacion": calificacion,
                "votos": votos,
                "puntaje_ponderado": calcular_puntaje_ponderado(calificacion, votos),
                "nivel_popularidad": clasificar_popularidad(votos),
                "generos": generos_esp,
                "ids_directores": [],
                "ids_guionistas": [],
                "ids_actores": []
            }

    del ratings
    print(f"-> {len(producciones):,} producciones seleccionadas.")

    # 3. PRINCIPALS (Directores, Guionistas y hasta 6 Actores)
    print("\n3/4 Cruzando roles (directores, guionistas y actores) sobre 102M de relaciones...")
    personas_necesarias = set()
    with gzip.open(ARCH_PRINCIPALS, "rt", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        for linea in f:
            cols = linea.strip().split("\t")
            if len(cols) < 4:
                continue

            tconst = cols[0]
            if tconst in producciones:
                nconst = cols[2]
                rol = cols[3]
                p = producciones[tconst]

                if rol == "director" and len(p["ids_directores"]) < 2:
                    p["ids_directores"].append(nconst)
                    personas_necesarias.add(nconst)
                elif rol == "writer" and len(p["ids_guionistas"]) < 2:
                    p["ids_guionistas"].append(nconst)
                    personas_necesarias.add(nconst)
                elif rol in ("actor", "actress") and len(p["ids_actores"]) < 6:
                    p["ids_actores"].append(nconst)
                    personas_necesarias.add(nconst)

    print(f"-> {len(personas_necesarias):,} personas clave requeridas.")

    # 4. NAMES
    print("\n4/4 Extrayendo nombres reales...")
    nombres = {}
    with gzip.open(ARCH_NAMES, "rt", encoding="utf-8", errors="ignore") as f:
        _ = f.readline()
        for linea in f:
            cols = linea.strip().split("\t")
            if len(cols) >= 2:
                nconst = cols[0]
                if nconst in personas_necesarias:
                    nombres[nconst] = cols[1].strip()
                    if len(nombres) >= len(personas_necesarias):
                        break
    print(f"-> {len(nombres):,} nombres asociados.")

    # 5. ESCRITURA
    print(f"\nGenerando '{ARCH_SALIDA}'...")
    Path(ARCH_SALIDA).parent.mkdir(parents=True, exist_ok=True)
    with open(ARCH_SALIDA, "w", encoding="utf-8") as f_out:
        for p in producciones.values():
            directores = [nombres[nid] for nid in p["ids_directores"] if nid in nombres]
            guionistas = [nombres[nid] for nid in p["ids_guionistas"] if nid in nombres]
            actores = [nombres[nid] for nid in p["ids_actores"] if nid in nombres]

            registro_es = {
                "id": p["id"],
                "tipo": p["tipo"],
                "titulo": p["titulo"],
                "titulo_original": p["titulo_original"],
                "es_adulto": p["es_adulto"],
                "anio": p["anio"],
                "anio_fin": p["anio_fin"],
                "duracion": p["duracion"],
                "rango_duracion": p["rango_duracion"],
                "calificacion": p["calificacion"],
                "votos": p["votos"],
                "puntaje_ponderado": p["puntaje_ponderado"],
                "nivel_popularidad": p["nivel_popularidad"],
                "generos": p["generos"],
                "director": ", ".join(directores) if directores else "Desconocido",
                "guionista": ", ".join(guionistas) if guionistas else "Desconocido",
                "actores": ", ".join(actores) if actores else "Desconocido"
            }
            f_out.write(json.dumps(registro_es, ensure_ascii=False) + "\n")

    t_total = (time.time() - t_inicio) / 60
    print(f"\n¡ETL Masivo finalizado con éxito en {t_total:.2f} minutos!")
    print(f"Archivo generado: '{ARCH_SALIDA}'")

if __name__ == "__main__":
    ejecutar_etl(umbral_votos=1)