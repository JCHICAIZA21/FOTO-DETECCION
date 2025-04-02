from fastapi import FastAPI, Depends, Response, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db, SessionLocal, init_db
from crud import create_attribute, get_attributes
from process_json import process_json, clean_json_content
from template_generator import TemplateGenerator
from api_client import RuntAPIClient
from global_vars import GlobalVars
import json
import os
from fastapi.middleware.cors import CORSMiddleware
import zipfile
import tempfile
from datetime import datetime
import re

# Agregar al inicio del archivo, después de los imports
os.makedirs('output/pdfs', exist_ok=True)
os.makedirs('output/images', exist_ok=True)

# Definir la ruta del archivo de eventos consolidados
EVENTOS_FILE = "/eventos/eventos_consolidados.json"

app = FastAPI()
runt_client = RuntAPIClient()

# Inicializar la base de datos al arrancar
init_db()

# Agregar al inicio del archivo después de crear la app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "API Consumer Running"}

@app.get("/process")
@app.post("/process")
async def process_file(request: Request):
    try:
        if not os.path.exists(EVENTOS_FILE):
            print(f"[{datetime.now()}] Error: No se encontró el archivo de eventos consolidados")
            return {"error": "No se encontró el archivo de eventos consolidados"}
            
        print(f"[{datetime.now()}] Leyendo archivo de eventos: {EVENTOS_FILE}")
        with open(EVENTOS_FILE, "r", encoding="utf-8") as f:
            json_data = json.load(f)
            print(f"[{datetime.now()}] Eventos leídos: {len(json_data)}")
            
        processed_data = process_json(json_data)
        print(f"[{datetime.now()}] Eventos procesados: {len(processed_data['processed'])}")
        
        # Determinar si es una solicitud automática o manual
        is_automatic = request.method == "POST"
        source = "automático" if is_automatic else "manual"
        print(f"[{datetime.now()}] Procesamiento {source} completado")
        
        # Verificar si hay nuevos eventos procesados
        new_events = len(processed_data['processed'])
        if new_events > 0:
            print(f"[{datetime.now()}] Se procesaron {new_events} nuevos eventos")
        else:
            print(f"[{datetime.now()}] No hay nuevos eventos para procesar")
        
        return {
            "message": f"Se procesaron {new_events} registros ({source})",
            "data": processed_data,
            "source": source
        }
    except Exception as e:
        print(f"[{datetime.now()}] Error en el procesamiento: {str(e)}")
        return {"error": str(e)}

@app.post("/attributes/")
def add_attribute(name: str, type: str, db: Session = Depends(get_db)):
    return create_attribute(db, name, type)

@app.get("/attributes/")
def list_attributes(db: Session = Depends(get_db)):
    return get_attributes(db)

@app.get("/generate-pdf")
def generate_pdf():
    try:
        if not os.path.exists(EVENTOS_FILE):
            return {"error": "No se encontró el archivo de eventos consolidados"}
            
        with open(EVENTOS_FILE, "r", encoding="utf-8") as f:
            json_data = json.load(f)
                
        # Procesar todos los registros
        processed_data = process_json(json_data)
        
        # Inicializar generador de templates
        template_gen = TemplateGenerator()
        
        # Generar PDFs para todos los registros
        generated_pdfs = template_gen.generate_pdfs_for_records(processed_data["processed"])
        
        if generated_pdfs:
            return {
                "message": f"Se generaron {len(generated_pdfs)} PDFs exitosamente",
                "pdfs": generated_pdfs
            }
        else:
            return {"error": "No se generaron PDFs"}
                
    except Exception as e:
        return {"error": f"Error general: {str(e)}"}

@app.get("/download-pdf/{filename}")
async def download_pdf(filename: str):
    pdf_path = os.path.join("output/pdfs", filename)
    if os.path.exists(pdf_path):
        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=filename,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    return {"error": "PDF no encontrado"}

@app.get("/runt/generate-key")
def generate_runt_key():
    return runt_client.generate_key()

@app.get("/runt/test-connection")
def test_runt_connection():
    return {
        "base_url": os.getenv("API_URL"),
        "headers": {
            "X-Runt-Id-Usuario": os.getenv("RUNT_USUARIO"),
            "X-Runt-Firma": os.getenv("RUNT_FIRMA"),
            "X-Forwarded-For": os.getenv("FORWARDED_IP")
        }
    }

@app.get("/global-vars")
def get_global_vars():
    return GlobalVars.get_all()

@app.get("/global-vars/{var_name}")
def get_global_var(var_name: str):
    return {"name": var_name, "value": GlobalVars.get_value(var_name)}

@app.get("/download-all-pdfs")
async def download_all_pdfs(filenames: str):
    try:
        # Convertir la cadena de filenames a lista
        pdf_files = filenames.split(",")
        
        # Crear un archivo ZIP temporal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"reportes_{timestamp}.zip"
        zip_path = os.path.join("output/pdfs", zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename in pdf_files:
                pdf_path = os.path.join("output/pdfs", filename)
                if os.path.exists(pdf_path):
                    # Agregar archivo al ZIP
                    zipf.write(pdf_path, filename)
        
        # Devolver el archivo ZIP
        return FileResponse(
            path=zip_path,
            media_type='application/zip',
            filename=zip_filename,
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
    except Exception as e:
        return {"error": f"Error al crear ZIP: {str(e)}"}

@app.get("/get-plate")
async def get_plate():
    try:
        if not os.path.exists(EVENTOS_FILE):
            return {"error": "No se encontró el archivo de eventos consolidados"}
            
        with open(EVENTOS_FILE, 'r', encoding='utf-8') as file:
            eventos = json.load(file)
            
            if eventos and len(eventos) > 0:
                # Obtener la placa del último evento
                ultimo_evento = eventos[-1]
                if 'plate' in ultimo_evento:
                    plate = ultimo_evento['plate']
                    print(f"Placa encontrada: {plate}")
                    return {"success": True, "plate": plate}
            
            return {
                "success": False,
                "error": "No se encontraron eventos con placas",
                "debug": {
                    "total_eventos": len(eventos) if eventos else 0
                }
            }
            
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"Error al leer la placa: {str(e)}",
            "traceback": traceback.format_exc(),
            "file_path": EVENTOS_FILE
        }
