from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from sqlalchemy.orm import Session
from database import get_db, init_db
from services.runt_service import RuntService
import schemas
from typing import List, Dict, Any, Optional
import json
import requests
import os
from pydantic import BaseModel
import httpx
import crud
from services.pdf_service import PdfService
import logging
from fastapi.responses import FileResponse, Response, JSONResponse
from datetime import datetime
from models import GeneratedPdf, PdfTemplate, VehicleInfo
import asyncio
import traceback

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Variables globales para los servicios
runt_service = None
pdf_service = None

@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Inicializando base de datos...")
        init_db()
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error(f"Error inicializando la base de datos: {str(e)}")
        raise

# Agregar CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_CONSUMER_URL = os.getenv('API_CONSUMER_URL', 'http://api-consumer:8000')

logger = logging.getLogger(__name__)

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
        # Inicializar el servicio con la sesión de base de datos
        service = RuntService(db)
        
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
                            return service.process_runt_sequence(db, plate)
                
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
    service = RuntService(db)
    return service.test_connection(db)

@app.get("/endpoints", response_model=List[schemas.ApiEndpoint])
def get_endpoints(db: Session = Depends(get_db)):
    service = RuntService(db)
    return service.get_all_endpoints(db)

@app.post("/endpoints", response_model=schemas.ApiEndpoint)
def create_endpoint(
    endpoint: schemas.ApiEndpointCreate, 
    db: Session = Depends(get_db)
):
    service = RuntService(db)
    return service.create_endpoint(db, endpoint)

@app.get("/variables")
async def get_variables(db: Session = Depends(get_db)):
    try:
        service = RuntService(db)
        variables = service.get_all_variables(db)
        return variables
    except Exception as e:
        return {"error": str(e)}

@app.post("/variables", response_model=schemas.GlobalVariable)
def create_variable(variable: schemas.GlobalVariableCreate, db: Session = Depends(get_db)):
    service = RuntService(db)
    return service.create_variable(db, variable)

@app.put("/variables/{name}", response_model=schemas.GlobalVariable)
def update_variable(name: str, variable: schemas.GlobalVariableUpdate, db: Session = Depends(get_db)):
    service = RuntService(db)
    updated_var = service.update_variable(db, name, variable)
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
async def process_runt(request: Request, db: Session = Depends(get_db)):
    """Procesa placas a través del servicio RUNT."""
    try:
        # Inicializar el servicio con la sesión de base de datos
        service = RuntService(db)
        
        # Obtener datos del request
        data = await request.json()
        plates = data.get("plates", [])
        
        # Convertir placa única a lista
        if isinstance(plates, str):
            plates = [plates]
        
        # Validar que haya placas para procesar
        if not plates:
            # Intentar obtener placas del API Consumer
            try:
                consumer_response = requests.get("http://api-consumer:8000/get-plate")
                if consumer_response.status_code == 200:
                    plates = consumer_response.json().get("plates", [])
            except Exception as e:
                logger.error(f"Error al obtener placas del API Consumer: {str(e)}")
                return {
                    "success": False,
                    "error": "No se pudieron obtener placas del API Consumer"
                }
        
        if not plates:
            return {
                "success": False,
                "error": "No se proporcionaron placas para procesar"
            }
        
        # Procesar las placas
        result = service.process_runt_sequence(db, plates)
        return result
        
    except Exception as e:
        logger.error(f"Error en process_runt: {str(e)}")
        return {
            "success": False,
            "error": f"Error al procesar las placas: {str(e)}"
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

@app.get("/template-variables")
async def get_template_variables():
    """Obtiene todas las variables disponibles para usar en las plantillas."""
    try:
        variables = {
            "Vehículo": [
                "plate",
                "marca",
                "linea",
                "modelo",
                "color",
                "tipo_servicio",
                "clase_vehiculo",
                "no_licencia",
                "estado",
                "cilindraje",
                "tipo_carroceria",
                "no_motor",
                "no_chasis",
                "no_vin"
            ],
            "Propietario": [
                "nombre",
                "tipo_documento",
                "numero_documento",
                "direccion",
                "ciudad",
                "telefono"
            ],
            "SOAT": [
                "numero",
                "vigencia",
                "estado",
                "entidad"
            ],
            "RTM": [
                "numero",
                "vigencia",
                "estado",
                "cda"
            ],
            "Evento": [
                "fecha",
                "hora",
                "ubicacion",
                "velocidad",
                "tipo_infraccion",
                "evidencia_url"
            ],
            "Sistema": [
                "fecha_generacion",
                "hora_generacion",
                "usuario_generador"
            ]
        }
        return variables
    except Exception as e:
        logger.error(f"Error obteniendo variables de plantilla: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo variables: {str(e)}"
        )

@app.get("/templates")
async def get_templates(db: Session = Depends(get_db)):
    """Obtiene todas las plantillas disponibles."""
    try:
        templates = crud.get_all_templates(db)
        return templates
    except Exception as e:
        logger.error(f"Error obteniendo plantillas: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo plantillas: {str(e)}"
        )

@app.get("/templates/{template_id}")
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """Obtiene una plantilla específica por su ID."""
    try:
        template = crud.get_template_by_id(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        return template
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error obteniendo plantilla: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo plantilla: {str(e)}"
        )

@app.post("/templates")
async def create_template(template: dict, db: Session = Depends(get_db)):
    """Crea una nueva plantilla."""
    try:
        # Verificar si ya existe una plantilla con el mismo nombre
        existing = crud.get_template_by_name(db, template["name"])
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe una plantilla con el nombre '{template['name']}'"
            )
        
        new_template = crud.create_template(
            db,
            name=template["name"],
            content=template["content"]
        )
        return new_template
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error creando plantilla: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creando plantilla: {str(e)}"
        )

