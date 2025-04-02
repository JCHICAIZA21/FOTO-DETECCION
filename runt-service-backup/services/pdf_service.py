from jinja2 import Template
from weasyprint import HTML
import os
from datetime import datetime
from sqlalchemy.orm import Session
import crud
from typing import Dict, Any, List, Optional
import json
from models import PdfTemplate, VehicleInfo

class PdfService:
    def __init__(self):
        self.output_dir = "output/pdfs"
        os.makedirs(self.output_dir, exist_ok=True)

    def get_database_fields(self) -> Dict[str, List[str]]:
        """Retorna un diccionario con las tablas y sus campos disponibles"""
        return {
            "vehicle_info": [
                "plate", "no_registro", "no_licencia_transito", 
                "fecha_expedicion_lic_transito", "estado_vehiculo",
                "tipo_servicio", "clase_vehiculo", "marca", "linea",
                "modelo", "color", "no_serie", "no_motor", "no_chasis",
                "no_vin", "cilindraje", "tipo_carroceria", "fecha_matricula",
                "tiene_gravamenes", "organismo_transito", "prendas",
                "prendario", "clasificacion", "capacidad_carga",
                "peso_bruto_vehicular", "no_ejes"
            ],
            "vehicle_owner": [
                "tipo_documento", "numero_documento", "nombre_completo",
                "primer_nombre", "segundo_nombre", "primer_apellido",
                "segundo_apellido", "tipo_propiedad", "detalle_propiedad",
                "fecha_nacimiento"
            ],
            "vehicle_owner_address": [
                "direccion", "departamento", "ciudad", "telefono",
                "celular", "email"
            ],
            "vehicle_soat": [
                "no_poliza", "fecha_expedicion", "fecha_vigencia",
                "fecha_vencimiento", "nit_entidad", "entidad_expide",
                "estado"
            ],
            "vehicle_rtm": [
                "nro_rtm", "tipo_revision", "fecha_expedicion",
                "fecha_vigente", "cda_expide", "vigente"
            ]
        }

    def create_template(
        self, 
        db: Session, 
        name: str, 
        content: str, 
        variables: Dict[str, Any]
    ) -> PdfTemplate:
        """Crea una nueva plantilla"""
        template = PdfTemplate(
            name=name,
            template_content=content,
            variables=variables
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    def update_template(
        self, 
        db: Session, 
        template_id: int, 
        content: str = None, 
        variables: Dict[str, Any] = None
    ) -> PdfTemplate:
        """Actualiza una plantilla existente"""
        template = db.query(PdfTemplate).filter(
            PdfTemplate.id == template_id
        ).first()
        
        if template:
            if content is not None:
                template.template_content = content
            if variables is not None:
                template.variables = variables
            template.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(template)
        
        return template

    def get_template(self, db: Session, template_id: int) -> PdfTemplate:
        """Obtiene una plantilla por su ID"""
        return db.query(PdfTemplate).filter(
            PdfTemplate.id == template_id
        ).first()

    def get_all_templates(self, db: Session) -> List[PdfTemplate]:
        """Obtiene todas las plantillas"""
        return db.query(PdfTemplate).all()

    def get_vehicle_data(self, db: Session, plate: str) -> Dict[str, Any]:
        """Obtiene todos los datos del vehículo y los formatea para la plantilla"""
        vehicle_data = crud.get_vehicle_info(db, plate)
        if not vehicle_data:
            return None

        # Formatear los datos para la plantilla
        formatted_data = {
            "vehicle": self._format_vehicle_info(vehicle_data["vehicle_info"]),
            "owners": [self._format_owner(owner) for owner in vehicle_data["owners"]],
            "current_owner": self._get_current_owner(vehicle_data["owners"]),
            "soat": self._get_latest_soat(vehicle_data["soats"]),
            "rtm": self._get_latest_rtm(vehicle_data["rtms"]),
            "policies": self._format_policies(vehicle_data["civil_policies"])
        }
        return formatted_data

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

    def generate_pdf(
        self,
        db: Session,
        template_id: int,
        plate: str,
        output_filename: Optional[str] = None
    ) -> str:
        """Genera un PDF usando una plantilla y datos del vehículo"""
        try:
            # Obtener la plantilla
            template = crud.get_template(db, template_id)
            if not template:
                raise ValueError(f"No se encontró la plantilla con ID {template_id}")

            # Obtener los datos del vehículo
            vehicle_data = crud.get_vehicle_info(db, plate)
            if not vehicle_data:
                raise ValueError(f"No se encontraron datos para la placa {plate}")

            # Preparar los datos para la plantilla
            template_data = {
                "vehicle": vehicle_data["vehicle_info"],
                "owners": vehicle_data["owners"],
                "soat": vehicle_data["soats"][0] if vehicle_data["soats"] else None,
                "rtm": vehicle_data["rtms"][0] if vehicle_data["rtms"] else None,
                "policies": vehicle_data["civil_policies"],
                "current_owner": next((owner for owner in vehicle_data["owners"] if owner.is_current), None)
            }

            # Renderizar la plantilla
            template_obj = self.env.from_string(template.content)
            html_content = template_obj.render(**template_data)

            # Generar nombre de archivo si no se proporciona
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"reporte_{plate}_{timestamp}.pdf"

            output_path = os.path.join("output/pdfs", output_filename)

            # Generar PDF
            HTML(string=html_content).write_pdf(output_path)

            # Registrar el PDF generado
            crud.create_generated_pdf(db, {
                "vehicle_id": vehicle_data["vehicle_info"].id,
                "template_id": template_id,
                "pdf_path": output_path
            })

            return output_path

        except Exception as e:
            print(f"Error generando PDF: {str(e)}")
            raise

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