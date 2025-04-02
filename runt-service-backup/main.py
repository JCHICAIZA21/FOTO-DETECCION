from fastapi import FastAPI, Depends, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, init_db
from services.runt_service import RuntService
import schemas
from typing import List, Dict, Any
import json
import requests
import os
from pydantic import BaseModel
import httpx
import crud
from services.pdf_service import PdfService

app = FastAPI()

# Agregar CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar la base de datos al arrancar
init_db()

runt_service = RuntService()
pdf_service = PdfService()

API_CONSUMER_URL = os.getenv('API_CONSUMER_URL', 'http://api-consumer:8000')

class PlateRequest(BaseModel):
    plate: str

class PdfGenerationRequest(BaseModel):
    template_id: int
    plate: str
    output_filename: str

class TemplateCreate(BaseModel):
    name: str
    content: str
    variables: Dict[str, Any]

class TemplateUpdate(BaseModel):
    content: str = None
    variables: Dict[str, Any] = None

@app.get("/")
def read_root():
    return {"message": "RUNT API Service Running"}

@app.get("/generate-key")
def generate_key(db: Session = Depends(get_db)):
    try:
        # Intentar obtener la placa del servicio api-consumer
        try:
            response = requests.get("http://api-consumer:8000/process")
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "processed" in data["data"]:
                    # Obtener la placa del primer registro procesado
                    processed_records = data["data"]["processed"]
                    if processed_records and len(processed_records) > 0:
                        plate = processed_records[0].get("plate")
                        if plate:
                            print(f"Placa obtenida: {plate}")
                            return runt_service.process_runt_sequence(db, plate)
                
            return {
                "success": False,
                "error": "No se pudo obtener la placa del archivo procesado"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error al conectar con el servicio api-consumer: {str(e)}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error al procesar la solicitud: {str(e)}"
        }

@app.get("/test-connection")
def test_connection(db: Session = Depends(get_db)):
    return runt_service.test_connection(db)

@app.get("/endpoints", response_model=List[schemas.ApiEndpoint])
def get_endpoints(db: Session = Depends(get_db)):
    return runt_service.get_all_endpoints(db)

@app.post("/endpoints", response_model=schemas.ApiEndpoint)
def create_endpoint(
    endpoint: schemas.ApiEndpointCreate, 
    db: Session = Depends(get_db)
):
    return runt_service.create_endpoint(db, endpoint)

@app.get("/variables")
async def get_variables(db: Session = Depends(get_db)):
    try:
        service = RuntService()
        variables = service.get_all_variables(db)
        return variables
    except Exception as e:
        return {"error": str(e)}

@app.post("/variables", response_model=schemas.GlobalVariable)
def create_variable(variable: schemas.GlobalVariableCreate, db: Session = Depends(get_db)):
    return runt_service.create_variable(db, variable)

@app.put("/variables/{name}", response_model=schemas.GlobalVariable)
def update_variable(name: str, variable: schemas.GlobalVariableUpdate, db: Session = Depends(get_db)):
    updated_var = runt_service.update_variable(db, name, variable)
    if not updated_var:
        raise HTTPException(status_code=404, detail="Variable no encontrada")
    return updated_var

@app.get("/get-plate")
async def get_plate():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://api-consumer:8000/get-plate")
            response.raise_for_status()
            data = response.json()
            
            print(f"Respuesta del api-consumer: {data}")
            
            # Manejar tanto 'plate' como 'plates'
            if data.get("success"):
                if "plates" in data:
                    return {"success": True, "plates": data["plates"]}
                elif "plate" in data:
                    return {"success": True, "plates": [data["plate"]]}
            
            error_msg = data.get("error", "No se encontraron placas en el archivo")
            debug_info = data.get("debug", {})
            print(f"Error: {error_msg}")
            print(f"Debug info: {debug_info}")
            return {
                "success": False,
                "error": error_msg,
                "debug": debug_info
            }
                
    except Exception as e:
        print(f"Error en get_plate: {str(e)}")
        return {
            "success": False,
            "error": f"Error al obtener las placas: {str(e)}",
            "debug": {
                "exception_type": type(e).__name__,
                "exception_details": str(e)
            }
        }

