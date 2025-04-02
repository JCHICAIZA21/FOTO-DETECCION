import base64
import os
import requests
from database import get_db
from crud import get_attributes
import uuid
from typing import Dict, List, Tuple
import json
import time
import httpx

# Directorios de salida
IMAGE_DIR = "output/images"
VIDEO_DIR = "output/videos"
HIKVISION_FILE = "/eventos/eventos_consolidados.json"
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

def save_base64_file(data, file_type, plate):
    try:
        unique_id = str(uuid.uuid4())
        if file_type == "image":
            file_path = os.path.join(IMAGE_DIR, f"{plate}_{unique_id}.png")
        else:
            file_path = os.path.join(VIDEO_DIR, f"{plate}_{unique_id}.mp4")
            
        with open(file_path, "wb") as file:
            file.write(base64.b64decode(data))
        return file_path
    except Exception as e:
        return f"Error al guardar archivo: {e}"

def clean_json_content(content: str) -> str:
    """Limpia y formatea el contenido JSON."""
    # Eliminar espacios en blanco y saltos de línea innecesarios
    content = content.strip()
    
    # Eliminar comas extra al final de los objetos
    content = content.replace('},\n}', '}}')
    content = content.replace('},\n]', '}]')
    
    # Eliminar comas sueltas antes de cerrar el array
    content = content.replace(',\n]', ']')
    content = content.replace(',]', ']')
    
    # Si hay una coma seguida de varios saltos de línea y un cierre
    content = content.replace(',\n\n}', '}')
    content = content.replace(',\n\n]', ']')
    
    # Si no está en un array, envolverlo en uno
    if not content.startswith('['):
        content = '[' + content + ']'
    
    # Asegurarse de que el contenido termine correctamente
    if content.endswith(','):
        content = content[:-1]
    
    return content

def validate_json_structure(record: dict) -> bool:
    """Valida la estructura básica de un registro JSON."""
    required_fields = [
        "event_id", "device_id", "plate", "date", "evidences"
    ]
    
    return all(field in record for field in required_fields)

def read_hikvision_events():
    """Lee los eventos desde el archivo de Hikvision."""
    try:
        if os.path.exists(HIKVISION_FILE):
            with open(HIKVISION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error leyendo eventos de Hikvision: {e}")
        return []

async def send_to_runt_service(data: dict):
    """Envía los datos procesados al servicio RUNT."""
    try:
        runt_service_url = os.getenv("RUNT_SERVICE_URL", "http://runt-service:8000")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{runt_service_url}/process-runt",
                json=data
            )
            response.raise_for_status()
            result = response.json()
            print(f"Respuesta del servicio RUNT: {result}")
            return result
    except Exception as e:
        print(f"Error enviando datos al servicio RUNT: {str(e)}")
        return None

async def process_json(json_data=None):
    """Procesa el archivo JSON y envía los datos al servicio RUNT."""
    try:
        if json_data is None:
            json_data = read_hikvision_events()
            
        processed_records = []
        for record in json_data:
            try:
                # Procesar el registro
                processed_record = {
                    "plate": record.get("plate"),
                    "event_id": record.get("event_id"),
                    "device_id": record.get("device_id"),
                    "date": record.get("date"),
                    "evidences": record.get("evidences", {}),
                    "video_filename": record.get("video_filename")
                }
                
                # Enviar al servicio RUNT
                result = await send_to_runt_service(processed_record)
                if result and "error" not in result:
                    processed_records.append(processed_record)
                else:
                    print(f"Error procesando registro: {result}")
                    
            except Exception as e:
                print(f"Error procesando registro: {str(e)}")
                continue
                
        return processed_records
        
    except Exception as e:
        print(f"Error en process_json: {str(e)}")
        return []
