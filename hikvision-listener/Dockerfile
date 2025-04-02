# Dockerfile
FROM python:3.11-slim

# Instalar dependencias
RUN pip install --no-cache-dir requests flask xmltodict

# Crear carpeta de trabajo
WORKDIR /app

# Copiar el script que se conecta a la cámara
COPY app.py .

# Exponer el puerto (para notificaciones tipo push desde la cámara)
EXPOSE 8080

# Ejecutar el script
CMD ["python", "app.py"] 