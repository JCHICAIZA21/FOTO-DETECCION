from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from models import (
    Attribute, GlobalVariable, ApiEndpoint,
    VehicleInfo, VehicleOwner, VehicleOwnerAddress,
    VehicleSoat, VehicleRtm, VehicleCivilPolicy,
    PolicyDetail, PdfTemplate, GeneratedPdf, Event
)
from schemas import ApiEndpointCreate, GlobalVariableCreate, GlobalVariableUpdate
import logging
import traceback

logger = logging.getLogger(__name__)

def get_attributes(db: Session):
    return db.query(Attribute).all()

def create_attribute(db: Session, name: str, type: str):
    attr = Attribute(name=name, type=type)
    db.add(attr)
    db.commit()
    db.refresh(attr)
    return attr

def get_global_variables(db: Session) -> List[GlobalVariable]:
    return db.query(GlobalVariable).all()

def get_global_variable(db: Session, name: str) -> GlobalVariable:
    return db.query(GlobalVariable).filter(GlobalVariable.name == name).first()

def create_global_variable(
    db: Session, 
    name: str, 
    value: str, 
    description: str = None
) -> GlobalVariable:
    variable = GlobalVariable(
        name=name,
        value=value,
        description=description
    )
    db.add(variable)
    db.commit()
    db.refresh(variable)
    return variable

def update_global_variable(db: Session, name: str, value: str, description: str = None):
    var = get_global_variable(db, name)
    if var:
        var.value = value
        if description is not None:
            var.description = description
        db.commit()
        db.refresh(var)
    return var

def get_api_endpoints(db: Session) -> List[ApiEndpoint]:
    return db.query(ApiEndpoint).all()

def get_api_endpoint(db: Session, name: str) -> ApiEndpoint:
    return db.query(ApiEndpoint).filter(ApiEndpoint.name == name).first()

