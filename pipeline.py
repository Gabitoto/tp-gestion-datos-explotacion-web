"""Orquestador CLI del pipeline completo de IMDb y Redis.
Permite ejecutar cada fase o el flujo completo de forma secuencial.
"""
import argparse
import socket
import sys
import urllib.request
from pathlib import Path

# Configurar stdout para evitar errores de encoding en Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Aseguramos que la raíz esté en sys.path
RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.config import (
    DIR_RAW, DIR_PROCESADOS, ARCH_RATINGS, ARCH_BASICS,
    ARCH_PRINCIPALS, ARCH_NAMES, ARCH_JSONL, REDIS_HOST, REDIS_PORT
)

URLS_IMDB = {
    ARCH_RATINGS: "https://datasets.imdbws.com/title.ratings.tsv.gz",
    ARCH_BASICS: "https://datasets.imdbws.com/title.basics.tsv.gz",
    ARCH_PRINCIPALS: "https://datasets.imdbws.com/title.principals.tsv.gz",
    ARCH_NAMES: "https://datasets.imdbws.com/name.basics.tsv.gz",
}


def _titulo(texto):
    print("\n" + "=" * 60)
    print(texto)
    print("=" * 60)


def descargar_archivos_raw():
    """Descarga los 4 archivos oficiales de IMDb en data/raw si no existen."""
    DIR_RAW.mkdir(parents=True, exist_ok=True)
    _titulo("FASE 1: VERIFICACIÓN Y DESCARGA DE DATASETS CRUDOS")

    for destino, url in URLS_IMDB.items():
        destino = Path(destino)
        if destino.exists() and destino.stat().st_size > 0:
            mb = destino.stat().st_size / (1024 * 1024)
            print(f"[OK] Ya existe: {destino.name} ({mb:.1f} MB)")
            continue

        print(f"[>>] Descargando {destino.name} desde {url}...")
        # Se descarga a un .part y se renombra al final: si se corta la descarga,
        # no queda un archivo incompleto que luego se tome como válido.
        temporal = destino.with_name(destino.name + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req) as response, open(temporal, "wb") as out_file:
                total_bytes = int(response.info().get("Content-Length", 0) or 0)
                descargados = 0
                bloque = 1024 * 1024  # 1 MB
                while True:
                    buffer = response.read(bloque)
                    if not buffer:
                        break
                    out_file.write(buffer)
                    descargados += len(buffer)
                    if total_bytes:
                        progreso = (descargados / total_bytes) * 100
                        print(f"\r  Progreso: {descargados / (1024*1024):.1f} MB / {total_bytes / (1024*1024):.1f} MB ({progreso:.1f}%)", end="", flush=True)
                    else:
                        print(f"\r  Descargados: {descargados / (1024*1024):.1f} MB", end="", flush=True)
            temporal.replace(destino)
        except BaseException:
            temporal.unlink(missing_ok=True)
            raise
        print(f"\n[OK] Completado: {destino.name}")


def ejecutar_exploracion():
    """Ejecuta los scripts de exploración de columnas y filas."""
    _titulo("FASE 2: EXPLORACIÓN PRELIMINAR")
    from src.exploracion.explorar_columnas import explorar
    from src.exploracion.contar_filas import contar
    explorar()
    contar()


def ejecutar_etl():
    """Ejecuta el pipeline ETL de limpieza, normalización y cruce."""
    _titulo("FASE 3: PIPELINE ETL MASIVO")
    DIR_PROCESADOS.mkdir(parents=True, exist_ok=True)
    from src.etl.etl import ejecutar_etl as correr_etl
    correr_etl(umbral_votos=1)


def ejecutar_auditoria():
    """Valida el archivo generado peliculas_limpias.jsonl. Devuelve True si es válido."""
    _titulo("FASE 4: AUDITORÍA Y CONTROL DE CALIDAD")
    from src.validacion.auditar_jsonl import auditar
    resultado = auditar(ARCH_JSONL)
    return bool(resultado and resultado["registros"] > 0)


