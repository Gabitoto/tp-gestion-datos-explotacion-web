FROM python:3.11-slim

# Evitar que Python bufferice la salida y no escriba bytecode .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instalar curl y herramientas del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python aprovechando la caché de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente y estructura del proyecto
COPY src/ ./src/
COPY app/ ./app/
COPY pipeline.py .
COPY data/ ./data/

# Exponer el puerto de la aplicación Streamlit
EXPOSE 8501

# Comando por defecto: Iniciar la interfaz Streamlit en 0.0.0.0:8501
CMD ["streamlit", "run", "app/Inicio.py", "--server.port=8501", "--server.address=0.0.0.0"]
