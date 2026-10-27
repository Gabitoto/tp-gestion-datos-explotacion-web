# 🎬 Catálogo y Análisis IMDb sobre Redis (Modelo Clave-Valor)

Proyecto integral de ingeniería de datos y visualización analítica. Implementa un pipeline completo de extracción, transformación y cruce de datos masivos de **IMDb**, modelado en una base de datos no relacional **Clave-Valor (Redis)** y consumo a través de una capa desacoplada de consultas y un dashboard interactivo en **Streamlit**.

El proyecto está completamente **dockerizado** para desplegarse con un solo comando tanto en entornos de desarrollo como de producción, e incluye una **suite completa de tests automatizados** en memoria.

---

## 📌 Tabla de Contenidos
1. [Arquitectura y Flujo del Proyecto](#-arquitectura-y-flujo-del-proyecto)
2. [Estructura del Repositorio](#-estructura-del-repositorio)
3. [Componentes Construidos](#-componentes-construidos)
4. [Diseño del Modelo Clave-Valor en Redis](#-diseño-del-modelo-clave-valor-en-redis)
5. [🧪 Suite de Tests y Calidad de Código](#-suite-de-tests-y-calidad-de-código)
6. [Ejecución con Docker (Recomendada)](#-ejecución-con-docker-recomendada)
7. [Ejecución Local (Alternativa sin Docker)](#-ejecución-local-alternativa-sin-docker)
8. [Cómo Extender el Proyecto (Nuevas Vistas)](#-cómo-extender-el-proyecto-nuevas-vistas)

---

## 🚀 Arquitectura y Flujo del Proyecto

El proyecto está diseñado bajo una arquitectura modular y por capas, donde cada fase tiene una responsabilidad única:

```mermaid
flowchart TD
    subgraph 1. Ingesta y Exploración
        RAW["Datasets Crudos IMDb\n(.tsv.gz en data/raw/)"]
        EXP["Diagnóstico y Métricas\n(exploracion/)"]
        RAW --> EXP
    end

    subgraph 2. Procesamiento Masivo (ETL)
        RAW --> ETL["Pipeline ETL\n(src/etl/etl.py)"]
        ETL -->|"Limpia, filtra, normaliza,\npondera y cruza nombres"| JSONL["peliculas_limpias.jsonl\n(data/processed/)"]
        JSONL --> AUDIT["Auditoría y Validación\n(src/validacion/auditar_jsonl.py)"]
    end

    subgraph 3. Base Clave-Valor (Redis)
        JSONL --> CARGA["Carga Masiva por Lotes\n(src/carga_redis/cargar_redis.py)"]
        CARGA --> REDIS[("Redis Server\nHashes | Sets | ZSets | Counters")]
    end

    subgraph 4. Capa de Servicios y Presentación
        REDIS --> QUERIES["Capa de Consultas / Vistas\n(src/consultas/vistas.py)"]
        QUERIES --> UI["Aplicación Web Interactiva\n(Streamlit en app/Inicio.py)"]
    end

    subgraph 5. Aseguramiento de Calidad
        TESTS["Suite de Tests (pytest + fakeredis)\nUnitarios | Integración | Smoke UI"]
        TESTS -.->|Valida sin red ni BD externa| ETL
        TESTS -.->|Valida modelo clave-valor| REDIS
        TESTS -.->|Valida contratos| QUERIES
    end
```

---

## 📂 Estructura del Repositorio

```
Trabajo final clave-valor/
├── data/
│   ├── raw/                  # Datasets crudos de IMDb (.tsv.gz descargados)
│   └── processed/            # Salida del ETL (peliculas_limpias.jsonl)
├── src/
│   ├── config.py             # Configuración central (rutas Pathlib, conexión Redis y claves)
│   ├── exploracion/          # Scripts de inspección sin descompresión
│   │   ├── explorar_columnas.py  # Muestra columnas y 3 filas de ejemplo de cada dataset
│   │   └── contar_filas.py       # Cuenta el total de filas exactas por archivo
│   ├── etl/
│   │   └── etl.py            # Pipeline masivo de transformación y cruce de datos
│   ├── validacion/
│   │   └── auditar_jsonl.py  # Verificación de tamaño, cantidad de registros y esquema
│   ├── carga_redis/
│   │   ├── cargar_redis.py       # Ingesta masiva optimizada por pipelines a Redis
│   │   └── prototipo_streaming.py# Prototipo alternativo de carga por streaming web
│   └── consultas/
│       ├── conexion.py       # Singleton de conexión a Redis (con timeouts seguros)
│       └── vistas.py         # Capa de abstracción de datos ("Vistas" analíticas)
├── app/                      # Interfaz gráfica en Streamlit
│   ├── Inicio.py             # Portada y métricas principales de la base
│   └── pages/
│       ├── 1_Dashboard.py    # Gráficos de distribución (géneros, décadas)
│       ├── 2_Rankings.py     # Tablas Top-N dinámicas (votos, nota, ponderado)
│       └── 3_Explorador.py   # Búsqueda por género y ficha técnica por ID
├── tests/                    # Suite de testing automatizada (100% en memoria)
│   ├── conftest.py           # Fixtures, mini-datasets y simulación Fakeredis
│   ├── test_config.py        # Validación de configuración y claves
│   ├── test_etl.py           # Pruebas del pipeline ETL y métricas derivadas
│   ├── test_carga_redis.py   # Pruebas del modelo clave-valor en Redis
│   ├── test_vistas.py        # Pruebas de la capa de consultas analíticas
│   ├── test_exploracion_validacion.py # Pruebas de exploración y auditoría
│   ├── test_pipeline.py      # Pruebas del orquestador CLI y manejo de errores
│   ├── test_estructura.py    # Integridad del repositorio según documentación
│   └── test_app_streamlit.py # Smoke tests de la interfaz gráfica
├── pipeline.py               # Orquestador CLI para ejecutar cualquier fase o el flujo completo
├── Dockerfile                # Imagen Docker de la aplicación Python + Streamlit
├── docker-compose.yml        # Orquestación de contenedores (Redis + App Streamlit)
├── .dockerignore             # Exclusión de archivos pesados y entornos locales del build
├── pytest.ini                # Configuración de ejecución de pytest
├── docs/                     # Memoria técnica y especificaciones del trabajo
├── requirements.txt          # Dependencias de producción (redis, streamlit, pandas)
├── requirements-dev.txt      # Dependencias de desarrollo y test (pytest, fakeredis)
└── README.md
```

---

## ⚙️ Componentes Construidos

| Módulo / Archivo | Rol en el Proyecto |
| :--- | :--- |
| **`docker-compose.yml`** | Orquesta dos servicios interconectados: **Redis 7 Alpine** con persistencia en volumen y healthcheck, y la **App Streamlit** con volúmenes enlazados para desarrollo y datos. |
| **`Dockerfile`** | Construye la imagen basada en `python:3.11-slim`, instala requerimientos del sistema y de Python, y expone el puerto `8501`. |
| **`pipeline.py`** | **Orquestador general**. Permite verificar el estado, descargar datasets automáticamente con descargas atómicas (`.part`), correr el ETL, auditar y cargar a Redis (`--todo` o por fases). |
| **`src/config.py`** | **Única fuente de verdad**. Detecta automáticamente `REDIS_HOST` (sea `localhost` o el contenedor `redis`) y define rutas, umbrales de negocio y nombres semánticos de claves. |
| **`src/etl/etl.py`** | Filtra por formatos narrativos y votos mínimos ($\ge 1$), traduce géneros y tipos al español, clasifica duración y popularidad, calcula puntaje ponderado Bayesiano y cruza directores, guionistas y hasta 6 actores con sus nombres reales sobre más de 100M de relaciones. |
| **`src/validacion/auditar_jsonl.py`** | Control de calidad que verifica la existencia del archivo limpio, reporta peso en MB, conteo de filas y visualiza el esquema del primer registro. |
| **`src/carga_redis/cargar_redis.py`** | Lee `peliculas_limpias.jsonl` e inserta masivamente en Redis usando `pipeline(transaction=False)` en bloques de 2.500 registros. Pre-agrega frecuencias por década y aplica filtros de confiabilidad. |
| **`src/consultas/vistas.py`** | Separa la lógica de base de datos de la interfaz visual. Cada función representa una consulta o "vista" que consume Hashes, Sets o Sorted Sets en Redis en bloques optimizados. |
| **`app/Inicio.py` y `pages/`** | Frontend multipágina en Streamlit con manejo robusto de excepciones ante caídas de servidor y componentes modernos. |
| **`tests/`** | Suite integral de 8 módulos de pruebas automatizadas que validan la lógica sin necesidad de levantar servicios externos. |

---

## 🧠 Diseño del Modelo Clave-Valor en Redis

El modelo aprovecha las estructuras nativas de Redis para responder consultas en tiempo constante $O(1)$ o logarítmico $O(\log N)$:

1. **Hashes (`HSET`)**:
   - `pelicula:{id}`: Guarda la entidad completa (`titulo`, `anio`, `duracion`, `calificacion`, `votos`, `puntaje_ponderado`, `director`, `actores`, etc.).
   - `kpi:generos:conteo`: Acumulador de frecuencias por género actualizado atómicamente con `HINCRBY`.
   - `kpi:decadas:conteo`: Acumulador pre-agregado de producciones por década para evitar escaneos globales en tiempo de consulta.
2. **Sets (`SADD`)**:
   - Índices secundarios para filtrado instantáneo:
     - `filtro:genero:{genero}`
     - `filtro:decada:{decada}` (excluye años desconocidos o nulos)
     - `filtro:director:{nombre}`
     - `filtro:actor:{nombre}`
   - Permiten operaciones nativas como `SINTER` para cruzar criterios sin escanear toda la base.
3. **Sorted Sets (`ZSET` / `ZADD`)**:
   - `ranking:votos`: Ranking histórico ordenado por volumen de votos.
   - `ranking:calificacion`: Ranking ordenado por nota promedio (con filtro de confiabilidad $\ge 100.000$ votos).
   - `ranking:ponderado`: Ranking ordenado por estimación Bayesiana que equilibra nota y popularidad.
   - Consultas con `ZREVRANGE` en tiempo sub-milisegundo gracias a la estructura SkipList interna.
4. **Strings / Contadores (`INCR`)**:
   - `kpi:total_peliculas`: Contador escalar del universo de datos cargado.

---

## 🧪 Suite de Tests y Calidad de Código

El proyecto cuenta con una cobertura integral de pruebas automatizadas desarrolladas con **pytest** y **fakeredis**. Los tests corren **completamente en memoria**, sin requerir conexión a internet, sin necesidad de un servidor Redis activo y sin tener descargados los datasets de 2 GB.

### 1. Qué cubre la suite de tests:
- **`test_config.py`**: Valida rutas relativas al proyecto, compatibilidad de variables de entorno (Docker vs. local) y unicidad de nombres de claves.
- **`test_etl.py`**: Prueba las funciones de clasificación pura (duración, popularidad), la fórmula de puntaje Bayesiano y ejecuta un pipeline ETL completo sobre datasets TSV gzip sintéticos en memoria.
- **`test_carga_redis.py`**: Valida la inserción por lotes, pre-agregaciones, sanitización de décadas y consistencia de Hashes, Sets y Sorted Sets.
- **`test_vistas.py`**: Comprueba que la capa de consultas retorne las estructuras de datos esperadas, ordene correctamente cronológica y cuantitativamente, y soporte bases vacías sin fallar.
- **`test_exploracion_validacion.py`**: Valida que los scripts de exploración lean encabezados y que el auditor reporte métricas y esquemas correctamente.
- **`test_pipeline.py`**: Verifica que todos los flags del CLI funcionen, simula descargas interrumpidas garantizando que no queden archivos corruptos y comprueba el control de flujo.
- **`test_estructura.py`**: Asegura que todos los archivos listados en la documentación existan y que ningún módulo ejecute efectos secundarios al ser importado.
- **`test_app_streamlit.py`**: Realiza *smoke tests* de la interfaz gráfica comprobando que renderice métricas, gráficos y tablas adecuadamente ante bases activas o caídas.

### 2. Cómo ejecutar los tests:

Instalá las dependencias de desarrollo y ejecutá pytest:
```powershell
# Instalar dependencias de testing en el entorno virtual
uv pip install -r requirements-dev.txt --python .venv\Scripts\python.exe

# Ejecutar la suite completa de tests
.venv\Scripts\pytest.exe
```

Para correr un módulo específico o ver el reporte detallado:
```powershell
.venv\Scripts\pytest.exe tests/test_etl.py -v
.venv\Scripts\pytest.exe tests/test_carga_redis.py -v
```

---

## 🐳 Ejecución con Docker (Recomendada)

Con Docker no necesitas instalar Python ni Redis en tu computadora. Todo se ejecuta aislado en contenedores.

### 1. Iniciar los Servicios (Redis + Streamlit)
Levantá la base de datos y la aplicación web:
```bash
docker compose up -d --build
```
> Redis quedará disponible en el puerto `6379` y la aplicación en **`http://localhost:8501`**.

### 2. Verificar el Estado del Sistema
Desde tu terminal, consultá el estado de los datos y de Redis dentro del contenedor:
```bash
docker compose run --rm app python pipeline.py --estado
```

### 3. Ejecutar el Pipeline Completo
Para ejecutar la descarga de datasets crudos, el ETL, la validación y la carga a Redis en un solo paso:
```bash
docker compose run --rm app python pipeline.py --todo
```

*(Opcional)* Si preferís correr fase por fase dentro de Docker:
```bash
docker compose run --rm app python pipeline.py --descargar     # Descarga los 4 .tsv.gz
docker compose run --rm app python pipeline.py --etl           # Procesa y genera el JSONL
docker compose run --rm app python pipeline.py --auditar       # Valida el JSONL
docker compose run --rm app python pipeline.py --cargar-redis  # Ingesta en Redis
```

Los datos descargados y procesados se guardan directamente en tu carpeta local `data/` gracias al volumen montado en el contenedor.

### 4. Detener los Contenedores
```bash
docker compose down
```

---

## 💻 Ejecución Local (Alternativa sin Docker)

Si prefieres ejecutar el proyecto directamente en Windows con Python:

### Paso 1: Configurar el Entorno con `uv`
```powershell
uv venv .venv
uv pip install -r requirements.txt --python .venv\Scripts\python.exe
```

### Paso 2: Ejecutar con el Orquestador
Asegurate de tener Redis activo en `localhost:6379` (en WSL o servicio local) y ejecutá:
```powershell
# Ver estado actual
.venv\Scripts\python.exe pipeline.py --estado

# Ejecutar el flujo completo
.venv\Scripts\python.exe pipeline.py --todo

# Iniciar la interfaz web
.venv\Scripts\streamlit.exe run app/Inicio.py
```

---

## 🛠️ Cómo Extender el Proyecto (Nuevas Vistas)

El desacoplamiento entre datos y frontend permite agregar funcionalidades fácilmente:

1. **Definir la consulta en Redis**:
   Agregá la función correspondiente en `src/consultas/vistas.py` (ej. consultar directores más prolíficos o cruzar filtros con `sinter`).
2. **Crear la vista en Streamlit**:
   Creá un archivo nuevo en `app/pages/` (por ejemplo `4_Directores.py`), importá la función desde `src.consultas.vistas` y mostrá los datos con componentes de Streamlit (`st.bar_chart`, `st.dataframe`, etc.).

