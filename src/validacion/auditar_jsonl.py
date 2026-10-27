import json
import sys
from pathlib import Path

from src.config import ARCH_JSONL


def auditar(archivo=ARCH_JSONL):
    """Audita el JSONL del ETL. Devuelve {registros, mb, primer_registro} o None si no existe."""
    archivo = Path(archivo)
    if not archivo.exists():
        print(f"Error: No se encontró el archivo '{archivo}'. Ejecutá antes: python -m src.etl.etl")
        return None

    print("=" * 60)
    print(f"AUDITORÍA DE REGISTROS: {archivo.name}")
    print("=" * 60)

    peso_mb = archivo.stat().st_size / (1024 * 1024)

    contador = 0
    primera_linea = None

    with open(archivo, "r", encoding="utf-8") as f:
        for linea in f:
            if contador == 0:
                primera_linea = linea
            contador += 1

    print(f"\n-> Total de registros/filas: {contador:,}")
    print(f"-> Tamaño en disco: {peso_mb:.2f} MB")

    ejemplo = None
    if primera_linea:
        print("\n--- EJEMPLO DEL PRIMER REGISTRO ---")
        ejemplo = json.loads(primera_linea)
        for clave, valor in ejemplo.items():
            print(f"  {clave}: {valor}")

    print("=" * 60)
    return {"registros": contador, "mb": peso_mb, "primer_registro": ejemplo}


if __name__ == "__main__":
    if auditar() is None:
        sys.exit(1)