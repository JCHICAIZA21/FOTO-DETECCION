from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import json
import traceback
from datetime import datetime
import time
import threading
import hashlib
import logging
from typing import List, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales
EVENTOS_FILE = "/eventos/eventos_consolidados.json"
RUNT_SERVICE_URL = os.getenv('RUNT_SERVICE_URL', 'http://runt-service:8002')
API_URL = os.getenv('API_URL', 'http://api-consumer:8000')

last_process = {
    "timestamp": time.time(),
    "message": "No se ha ejecutado ningún proceso",
    "source": "system"
}
is_processing = False
last_hash = None
monitoring_thread = None

def calculate_file_hash(file_path):
    """Calcula el hash MD5 del archivo"""
    if not os.path.exists(file_path):
        return None
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def process_events():
    """Procesa los eventos del archivo JSON."""
    global last_process, is_processing
    try:
        if not os.path.exists(EVENTOS_FILE):
            logger.warning(f"El archivo {EVENTOS_FILE} no existe")
            last_process = {
                "timestamp": time.time(),
                "message": f"El archivo {EVENTOS_FILE} no existe",
                "source": "system"
            }
            return

        logger.info(f"Leyendo archivo de eventos: {EVENTOS_FILE}")
        with open(EVENTOS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Eventos leídos: {len(data)}")
            
        if not data:
            logger.warning("El archivo JSON está vacío")
            last_process = {
                "timestamp": time.time(),
                "message": "El archivo JSON está vacío",
                "source": "system"
            }
            return

        # Procesar los eventos directamente
        try:
            from process_json import process_json
            processed_data = process_json(data)
            logger.info(f"Eventos procesados: {len(processed_data['processed'])}")
            
            last_process = {
                "timestamp": time.time(),
                "message": f"Se procesaron {len(processed_data['processed'])} nuevos eventos",
                "source": "system"
            }
        except ImportError:
            logger.error("No se pudo importar process_json")
            raise Exception("Error al importar el módulo process_json")
        
    except Exception as e:
        logger.error(f"Error procesando eventos: {str(e)}")
        logger.error(traceback.format_exc())
        last_process = {
            "timestamp": time.time(),
            "message": f"Error procesando eventos: {str(e)}",
            "source": "system"
        }
    finally:
        is_processing = False

def monitor_file_changes():
    """Monitorea cambios en el archivo JSON."""
    global last_hash, is_processing
    logger.info(f"Iniciando monitoreo de archivos en {EVENTOS_FILE}...")
    
    while True:
        try:
            current_hash = calculate_file_hash(EVENTOS_FILE)
            
            if current_hash is None:
                logger.warning(f"El archivo {EVENTOS_FILE} no existe")
                time.sleep(5)
                continue
                
            if last_hash is None:
                last_hash = current_hash
                logger.info("Hash inicial establecido")
                time.sleep(1)
                continue
                
            if current_hash != last_hash and not is_processing:
                logger.info("Detectado cambio en el archivo JSON")
                # Esperar un segundo para asegurar que el archivo se ha escrito completamente
                time.sleep(1)
                
                # Verificar que el archivo existe y no está vacío
                if os.path.exists(EVENTOS_FILE) and os.path.getsize(EVENTOS_FILE) > 0:
                    is_processing = True
                    process_events()
                    last_hash = current_hash
                else:
                    logger.warning("El archivo no existe o está vacío después del cambio")
            
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error en el monitoreo: {str(e)}")
            logger.error(traceback.format_exc())
            time.sleep(5)

@app.on_event("startup")
async def startup_event():
    """Inicializa el monitoreo de archivos al arrancar."""
    global monitoring_thread
    logger.info("Iniciando servicio de monitoreo...")
    
    # Iniciar el thread de monitoreo
    monitoring_thread = threading.Thread(target=monitor_file_changes, daemon=True)
    monitoring_thread.start()
    
    # Verificar si el archivo existe al inicio
    if os.path.exists(EVENTOS_FILE):
        logger.info(f"Archivo {EVENTOS_FILE} encontrado al inicio")
        global last_hash
        last_hash = calculate_file_hash(EVENTOS_FILE)
    else:
        logger.warning(f"Archivo {EVENTOS_FILE} no encontrado al inicio")

@app.get("/health")
async def health_check():
    """Endpoint para verificar la salud del servicio."""
    try:
        return {
            "status": "healthy",
            "monitoring_active": monitoring_thread is not None and monitoring_thread.is_alive(),
            "last_process": last_process,
            "file_exists": os.path.exists(EVENTOS_FILE),
            "file_path": EVENTOS_FILE,
            "is_processing": is_processing,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error en health check: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.post("/process")
async def process_json_endpoint(background_tasks: BackgroundTasks):
    """Endpoint para procesar el archivo JSON manualmente."""
    global is_processing
    if is_processing:
        raise HTTPException(status_code=400, detail="Ya hay un proceso en ejecución")
    
    is_processing = True
    background_tasks.add_task(process_events)
    return {"message": "Proceso iniciado"}

@app.post("/generate-pdf")
async def generate_pdf(request: Request):
    try:
        # Obtener el cuerpo de la solicitud como JSON
        request_data = await request.json()
        
        # Reenviar la solicitud al servicio RUNT
        response = requests.post(
            f"{RUNT_SERVICE_URL}/generate-pdf",
            json=request_data
        )
        
        if response.ok:
            # Devolver el PDF como respuesta binaria
            return Response(
                content=response.content,
                media_type="application/pdf"
            )
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error from RUNT service: {response.text}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating PDF: {str(e)}"
        )

@app.get("/get-plate")
async def get_plate():
    """Obtiene las placas del archivo eventos_consolidados.json."""
    try:
        if not os.path.exists(EVENTOS_FILE):
            return {
                "success": False,
                "error": f"Archivo {EVENTOS_FILE} no encontrado",
                "debug": {
                    "current_dir": os.getcwd(),
                    "file_path": EVENTOS_FILE,
                    "files": os.listdir()
                }
            }

        with open(EVENTOS_FILE, "r", encoding='utf-8') as file:
            try:
                data = json.load(file)
                plates = []
                
                # Si es una lista de objetos
                if isinstance(data, list):
                    plates = [item["plate"] for item in data if "plate" in item]
                # Si es un objeto con plate
                elif isinstance(data, dict) and "plate" in data:
                    plates = [data["plate"]]
                
                if plates:
                    # Limpiar y validar placas
                    plates = [p.strip().upper() for p in plates if p and len(p.strip()) >= 5]
                    logger.info(f"Placas encontradas: {plates}")
                    return {
                        "success": True,
                        "plates": plates
                    }
                else:
                    return {
                        "success": False,
                        "error": "No se encontraron placas en el archivo",
                        "debug": {
                            "file_path": EVENTOS_FILE,
                            "data_type": type(data).__name__
                        }
                    }
                    
            except json.JSONDecodeError as e:
                logger.error(f"Error parseando JSON: {e}")
                return {
                    "success": False,
                    "error": f"Error al parsear el archivo JSON: {str(e)}",
                    "debug": {
                        "file_path": EVENTOS_FILE,
                        "error_details": str(e)
                    }
                }
            
    except Exception as e:
        logger.error(f"Error al leer el archivo: {str(e)}")
        return {
            "success": False,
            "error": f"Error al leer el archivo: {str(e)}",
            "debug": {
                "current_dir": os.getcwd(),
                "file_path": EVENTOS_FILE,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        } 