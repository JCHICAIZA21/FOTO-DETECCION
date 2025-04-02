# Usa una imagen base de Python
FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Configura el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar requirements.txt
COPY api-consumer/requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todos los archivos necesarios
COPY api-consumer/main.py .
COPY app/process_json.py .
COPY app/database.py .
COPY app/models.py .
COPY app/crud.py .
COPY app/global_vars.py .
COPY app/api_helpers.py .

# Crear directorios necesarios
RUN mkdir -p /eventos /app/output/images

# Exponer el puerto
EXPOSE 8000

# Comando para iniciar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 