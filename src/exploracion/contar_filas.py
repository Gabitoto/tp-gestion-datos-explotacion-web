import gzip
from pathlib import Path

from src.config import ARCHIVOS_RAW

archivos = ARCHIVOS_RAW


def contar(archivos=ARCHIVOS_RAW):
    """Cuenta las filas de datos (sin encabezado) de cada .tsv.gz. Devuelve {archivo: filas}."""
    resultado = {}
    print("=== CONTEO DE FILAS EXACTAS POR ARCHIVO ===")
    for nombre in archivos:
        nombre = Path(nombre)
        print(f"Contando {nombre.name}...", end=" ", flush=True)
        contador = 0
        with gzip.open(nombre, "rt", encoding="utf-8", errors="ignore") as f:
            for _ in f:
                contador += 1
        # Restamos 1 fila del encabezado
        filas_datos = max(contador - 1, 0)
        resultado[nombre.name] = filas_datos
        print(f"-> {filas_datos:,} filas.")
    return resultado


if __name__ == "__main__":
    contar()