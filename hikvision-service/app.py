import json
import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import time

app = Flask(__name__)
CORS(app)

# Configuración
EVENTOS_FILE = "/eventos/eventos_consolidados.json"
API_SERVICE_URL = "http://api-consumer:8000/process"  # URL del servicio API

def notify_api_service():
    """Notifica al servicio API que hay un nuevo evento para procesar"""
    try:
        print(f"[{datetime.now()}] Intentando notificar al servicio API...")
        headers = {'Content-Type': 'application/json'}
        # Enviar una solicitud POST vacía para indicar que es un procesamiento automático
        response = requests.post("http://api-consumer:8000/process", headers=headers, json={}, timeout=10)
        print(f"[{datetime.now()}] Respuesta del servicio API: {response.status_code}")
        print(f"[{datetime.now()}] Contenido de la respuesta: {response.text}")
        
        if response.status_code == 200:
            print(f"[{datetime.now()}] Notificación enviada exitosamente al servicio API")
            # Verificar si el procesamiento fue exitoso
            data = response.json()
            if data.get('source') == 'automático':
                print(f"[{datetime.now()}] Procesamiento automático completado: {data.get('message')}")
            else:
                print(f"[{datetime.now()}] Advertencia: El procesamiento no fue automático")
                # Intentar nuevamente con un pequeño retraso
                time.sleep(1)
                response = requests.post("http://api-consumer:8000/process", headers=headers, json={}, timeout=10)
                print(f"[{datetime.now()}] Segundo intento - Respuesta: {response.status_code}")
        else:
            print(f"[{datetime.now()}] Error al notificar al servicio API: {response.status_code}")
            print(f"[{datetime.now()}] Detalles del error: {response.text}")
    except requests.exceptions.Timeout:
        print(f"[{datetime.now()}] Timeout al intentar notificar al servicio API")
    except requests.exceptions.ConnectionError:
        print(f"[{datetime.now()}] Error de conexión al intentar notificar al servicio API")
    except Exception as e:
        print(f"[{datetime.now()}] Error inesperado al notificar al servicio API: {str(e)}")

@app.route('/eventos', methods=['POST'])
def receive_event():
    try:
        data = request.get_json()
        if not data:
            print(f"[{datetime.now()}] Error: No se recibieron datos en la solicitud")
            return jsonify({"error": "No se recibieron datos"}), 400

        print(f"[{datetime.now()}] Evento recibido: {json.dumps(data, indent=2)}")

        # Asegurar que el directorio existe
        os.makedirs(os.path.dirname(EVENTOS_FILE), exist_ok=True)

        # Leer eventos existentes
        eventos = []
        if os.path.exists(EVENTOS_FILE):
            with open(EVENTOS_FILE, 'r', encoding='utf-8') as f:
                eventos = json.load(f)
                print(f"[{datetime.now()}] Eventos existentes cargados: {len(eventos)}")

        # Agregar el nuevo evento
        eventos.append(data)
        print(f"[{datetime.now()}] Nuevo evento agregado. Total de eventos: {len(eventos)}")

        # Guardar todos los eventos
        with open(EVENTOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
        print(f"[{datetime.now()}] Eventos guardados en {EVENTOS_FILE}")

        # Notificar al servicio API
        notify_api_service()

        return jsonify({"message": "Evento recibido y guardado correctamente"}), 200

    except Exception as e:
        print(f"[{datetime.now()}] Error al procesar el evento: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"[{datetime.now()}] Iniciando servidor Hikvision en puerto 8080")
    app.run(host='0.0.0.0', port=8080) 