@app.put("/templates/{template_id}")
async def update_template(template_id: int, template: dict, db: Session = Depends(get_db)):
    """Actualiza una plantilla existente."""
    try:
        # Verificar si existe una plantilla con el mismo nombre pero diferente ID
        existing = crud.get_template_by_name(db, template["name"])
        if existing and existing.id != template_id:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe una plantilla con el nombre '{template['name']}'"
            )
        
        updated_template = crud.update_template(
            db,
            template_id=template_id,
            name=template["name"],
            content=template["content"]
        )
        if not updated_template:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        return updated_template
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error actualizando plantilla: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando plantilla: {str(e)}"
        )

@app.delete("/templates/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Elimina una plantilla existente."""
    try:
        success = crud.delete_template(db, template_id)
        if not success:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        return {"message": "Plantilla eliminada exitosamente"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error eliminando plantilla: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error eliminando plantilla: {str(e)}"
        )

@app.get("/database-fields")
def get_database_fields():
    """Obtiene los campos disponibles de la base de datos"""
    return pdf_service.get_database_fields()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

def get_template_by_id(template_id: int, db: Session = Depends(get_db)) -> Optional[dict]:
    """Obtiene una plantilla por su ID"""
    try:
        template = pdf_service.get_template_by_id(db, template_id)
        if not template:
            return None
        return {
            "id": template.id,
            "name": template.name,
            "content": template.content,
            "variables": template.variables if hasattr(template, 'variables') else {}
        }
    except Exception as e:
        logger.error(f"Error obteniendo plantilla: {str(e)}")
        return None

@app.post("/generate-pdf")
async def generate_pdf(request: Request, db: Session = Depends(get_db)):
    """Genera un PDF basado en una plantilla y datos de una placa."""
    try:
        data = await request.json()
        template_id = data.get("template_id")
        plate = data.get("plate")
        
        logger.info(f"Iniciando generación de PDF para placa {plate} con template {template_id}")
        
        if not template_id or not plate:
            logger.error("Faltan parámetros requeridos")
            raise HTTPException(
                status_code=400, 
                detail="Se requiere template_id y plate"
            )
            
        # Obtener la plantilla
        logger.info(f"Obteniendo plantilla {template_id}")
        template = get_template_by_id(template_id, db)
        if not template:
            logger.error(f"No se encontró la plantilla con ID {template_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Plantilla {template_id} no encontrada"
            )
            
        # Obtener datos del vehículo y eventos
        logger.info(f"Obteniendo datos del vehículo para placa {plate}")
        vehicle_data = crud.get_vehicle_data(db, plate)
        if not vehicle_data or not isinstance(vehicle_data, dict):
            logger.error(f"No se encontraron datos del vehículo para la placa {plate}")
            raise HTTPException(
                status_code=404, 
                detail=f"No se encontraron datos para la placa {plate}"
            )
            
        # Combinar todos los datos
        template_data = {
            "Vehículo": vehicle_data.get("vehicle", {}),
            "Propietario": vehicle_data.get("current_owner", {}),
            "SOAT": vehicle_data.get("soat", {}),
            "RTM": vehicle_data.get("rtm", {}),
            "Evento": vehicle_data.get("latest_event", {}),
            "Sistema": {
                "fecha_generacion": datetime.now().strftime("%Y-%m-%d"),
                "hora_generacion": datetime.now().strftime("%H:%M:%S"),
                "usuario_generador": "Sistema"
            },
            "image1_base64": data.get("image1_base64", ""),
            "image2_base64": data.get("image2_base64", "")
        }
        
        logger.info("Generando PDF con los datos recopilados")
        # Generar el PDF usando el servicio
        try:
            pdf_content = pdf_service.generate_pdf_from_template(
                template["content"],
                template_data
            )
            logger.info("PDF generado exitosamente")
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="reporte_{plate}.pdf"'
                }
            )
        except Exception as e:
            logger.error(f"Error generando PDF: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, 
                detail=f"Error generando PDF: {str(e)}"
            )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error en generate_pdf: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=str(e)
        )

