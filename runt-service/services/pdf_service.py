from jinja2 import Template
from weasyprint import HTML
import os
from datetime import datetime
from sqlalchemy.orm import Session
import crud
from typing import Dict, Any, List, Optional
import json
from models import PdfTemplate, VehicleInfo
from fastapi import HTTPException
import logging
import base64
from sqlalchemy.orm import Session
from models import GlobalVariable
from sqlalchemy.orm import Session
from database import get_db
import traceback

logger = logging.getLogger(__name__)

class PdfService:
    def __init__(self):
        self.output_dir = "output/pdfs"
        os.makedirs(self.output_dir, exist_ok=True)

    def get_database_fields(self):
        """Obtiene los campos disponibles de la base de datos"""
        return {
            "vehicle_info": [
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
            "propietario": [
                "nombre",
                "tipo_documento",
                "numero_documento",
                "direccion",
                "ciudad",
                "telefono"
            ],
            "soat": [
                "numero",
                "vigencia",
                "estado",
                "entidad"
            ],
            "rtm": [
                "numero",
                "vigencia",
                "estado",
                "cda"
            ],
            "polizas": [
                "numero",
                "fecha_expedicion",
                "fecha_vigencia",
                "aseguradora",
                "estado"
            ]
        }

    def create_template(self, db: Session, name: str, content: str, variables: dict = None):
        try:
            template = PdfTemplate(
                name=name,
                content=content,
                variables=variables or {}
            )
            db.add(template)
            db.commit()
            db.refresh(template)
            return template
        except Exception as e:
            logger.error(f"Error creando template: {str(e)}")
            db.rollback()
            raise

    def update_template(
        self, 
        db: Session, 
        template_id: int, 
        name: str = None, 
        content: str = None, 
        variables: dict = None
    ) -> PdfTemplate:
        """Actualiza una plantilla existente"""
        template = db.query(PdfTemplate).filter(
            PdfTemplate.id == template_id
        ).first()
        
        if template:
            if name:
                template.name = name
            if content:
                template.content = content
            if variables is not None:
                template.variables = variables
            template.updated_at = datetime.now()
            db.commit()
            db.refresh(template)
        
        return template

    def get_template(self, db: Session, template_id: int) -> PdfTemplate:
        """Obtiene una plantilla por su ID"""
        return db.query(PdfTemplate).filter(
            PdfTemplate.id == template_id
        ).first()

    def get_all_templates(self, db: Session):
        return db.query(PdfTemplate).all()

    def get_template_by_id(self, db: Session, template_id: int):
        return db.query(PdfTemplate).filter(PdfTemplate.id == template_id).first()

    def get_vehicle_data(self, db: Session, plate: str) -> Dict[str, Any]:
        """Obtiene todos los datos del vehículo y los formatea para la plantilla"""
        try:
            if not db:
                logger.error("No se proporcionó una sesión de base de datos")
                return None

            logger.info(f"Buscando datos para la placa: {plate}")
            vehicle_data = crud.get_vehicle_info(db, plate)
            if not vehicle_data:
                logger.warning(f"No se encontraron datos para la placa {plate}")
                return None

            logger.info(f"Datos encontrados para la placa {plate}, formateando información...")
            try:
                # Formatear los datos para la plantilla
                formatted_data = {
                    "vehicle": self._format_vehicle_info(vehicle_data["vehicle_info"]) if vehicle_data.get("vehicle_info") else {},
                    "owners": [self._format_owner(owner) for owner in vehicle_data.get("owners", [])],
                    "current_owner": self._get_current_owner(vehicle_data.get("owners", [])),
                    "soat": self._get_latest_soat(vehicle_data.get("soats", [])),
                    "rtm": self._get_latest_rtm(vehicle_data.get("rtms", [])),
                    "policies": self._format_policies(vehicle_data.get("civil_policies", []))
                }
                logger.info("Datos formateados correctamente")
                return formatted_data
            except Exception as format_error:
                logger.error(f"Error formateando datos: {str(format_error)}")
                logger.error(traceback.format_exc())
                return None
        except Exception as e:
            logger.error(f"Error obteniendo datos del vehículo: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def _format_vehicle_info(self, vehicle) -> Dict[str, Any]:
        """Formatea la información básica del vehículo"""
        return {
            "plate": vehicle.plate,
            "registro": vehicle.no_registro,
            "licencia": vehicle.no_licencia_transito,
            "fecha_expedicion": vehicle.fecha_expedicion_lic_transito.strftime("%d/%m/%Y"),
            "estado": vehicle.estado_vehiculo,
            "tipo_servicio": vehicle.tipo_servicio,
            "clase": vehicle.clase_vehiculo,
            "marca": vehicle.marca,
            "linea": vehicle.linea,
            "modelo": vehicle.modelo,
            "color": vehicle.color,
            "cilindraje": vehicle.cilindraje,
            "tipo_carroceria": vehicle.tipo_carroceria,
            "no_motor": vehicle.no_motor,
            "no_chasis": vehicle.no_chasis,
            "no_vin": vehicle.no_vin,
            # ... agregar más campos según necesidad
        }

    def _format_owner(self, owner) -> Dict[str, Any]:
        """Formatea la información del propietario"""
        return {
            "nombre_completo": owner.nombre_completo,
            "tipo_documento": owner.tipo_documento,
            "numero_documento": owner.numero_documento,
            "direcciones": [
                {
                    "direccion": addr.direccion,
                    "ciudad": addr.ciudad,
                    "departamento": addr.departamento,
                    "telefono": addr.telefono,
                    "celular": addr.celular
                } for addr in owner.addresses
            ]
        }

    def _get_current_owner(self, owners) -> Dict[str, Any]:
        """Obtiene el propietario actual"""
        current_owner = next((owner for owner in owners if owner.is_current), None)
        return self._format_owner(current_owner) if current_owner else None

    def _get_latest_soat(self, soats) -> Dict[str, Any]:
        """Obtiene el SOAT más reciente"""
        if not soats:
            return None
        latest = max(soats, key=lambda s: s.fecha_expedicion)
        return {
            "poliza": latest.no_poliza,
            "fecha_expedicion": latest.fecha_expedicion.strftime("%d/%m/%Y"),
            "fecha_vencimiento": latest.fecha_vencimiento.strftime("%d/%m/%Y"),
            "estado": latest.estado,
            "entidad": latest.entidad_expide
        }

    def _get_latest_rtm(self, rtms) -> Dict[str, Any]:
        """Obtiene la revisión técnico-mecánica más reciente"""
        if not rtms:
            return None
        latest = max(rtms, key=lambda r: r.fecha_expedicion)
        return {
            "numero": latest.nro_rtm,
            "fecha_expedicion": latest.fecha_expedicion.strftime("%d/%m/%Y"),
            "fecha_vigencia": latest.fecha_vigente.strftime("%d/%m/%Y"),
            "cda": latest.cda_expide,
            "vigente": latest.vigente
        }

    def _extract_base64_images(self, vehicle_data: dict) -> tuple:
        """Extrae y convierte imágenes a base64"""
        try:
            image1_base64 = None
            image2_base64 = None
            
            # Si hay imágenes en el directorio output/images
            image_dir = "output/images"
            if os.path.exists(image_dir):
                plate = vehicle_data["vehicle_info"].plate
                images = [f for f in os.listdir(image_dir) if f.startswith(plate) and f.endswith(('.png', '.jpg', '.jpeg'))]
                
                for i, img_file in enumerate(images[:2]):  # Tomar solo las primeras 2 imágenes
                    try:
                        with open(os.path.join(image_dir, img_file), "rb") as f:
                            img_data = base64.b64encode(f.read()).decode('utf-8')
                            if i == 0:
                                image1_base64 = f"data:image/png;base64,{img_data}"
                            else:
                                image2_base64 = f"data:image/png;base64,{img_data}"
                    except Exception as e:
                        logger.error(f"Error procesando imagen {img_file}: {str(e)}")
                    
            return image1_base64, image2_base64
        except Exception as e:
            logger.error(f"Error extrayendo imágenes: {str(e)}")
            return None, None

    def generate_pdf(self, template_content, data):
        try:
            # Obtener las variables del template y los datos del vehículo
            vehicle_info = data.get("vehicle_info", {})
            template_variables = data.get("template_variables", {})
            
            # Combinar las variables con los datos del vehículo
            context = {
                **template_variables,
                "plate": vehicle_info.get("plate", ""),
                "marca": vehicle_info.get("marca", ""),
                "linea": vehicle_info.get("linea", ""),
                "modelo": vehicle_info.get("modelo", ""),
                "color": vehicle_info.get("color", ""),
                "tipo_servicio": vehicle_info.get("tipo_servicio", ""),
                "clase_vehiculo": vehicle_info.get("clase_vehiculo", ""),
                "no_licencia": vehicle_info.get("no_licencia_transito", ""),
                "estado": vehicle_info.get("estado_vehiculo", ""),
                "cilindraje": vehicle_info.get("cilindraje", ""),
                "tipo_carroceria": vehicle_info.get("tipo_carroceria", ""),
                "no_motor": vehicle_info.get("no_motor", ""),
                "no_chasis": vehicle_info.get("no_chasis", ""),
                "no_vin": vehicle_info.get("no_vin", ""),
                "image1_base64": data.get("image1_base64", ""),
                "image2_base64": data.get("image2_base64", "")
            }
            
            # Crear el template con Jinja2
            template = Template(template_content)
            html_content = template.render(**context)
            
            # Agregar estilos CSS
            html_content = f"""
            <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; }}
                        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                        th {{ background-color: #f5f5f5; }}
                        img {{ max-width: 100%; height: auto; }}
                        .header {{ text-align: center; margin-bottom: 20px; }}
                        .footer {{ text-align: center; margin-top: 20px; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
            </html>
            """
            
            # Generar el PDF
            pdf = HTML(string=html_content).write_pdf()
            return pdf
            
        except Exception as e:
            logger.error(f"Error generando PDF: {str(e)}")
            raise Exception(f"Error generando PDF: {str(e)}")

    def _get_field_value(self, data: Dict, table: str, field: str) -> Any:
        """Obtiene el valor de un campo específico de los datos"""
        if table == "vehicle_info":
            return data["vehicle"].get(field)
        elif table == "current_owner":
            return data["current_owner"].get(field) if data["current_owner"] else None
        elif table == "soat":
            return data["soat"].get(field) if data["soat"] else None
        elif table == "rtm":
            return data["rtm"].get(field) if data["rtm"] else None
        return None 

    def generate_preview_pdf(self, template_content: str, sample_data: dict) -> bytes:
        """Genera un PDF de previsualización con datos de ejemplo"""
        try:
            # Preparar datos de ejemplo
            template_data = {
                "item": {
                    "plate": "ABC123",
                    "image1_base64": None,
                    "image2_base64": None,
                    "infraction_data": {
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
                        "no_vin": "VIN123",
                        "propietario": {
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
                        "polizas": [{
                            "numero": "POL123",
                            "fecha_expedicion": "01/01/2024",
                            "fecha_vigencia": "31/12/2024",
                            "aseguradora": "ASEGURADORA EJEMPLO",
                            "estado": "VIGENTE"
                        }]
                    }
                }
            }

            # Obtener variables parametrizadas de la base de datos
            db = next(get_db())
            variables = db.query(GlobalVariable).all()
            for var in variables:
                template_data[var.name] = var.value

            # Renderizar plantilla
            template = Template(template_content)
            html_content = template.render(**template_data)
            
            # Agregar estilos CSS
            html_content = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        margin: 20px; 
                        line-height: 1.6;
                    }}
                    table {{ 
                        width: 100%; 
                        border-collapse: collapse; 
                        margin: 10px 0; 
                    }}
                    th, td {{ 
                        border: 1px solid #ddd; 
                        padding: 8px; 
                        text-align: left; 
                    }}
                    th {{ 
                        background-color: #f5f5f5; 
                        width: 30%;
                    }}
                    h1, h2 {{ 
                        color: #333; 
                        margin-top: 20px;
                    }}
                    .header {{ 
                        text-align: center; 
                        margin-bottom: 30px; 
                        padding: 20px;
                        background-color: #f8f9fa;
                        border-radius: 5px;
                    }}
                    .section {{ 
                        margin: 20px 0; 
                        padding: 15px;
                        border: 1px solid #dee2e6;
                        border-radius: 5px;
                        background-color: white;
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                        margin: 10px 0;
                        border-radius: 5px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .image-container {{
                        text-align: center;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            # Generar PDF
            pdf = HTML(string=html_content).write_pdf()
            return pdf

        except Exception as e:
            logger.error(f"Error generating preview PDF: {str(e)}")
            raise 

    def generate_pdf_from_template(self, template_content: str, data: dict) -> bytes:
        """Genera un PDF a partir de una plantilla y datos"""
        try:
            logger.info("Iniciando generación de PDF...")
            if not template_content:
                logger.error("El contenido de la plantilla está vacío")
                raise ValueError("El contenido de la plantilla no puede estar vacío")

            logger.info("Creando template de Jinja2...")
            # Crear el template de Jinja2
            template = Template(template_content)
            
            logger.info("Renderizando HTML...")
            # Renderizar el HTML
            try:
                html_content = template.render(**data)
            except Exception as template_error:
                logger.error(f"Error renderizando template: {str(template_error)}")
                logger.error(f"Datos proporcionados: {json.dumps(data, default=str)}")
                logger.error(traceback.format_exc())
                raise ValueError(f"Error renderizando template: {str(template_error)}")
            
            logger.info("Agregando estilos CSS...")
            # Agregar estilos CSS
            html_content = f"""
            <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{ 
                            font-family: Arial, sans-serif; 
                            margin: 20px; 
                            line-height: 1.6;
                        }}
                        table {{ 
                            width: 100%; 
                            border-collapse: collapse; 
                            margin: 10px 0; 
                        }}
                        th, td {{ 
                            border: 1px solid #ddd; 
                            padding: 8px; 
                            text-align: left; 
                        }}
                        th {{ 
                            background-color: #f5f5f5; 
                            width: 30%;
                        }}
                        h1, h2 {{ 
                            color: #333; 
                            margin-top: 20px;
                        }}
                        .header {{ 
                            text-align: center; 
                            margin-bottom: 30px; 
                            padding: 20px;
                            background-color: #f8f9fa;
                            border-radius: 5px;
                        }}
                        .section {{ 
                            margin: 20px 0; 
                            padding: 15px;
                            border: 1px solid #dee2e6;
                            border-radius: 5px;
                            background-color: white;
                        }}
                        img {{
                            max-width: 100%;
                            height: auto;
                            margin: 10px 0;
                            border-radius: 5px;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        }}
                        .image-container {{
                            text-align: center;
                            margin: 20px 0;
                        }}
                    </style>
                </head>
                <body>
                    {html_content}
                </body>
            </html>
            """
            
            logger.info("Convirtiendo HTML a PDF...")
            # Convertir HTML a PDF
            try:
                pdf = HTML(string=html_content).write_pdf()
                logger.info("PDF generado exitosamente")
                return pdf
            except Exception as pdf_error:
                logger.error(f"Error generando PDF: {str(pdf_error)}")
                logger.error(traceback.format_exc())
                raise ValueError(f"Error generando PDF: {str(pdf_error)}")
            
        except Exception as e:
            logger.error(f"Error en generate_pdf_from_template: {str(e)}")
            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=500, 
                detail=f"Error generando PDF: {str(e)}"
            )

    def _format_policies(self, policies) -> List[Dict[str, Any]]:
        """Formatea la información de las pólizas"""
        if not policies:
            return []
        return [{
            "numero": policy.no_poliza,
            "fecha_expedicion": policy.fecha_expedicion.strftime("%d/%m/%Y"),
            "fecha_vigencia": policy.fecha_vigencia.strftime("%d/%m/%Y"),
            "aseguradora": policy.aseguradora,
            "estado": policy.estado
        } for policy in policies] 