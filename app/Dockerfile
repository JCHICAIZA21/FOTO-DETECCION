# Usa una imagen base de Python
FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configura el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de la aplicación
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear directorios necesarios
RUN mkdir -p /app/output/pdfs /app/output/images /eventos
RUN chmod -R 777 /app/output /eventos

# Agregar un script de entrada
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