def get_vehicle_data(plate: str, db: Session) -> dict:
    """Obtiene los datos del vehículo desde la base de datos."""
    try:
        # Obtener datos del vehículo usando el servicio PDF
        vehicle_data = pdf_service.get_vehicle_data(db, plate)
        if not vehicle_data:
            logger.warning(f"No se encontraron datos para la placa {plate}")
            return {}
            
        # Extraer la información del vehículo
        vehicle_info = vehicle_data.get("vehicle", {})
        current_owner = vehicle_data.get("current_owner", {})
        
        # Formatear los datos
        return {
            "plate": vehicle_info.get("plate", ""),
            "marca": vehicle_info.get("marca", ""),
            "linea": vehicle_info.get("linea", ""),
            "modelo": vehicle_info.get("modelo", ""),
            "color": vehicle_info.get("color", ""),
            "tipo_servicio": vehicle_info.get("tipo_servicio", ""),
            "clase_vehiculo": vehicle_info.get("clase", ""),
            "no_licencia": vehicle_info.get("licencia", ""),
            "estado": vehicle_info.get("estado", ""),
            "cilindraje": vehicle_info.get("cilindraje", ""),
            "tipo_carroceria": vehicle_info.get("tipo_carroceria", ""),
            "no_motor": vehicle_info.get("no_motor", ""),
            "no_chasis": vehicle_info.get("no_chasis", ""),
            "no_vin": vehicle_info.get("no_vin", ""),
            "propietario": {
                "nombre": current_owner.get("nombre_completo", ""),
                "tipo_documento": current_owner.get("tipo_documento", ""),
                "numero_documento": current_owner.get("numero_documento", ""),
                "direccion": current_owner.get("direcciones", [{}])[0].get("direccion", ""),
                "ciudad": current_owner.get("direcciones", [{}])[0].get("ciudad", ""),
                "telefono": current_owner.get("direcciones", [{}])[0].get("telefono", "")
            } if current_owner else {}
        }
    except Exception as e:
        logger.error(f"Error obteniendo datos del vehículo: {str(e)}")
        logger.error(traceback.format_exc())
        return {}