def ejecutar_carga_redis():
    """Ejecuta la ingesta masiva en Redis."""
    _titulo(f"FASE 5: CARGA MASIVA A REDIS (CLAVE-VALOR)\nHost: {REDIS_HOST}:{REDIS_PORT}")
    from src.carga_redis.cargar_redis import cargar_a_redis
    cargar_a_redis()


def redis_disponible(host=None, port=None, timeout=1.0):
    """Chequeo rápido de puerto TCP (evita esperas largas si Redis está apagado)."""
    try:
        with socket.create_connection((host or REDIS_HOST, port or REDIS_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def verificar_estado():
    """Verifica el estado del sistema, archivos y conexión a Redis."""
    import redis
    print("\n=== ESTADO DEL PROYECTO ===")
    print("1. Archivos crudos (data/raw):")
    for f in [ARCH_RATINGS, ARCH_BASICS, ARCH_PRINCIPALS, ARCH_NAMES]:
        if f.exists():
            print(f"   [OK] {f.name} ({f.stat().st_size / (1024*1024):.1f} MB)")
        else:
            print(f"   [X]  {f.name} (FALTA)")

    print("\n2. Dataset procesado (data/processed):")
    if ARCH_JSONL.exists():
        print(f"   [OK] {ARCH_JSONL.name} ({ARCH_JSONL.stat().st_size / (1024*1024):.1f} MB)")
    else:
        print(f"   [X]  {ARCH_JSONL.name} (FALTA - requiere correr ETL)")

    print(f"\n3. Conexión a Redis ({REDIS_HOST}:{REDIS_PORT}):")
    if not redis_disponible():
        print(f"   [X]  No se pudo conectar a Redis en {REDIS_HOST}:{REDIS_PORT} (servidor apagado o inalcanzable)")
        return
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_timeout=5)
        total_claves = r.dbsize()
        print(f"   [OK] Conectado exitosamente. Total de claves en Redis: {total_claves:,}")
    except Exception as e:
        print(f"   [X]  Redis respondió con error: {e}")


def construir_parser():
    parser = argparse.ArgumentParser(description="Gestor secuencial del proyecto IMDb en Redis")
    parser.add_argument("--descargar", action="store_true", help="Descargar los 4 datasets oficiales de IMDb a data/raw")
    parser.add_argument("--explorar", action="store_true", help="Explorar columnas y contar filas de los datasets crudos")
    parser.add_argument("--etl", action="store_true", help="Ejecutar el pipeline ETL y generar peliculas_limpias.jsonl")
    parser.add_argument("--auditar", action="store_true", help="Auditar el archivo JSONL procesado")
    parser.add_argument("--cargar-redis", action="store_true", help="Cargar el archivo JSONL en Redis")
    parser.add_argument("--todo", action="store_true", help="Ejecutar el flujo completo de principio a fin (descargar, etl, auditar, cargar)")
    parser.add_argument("--estado", action="store_true", help="Verificar el estado de archivos y de Redis")
    return parser


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = construir_parser().parse_args(argv)

    if not argv:
        verificar_estado()
        print("\nPara ejecutar una acción específica use:")
        print("  python pipeline.py --descargar")
        print("  python pipeline.py --etl")
        print("  python pipeline.py --auditar")
        print("  python pipeline.py --cargar-redis")
        print("  python pipeline.py --todo")
        return 0

    if args.estado:
        verificar_estado()
        return 0

    if args.todo:
        descargar_archivos_raw()
        ejecutar_etl()
        if not ejecutar_auditoria():
            print("\n[X] La auditoría falló: se cancela la carga a Redis.")
            return 1
        ejecutar_carga_redis()
        verificar_estado()
        return 0

    if args.descargar:
        descargar_archivos_raw()
    if args.explorar:
        ejecutar_exploracion()
    if args.etl:
        ejecutar_etl()
    if args.auditar and not ejecutar_auditoria():
        return 1
    if args.cargar_redis:
        ejecutar_carga_redis()
    return 0


if __name__ == "__main__":
    sys.exit(main())