@app.post("/process-runt")
async def process_runt(db: Session = Depends(get_db)):
    try:
        # Obtener las placas
        async with httpx.AsyncClient() as client:
            response = await client.get("http://api-consumer:8000/get-plate")
            response.raise_for_status()
            data = response.json()
            
            print(f"Respuesta del api-consumer en process-runt: {data}")
            
            plates = []
            if data.get("success"):
                if "plates" in data:
                    plates = data["plates"]
                elif "plate" in data:
                    plates = [data["plate"]]
            
            if not plates:
                return {
                    "success": False,
                    "error": "No se encontraron placas para procesar",
                    "debug": data.get("debug", {})
                }
            
            print(f"Procesando placas: {plates}")
            
            # Procesar las placas
            runt_service = RuntService()
            processed_vehicles = []
            
            for plate in plates:
                result = runt_service.process_runt_sequence(db, [plate])
                if result.get("success"):
                    # Almacenar la información en la base de datos
                    for vehicle_data in result["data"]["vehicles"]:
                        if vehicle_data.get("success"):
                            try:
                                stored_vehicle = crud.store_vehicle_data(
                                    db, 
                                    vehicle_data["data"]
                                )
                                processed_vehicles.append({
                                    "plate": plate,
                                    "success": True,
                                    "stored": True,
                                    "data": vehicle_data["data"]
                                })
                            except Exception as e:
                                processed_vehicles.append({
                                    "plate": plate,
                                    "success": True,
                                    "stored": False,
                                    "error": str(e),
                                    "data": vehicle_data["data"]
                                })
                        else:
                            processed_vehicles.append({
                                "plate": plate,
                                "success": False,
                                "error": vehicle_data.get("error", "Error desconocido")
                            })
                else:
                    processed_vehicles.append({
                        "plate": plate,
                        "success": False,
                        "error": result.get("error", "Error en la consulta RUNT")
                    })
            
            return {
                "success": True,
                "processed_vehicles": processed_vehicles
            }
            
    except Exception as e:
        print(f"Error en process_runt: {str(e)}")
        return {
            "success": False,
            "error": f"Error en el proceso: {str(e)}"
        }

@app.post("/generate-pdfs-bulk")
async def generate_pdfs_bulk(
    request: List[PdfGenerationRequest],
    db: Session = Depends(get_db)
):
    """Genera PDFs para múltiples placas"""
    results = []
    for req in request:
        try:
            output_path = pdf_service.generate_pdf(
                db,
                req.template_id,
                req.plate,
                req.output_filename
            )
            results.append({
                "plate": req.plate,
                "success": True,
                "pdf_path": output_path,
                "filename": os.path.basename(output_path)
            })
        except Exception as e:
            results.append({
                "plate": req.plate,
                "success": False,
                "error": str(e)
            })
    
    return {
        "success": True,
        "results": results
    }

@app.get("/templates")
def get_templates(db: Session = Depends(get_db)):
    """Obtiene todas las plantillas disponibles"""
    return pdf_service.get_all_templates(db)

@app.get("/templates/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Obtiene una plantilla específica"""
    template = pdf_service.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return template

@app.post("/templates")
def create_template(
    template: TemplateCreate,
    db: Session = Depends(get_db)
):
    """Crea una nueva plantilla"""
    return pdf_service.create_template(
        db,
        template.name,
        template.content,
        template.variables
    )

@app.put("/templates/{template_id}")
def update_template(
    template_id: int,
    template: TemplateUpdate,
    db: Session = Depends(get_db)
):
    """Actualiza una plantilla existente"""
    updated = pdf_service.update_template(
        db,
        template_id,
        template.content,
        template.variables
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return updated

@app.get("/database-fields")
def get_database_fields():
    """Obtiene los campos disponibles de la base de datos"""
    return pdf_service.get_database_fields() 