def create_api_endpoint(
    db: Session, 
    name: str, 
    url: str, 
    method: str, 
    headers: Dict[str, Any],
    description: str = None
) -> ApiEndpoint:
    endpoint = ApiEndpoint(
        name=name,
        url=url,
        method=method,
        headers=headers,
        description=description
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint

def update_api_endpoint(
    db: Session,
    name: str,
    url: str = None,
    method: str = None,
    headers: Dict[str, Any] = None
):
    endpoint = get_api_endpoint(db, name)
    if endpoint:
        if url:
            endpoint.url = url
        if method:
            endpoint.method = method
        if headers:
            endpoint.headers = headers
        db.commit()
        db.refresh(endpoint)
    return endpoint

def create_vehicle_info(db: Session, vehicle_data: dict) -> VehicleInfo:
    """Crea o actualiza la información del vehículo"""
    # Función auxiliar para convertir 'SI'/'NO' a boolean
    def to_bool(value: str) -> bool:
        if isinstance(value, bool):
            return value
        return value.upper() == 'SI' if value else False

    vehicle = db.query(VehicleInfo).filter(
        VehicleInfo.plate == vehicle_data["noPlaca"]
    ).first()
    
    if not vehicle:
        vehicle = VehicleInfo(
            plate=vehicle_data["noPlaca"],
            no_registro=vehicle_data["noRegistro"],
            no_licencia_transito=vehicle_data["noLicenciaTransito"],
            fecha_expedicion_lic_transito=datetime.strptime(
                vehicle_data["fechaExpedicionLicTransito"], 
                "%d/%m/%Y"
            ),
            estado_vehiculo=vehicle_data["estadoDelVehiculo"],
            tipo_servicio=vehicle_data["tipoServicio"],
            clase_vehiculo=vehicle_data["claseVehiculo"],
            marca=vehicle_data["marca"],
            linea=vehicle_data["linea"],
            modelo=vehicle_data["modelo"],
            color=vehicle_data["color"],
            no_serie=vehicle_data["noSerie"],
            no_motor=vehicle_data["noMotor"],
            no_chasis=vehicle_data["noChasis"],
            no_vin=vehicle_data["noVin"],
            cilindraje=vehicle_data["cilindraje"],
            tipo_carroceria=vehicle_data["tipoCarroceria"],
            fecha_matricula=datetime.strptime(
                vehicle_data["fechaMatricula"], 
                "%d/%m/%Y"
            ),
            tiene_gravamenes=to_bool(vehicle_data["tieneGravamenes"]),
            organismo_transito=vehicle_data["organismoTransito"],
            prendas=to_bool(vehicle_data["prendas"]),
            prendario=vehicle_data["prendario"],
            clasificacion=vehicle_data["clasificacion"],
            capacidad_carga=vehicle_data["capacidadCarga"],
            peso_bruto_vehicular=vehicle_data["pesoBrutoVehicular"],
            no_ejes=int(vehicle_data["noEjes"])
        )
        db.add(vehicle)
    else:
        # Actualizar los campos existentes
        for key, value in vehicle_data.items():
            if hasattr(vehicle, key):
                # Convertir campos booleanos
                if key in ["tieneGravamenes", "prendas"]:
                    value = to_bool(value)
                # Convertir fechas
                elif key in ["fechaExpedicionLicTransito", "fechaMatricula"]:
                    value = datetime.strptime(value, "%d/%m/%Y")
                # Convertir enteros
                elif key == "noEjes":
                    value = int(value)
                setattr(vehicle, key, value)
    
    db.commit()
    db.refresh(vehicle)
    return vehicle

def create_vehicle_owner(db: Session, owner_data: dict, vehicle_id: int) -> VehicleOwner:
    """Crea o actualiza la información del propietario"""
    owner = VehicleOwner(
        vehicle_id=vehicle_id,
        tipo_documento=owner_data["tipoDocumento"],
        numero_documento=owner_data["noDocumento"],
        nombre_completo=owner_data["nombreCompleto"],
        primer_nombre=owner_data.get("primerNombre"),
        segundo_nombre=owner_data.get("segundoNombre"),
        primer_apellido=owner_data.get("primerApellido"),
        segundo_apellido=owner_data.get("segundoApellido"),
        tipo_propiedad=owner_data.get("tipoPropiedad"),
        detalle_propiedad=owner_data.get("detallePropiedad"),
        fecha_nacimiento=datetime.strptime(
            owner_data["fechaNacimiento"], 
            "%d/%m/%Y"
        ) if "fechaNacimiento" in owner_data else None
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner

def create_owner_address(db: Session, address_data: dict, owner_id: int) -> VehicleOwnerAddress:
    """Crea una dirección para un propietario"""
    address = VehicleOwnerAddress(
        owner_id=owner_id,
        direccion=address_data.get("direccion"),
        departamento=address_data.get("departamento"),
        ciudad=address_data.get("ciudad"),
        telefono=address_data.get("telefono"),
        celular=address_data.get("celular"),
        email=address_data.get("email")
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return address

def create_vehicle_soat(db: Session, soat_data: dict, vehicle_id: int) -> VehicleSoat:
    """Crea un registro SOAT para un vehículo"""
    soat = VehicleSoat(
        vehicle_id=vehicle_id,
        no_poliza=soat_data["noPoliza"],
        fecha_expedicion=datetime.strptime(soat_data["fechaExpedicion"], "%d/%m/%Y"),
        fecha_vigencia=datetime.strptime(soat_data["fechaVigencia"], "%d/%m/%Y"),
        fecha_vencimiento=datetime.strptime(soat_data["fechaVencimiento"], "%d/%m/%Y"),
        nit_entidad=soat_data["nitEntidad"],
        entidad_expide=soat_data["entidadExpideSoat"],
        estado=soat_data["estado"]
    )
    db.add(soat)
    db.commit()
    db.refresh(soat)
    return soat

def create_vehicle_rtm(db: Session, rtm_data: dict, vehicle_id: int) -> VehicleRtm:
    """Crea un registro RTM para un vehículo"""
    def to_bool(value: str) -> bool:
        if isinstance(value, bool):
            return value
        return value.upper() == 'SI' if value else False

    rtm = VehicleRtm(
        vehicle_id=vehicle_id,
        nro_rtm=rtm_data["nroRTM"],
        tipo_revision=rtm_data["tipoRevision"],
        fecha_expedicion=datetime.strptime(rtm_data["fechaExpedicion"], "%d/%m/%Y"),
        fecha_vigente=datetime.strptime(rtm_data["fechaVigente"], "%d/%m/%Y"),
        cda_expide=rtm_data["cdaExpide"],
        vigente=to_bool(rtm_data["vigente"])
    )
    db.add(rtm)
    db.commit()
    db.refresh(rtm)
    return rtm

def create_civil_policy(db: Session, policy_data: dict, vehicle_id: int) -> VehicleCivilPolicy:
    """Crea una póliza civil para un vehículo"""
    policy = VehicleCivilPolicy(
        vehicle_id=vehicle_id,
        numero_poliza=policy_data["numeroPoliza"],
        fecha_expedicion=datetime.strptime(policy_data["fechaExpedicion"], "%d/%m/%Y"),
        fecha_vigencia=datetime.strptime(policy_data["fechaVigencia"], "%d/%m/%Y"),
        tipo_documento=policy_data["tipoDocumento"],
        numero_documento=policy_data["numeroDocumento"],
        nombre_aseguradora=policy_data["nombreAseguradora"],
        tipo_poliza=policy_data["tipoPoliza"],
        fecha_inicio=datetime.strptime(policy_data["fechaInicio"], "%d/%m/%Y"),
        estado_poliza=policy_data["estadoPoliza"]
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy

def create_policy_detail(db: Session, detail_data: dict, policy_id: int) -> PolicyDetail:
    """Crea un detalle de póliza"""
    detail = PolicyDetail(
        policy_id=policy_id,
        nro_poliza=detail_data["nroPoliza"],
        tipo_doc_tomador=detail_data["tipoDocTomador"],
        nro_doc_tomador=detail_data["nroDocTomador"],
        cobertura=detail_data["cobertura"],
        monto=detail_data["monto"]
    )
    db.add(detail)
    db.commit()
    db.refresh(detail)
    return detail

def get_vehicle_by_plate(db: Session, plate: str) -> Optional[VehicleInfo]:
    """Obtiene un vehículo por su placa."""
    return db.query(VehicleInfo).filter(VehicleInfo.plate == plate).first()

def create_vehicle(db: Session, vehicle_data: dict) -> VehicleInfo:
    """Crea un nuevo vehículo."""
    db_vehicle = VehicleInfo(**vehicle_data)
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle

def update_vehicle(db: Session, vehicle_id: int, vehicle_data: dict) -> VehicleInfo:
    """Actualiza un vehículo existente."""
    db_vehicle = db.query(VehicleInfo).filter(VehicleInfo.id == vehicle_id).first()
    if db_vehicle:
        for key, value in vehicle_data.items():
            setattr(db_vehicle, key, value)
        db.commit()
        db.refresh(db_vehicle)
    return db_vehicle

def store_vehicle_data(db: Session, vehicle_data: Dict[str, Any]) -> VehicleInfo:
    """Almacena o actualiza los datos de un vehículo"""
    plate = vehicle_data.get("placa")
    if not plate:
        raise ValueError("La placa es requerida")

    vehicle = get_vehicle_by_plate(db, plate)
    if vehicle:
        # Actualizar vehículo existente
        for key, value in vehicle_data.items():
            if hasattr(vehicle, key):
                setattr(vehicle, key, value)
        db.commit()
        db.refresh(vehicle)
    else:
        # Crear nuevo vehículo
        vehicle = create_vehicle(db, vehicle_data)

    return vehicle

def get_vehicle_info(db: Session, plate: str) -> dict:
    """Obtiene toda la información almacenada de un vehículo"""
    vehicle = db.query(VehicleInfo).filter(VehicleInfo.plate == plate).first()
    if not vehicle:
        return None
    
    return {
        "vehicle_info": vehicle,
        "owners": vehicle.owners,
        "soats": vehicle.soats,
        "rtms": vehicle.rtms,
        "civil_policies": vehicle.civil_policies
    }

def get_all_templates(db: Session) -> List[PdfTemplate]:
    """Obtiene todas las plantillas."""
    return db.query(PdfTemplate).all()

def get_template_by_id(db: Session, template_id: int) -> Optional[PdfTemplate]:
    """Obtiene una plantilla por su ID."""
    return db.query(PdfTemplate).filter(PdfTemplate.id == template_id).first()

def get_template_by_name(db: Session, name: str) -> Optional[PdfTemplate]:
    """Obtiene una plantilla por su nombre."""
    return db.query(PdfTemplate).filter(PdfTemplate.name == name).first()

def create_template(db: Session, name: str, content: str) -> PdfTemplate:
    """Crea una nueva plantilla."""
    template = PdfTemplate(
        name=name,
        content=content
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template

def update_template(db: Session, template_id: int, name: str = None, content: str = None) -> Optional[PdfTemplate]:
    """Actualiza una plantilla existente."""
    template = get_template_by_id(db, template_id)
    if template:
        if name is not None:
            template.name = name
        if content is not None:
            template.content = content
        template.updated_at = datetime.now()
        db.commit()
        db.refresh(template)
    return template

def delete_template(db: Session, template_id: int) -> bool:
    """Elimina una plantilla."""
    template = get_template_by_id(db, template_id)
    if template:
        db.delete(template)
        db.commit()
        return True
    return False

def create_event(
    db: Session,
    plate: str,
    event_type: str,
    event_data: dict
) -> Event:
    """
    Crea un nuevo evento en la base de datos
    """
    # Obtener el vehículo asociado a la placa.
    vehicle = db.query(VehicleInfo).filter(VehicleInfo.plate == plate).first()
    if not vehicle:
        # Si no existe el vehículo, crear uno nuevo
        vehicle = VehicleInfo(
            plate=plate,
            vehicle_data={},
            owner_data={},
            soat_data={},
            rtm_data={}
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)

    # Crear el evento
    db_event = Event(
        vehicle_id=vehicle.id,
        plate=plate,
        event_type=event_type,
        event_data=event_data
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_vehicle_data(db: Session, plate: str):
    """
    Obtiene todos los datos relacionados con un vehículo por su placa.
    """
    try:
        # Obtener el vehículo
        vehicle = db.query(VehicleInfo).filter(VehicleInfo.plate == plate).first()
        if not vehicle:
            logger.warning(f"No se encontró el vehículo con placa {plate}")
            return None

        # Convertir el vehículo a diccionario
        vehicle_dict = {
            "id": vehicle.id,
            "plate": vehicle.plate,
            "no_registro": vehicle.no_registro,
            "no_licencia_transito": vehicle.no_licencia_transito,
            "fecha_expedicion_lic_transito": vehicle.fecha_expedicion_lic_transito.isoformat() if vehicle.fecha_expedicion_lic_transito else None,
            "estado_vehiculo": vehicle.estado_vehiculo,
            "tipo_servicio": vehicle.tipo_servicio,
            "clase_vehiculo": vehicle.clase_vehiculo,
            "marca": vehicle.marca,
            "linea": vehicle.linea,
            "modelo": vehicle.modelo,
            "color": vehicle.color,
            "no_serie": vehicle.no_serie,
            "no_motor": vehicle.no_motor,
            "no_chasis": vehicle.no_chasis,
            "no_vin": vehicle.no_vin,
            "cilindraje": vehicle.cilindraje,
            "tipo_carroceria": vehicle.tipo_carroceria,
            "fecha_matricula": vehicle.fecha_matricula.isoformat() if vehicle.fecha_matricula else None,
            "tiene_gravamenes": vehicle.tiene_gravamenes,
            "organismo_transito": vehicle.organismo_transito,
            "prendas": vehicle.prendas,
            "prendario": vehicle.prendario,
            "clasificacion": vehicle.clasificacion,
            "capacidad_carga": vehicle.capacidad_carga,
            "peso_bruto_vehicular": vehicle.peso_bruto_vehicular,
            "no_ejes": vehicle.no_ejes
        }

        try:
            # Intentar obtener eventos
            events = db.query(Event).filter(Event.vehicle_id == vehicle.id).all()
            events_list = []
            for event in events:
                event_dict = {
                    "id": event.id,
                    "event_id": event.event_id,
                    "device_id": event.device_id,
                    "date": event.date.isoformat() if event.date else None,
                    "evidences": event.evidences,
                    "video_filename": event.video_filename
                }
                events_list.append(event_dict)
        except Exception as e:
            logger.error(f"Error al obtener eventos: {str(e)}")
            events_list = []

        # Devolver los datos del vehículo y sus eventos
        return {
            "vehicle": vehicle_dict,
            "events": events_list
        }

    except Exception as e:
        logger.error(f"Error al obtener datos del vehículo {plate}: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def create_or_update_vehicle(
    db: Session,
    plate: str,
    vehicle_data: dict,
    owner_data: dict,
    soat_data: dict,
    rtm_data: dict
) -> VehicleInfo:
    """
    Crea o actualiza un vehículo en la base de datos
    """
    db_vehicle = db.query(VehicleInfo).filter(VehicleInfo.plate == plate).first()
    
    if db_vehicle:
        # Actualizar vehículo existente
        db_vehicle.vehicle_data = vehicle_data
        db_vehicle.owner_data = owner_data
        db_vehicle.soat_data = soat_data
        db_vehicle.rtm_data = rtm_data
        db_vehicle.updated_at = datetime.now()
    else:
        # Crear nuevo vehículo
        db_vehicle = VehicleInfo(
            plate=plate,
            vehicle_data=vehicle_data,
            owner_data=owner_data,
            soat_data=soat_data,
            rtm_data=rtm_data,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_vehicle)
    
    db.commit()
    db.refresh(db_vehicle)
    return db_vehicle
