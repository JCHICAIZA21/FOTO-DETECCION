FROM python:3.9-slim

# Instalar Node.js, npm y dependencias de WeasyPrint
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    bash \
    curl \
    iputils-ping \
    telnet \
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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar los archivos necesarios
COPY requirements.txt .
COPY jsrsasign-js.txt .
COPY sign.js .
COPY claveprivada.pkcs8.pem .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos
COPY . .

# Agregar el directorio actual al PYTHONPATH
ENV PYTHONPATH=/app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"] 