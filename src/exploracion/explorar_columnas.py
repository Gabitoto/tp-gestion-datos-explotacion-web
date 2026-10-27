import gzip
from pathlib import Path

from src.config import ARCHIVOS_RAW

archivos = ARCHIVOS_RAW


def explorar(archivos=ARCHIVOS_RAW, filas_ejemplo=3):
    """Imprime columnas y filas de ejemplo de cada .tsv.gz. Devuelve {archivo: columnas}."""
    columnas_por_archivo = {}
    for nombre in archivos:
        nombre = Path(nombre)
        print("=" * 70)
        print(f"ARCHIVO: {nombre.name}")
        print("=" * 70)

        with gzip.open(nombre, "rt", encoding="utf-8", errors="ignore") as f:
            # Fila 1: Encabezados / Nombres de columnas
            encabezado = f.readline().strip().split("\t")
            columnas_por_archivo[nombre.name] = encabezado
            print("\n--- COLUMNAS DISPONIBLES ---")
            for i, col in enumerate(encabezado):
                print(f"[{i}] {col}")

            print(f"\n--- PRIMERAS {filas_ejemplo} FILAS DE EJEMPLO ---")
            for num_fila in range(1, filas_ejemplo + 1):
                linea = f.readline().strip()
                if not linea:
                    break
                valores = linea.split("\t")
                print(f"\nFila {num_fila}:")
                for col_nombre, val in zip(encabezado, valores):
                    print(f"  {col_nombre}: {val}")
        print("\n")
    return columnas_por_archivo


if __name__ == "__main__":
    explorar()