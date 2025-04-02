#!/bin/bash

# Esperar a que la base de datos esté lista
echo "Esperando a que la base de datos esté lista..."
until PGPASSWORD=password psql -h db -U postgres -d json_processor -c '\q'; do
  echo "Esperando conexión con la base de datos..."
  sleep 1
done
echo "Base de datos lista!"

# Esperar a que el servicio RUNT esté listo
echo "Esperando a que el servicio RUNT esté listo..."
until curl -s http://runt-service:8002/health > /dev/null; do
  echo "Esperando conexión con el servicio RUNT..."
  sleep 1
done
echo "Servicio RUNT listo!"

if [ "$SERVICE_TYPE" = "api" ]; then
    echo "Iniciando API Consumer..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
elif [ "$SERVICE_TYPE" = "frontend" ]; then
    echo "Iniciando Frontend..."
    streamlit run frontend.py --server.port 8501 --server.address 0.0.0.0
else
    echo "SERVICE_TYPE no válido"
    exit 1
fi 