def get_events_data(plate: str, db: Session) -> dict:
    """Obtiene los datos de eventos desde la base de datos."""
    try:
        # Obtener datos del vehículo usando el servicio PDF
        vehicle_data = pdf_service.get_vehicle_data(db, plate)
        if not vehicle_data:
            logger.warning(f"No se encontraron datos para la placa {plate}")
            return {}
            
        # Extraer la información de SOAT y RTM
        soat = vehicle_data.get("soat", {})
        rtm = vehicle_data.get("rtm", {})
        policies = vehicle_data.get("policies", [])
        
        # Formatear los datos
        return {
            "soat": {
                "numero": soat.get("poliza", ""),
                "vigencia": soat.get("fecha_vencimiento", ""),
                "estado": soat.get("estado", ""),
                "entidad": soat.get("entidad", "")
            } if soat else {},
            "rtm": {
                "numero": rtm.get("numero", ""),
                "vigencia": rtm.get("fecha_vigencia", ""),
                "estado": rtm.get("vigente", ""),
                "cda": rtm.get("cda", "")
            } if rtm else {},
            "polizas": [{
                "numero": policy.get("numero", ""),
                "fecha_expedicion": policy.get("fecha_expedicion", ""),
                "fecha_vigencia": policy.get("fecha_vigencia", ""),
                "aseguradora": policy.get("aseguradora", ""),
                "estado": policy.get("estado", "")
            } for policy in policies]
        }
    except Exception as e:
        logger.error(f"Error obteniendo datos de eventos: {str(e)}")
        logger.error(traceback.format_exc())
        return {}

@app.post("/preview-pdf")
async def preview_pdf(request: dict):
    try:
        content = request.get("content")
        if not content:
            raise HTTPException(status_code=400, detail="Se requiere el contenido HTML")

        # Datos de ejemplo para la previsualización
        sample_data = {
            "vehicle": {
                "plate": "ABC123",
                "marca": "EJEMPLO",
                "linea": "MODELO EJEMPLO",
                "modelo": "2024",
                "color": "NEGRO",
                "tipo_servicio": "PARTICULAR",
                "clase_vehiculo": "AUTOMÓVIL",
                "no_licencia": "12345678",
                "estado": "ACTIVO",
                "cilindraje": "2000",
                "tipo_carroceria": "SEDAN",
                "no_motor": "MOT123",
                "no_chasis": "CHA123",
                "no_vin": "VIN123"
            },
            "owner": {
                "nombre": "JUAN EJEMPLO",
                "tipo_documento": "CC",
                "numero_documento": "123456789",
                "direccion": "CALLE EJEMPLO 123",
                "ciudad": "CIUDAD EJEMPLO",
                "telefono": "3001234567"
            },
            "soat": {
                "numero": "SOAT123",
                "vigencia": "31/12/2024",
                "estado": "VIGENTE",
                "entidad": "ASEGURADORA EJEMPLO"
            },
            "rtm": {
                "numero": "RTM123",
                "vigencia": "31/12/2024",
                "estado": "VIGENTE",
                "cda": "CDA EJEMPLO"
            },
            "policies": [
                {
                    "numero": "POL123",
                    "fecha_expedicion": "01/01/2024",
                    "fecha_vigencia": "31/12/2024",
                    "aseguradora": "ASEGURADORA EJEMPLO",
                    "estado": "VIGENTE"
                }
            ]
        }

        # Generar el PDF
        try:
            pdf_service = PdfService()
            pdf_content = pdf_service.generate_preview_pdf(content, sample_data)
            return Response(content=pdf_content, media_type="application/pdf")
        except Exception as e:
            logger.error(f"Error generating preview PDF: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        logger.error(f"Error en preview_pdf: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 