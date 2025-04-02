from sqlalchemy import Column, Integer, String, JSON, Text, DateTime, ForeignKey, Boolean, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

# Definir Base aquí
Base = declarative_base()

class Attribute(Base):
    __tablename__ = "attributes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)

class GlobalVariable(Base):
    __tablename__ = "global_variables"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    value = Column(String)
    description = Column(String, nullable=True)

class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    url = Column(String)
    method = Column(String)
    headers = Column(JSON)  # Almacena headers como JSON
    description = Column(String, nullable=True)

class PdfTemplate(Base):
    __tablename__ = "pdf_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    content = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    generated_pdfs = relationship("GeneratedPdf", back_populates="template")

class PdfVariable(Base):
    __tablename__ = "pdf_variables"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey('pdf_templates.id'))
    name = Column(String)
    default_value = Column(String, nullable=True)
    description = Column(String, nullable=True)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String, nullable=True)

class UserRole(Base):
    __tablename__ = "user_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    role_id = Column(Integer, ForeignKey('roles.id'))

class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String, nullable=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey('roles.id'))
    permission_id = Column(Integer, ForeignKey('permissions.id'))

class VehicleInfo(Base):
    __tablename__ = "vehicle_info"

    id = Column(Integer, primary_key=True, index=True)
    plate = Column(String, unique=True, index=True)
    vehicle_data = Column(JSON)
    owner_data = Column(JSON)
    soat_data = Column(JSON)
    rtm_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relaciones
    events = relationship("Event", back_populates="vehicle", cascade="all, delete-orphan")
    owners = relationship("VehicleOwner", back_populates="vehicle", cascade="all, delete-orphan")
    soats = relationship("VehicleSoat", back_populates="vehicle", cascade="all, delete-orphan")
    rtms = relationship("VehicleRtm", back_populates="vehicle", cascade="all, delete-orphan")
    civil_policies = relationship("VehicleCivilPolicy", back_populates="vehicle", cascade="all, delete-orphan")
    generated_pdfs = relationship("GeneratedPdf", back_populates="vehicle", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicle_info.id", ondelete="CASCADE"))
    plate = Column(String, index=True)
    event_type = Column(String)
    event_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.now)

    # Relación con vehículo
    vehicle = relationship("VehicleInfo", back_populates="events")

class VehicleOwner(Base):
    __tablename__ = "vehicle_owners"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey('vehicle_info.id', ondelete="CASCADE"))
    tipo_documento = Column(String)
    numero_documento = Column(String)
    nombre_completo = Column(String)
    primer_nombre = Column(String)
    segundo_nombre = Column(String)
    primer_apellido = Column(String)
    segundo_apellido = Column(String)
    tipo_propiedad = Column(Integer)
    detalle_propiedad = Column(String)
    fecha_nacimiento = Column(DateTime)
    fecha_inicio_propiedad = Column(DateTime)
    fecha_fin_propiedad = Column(DateTime)
    is_current = Column(Boolean, default=True)
    
    vehicle = relationship("VehicleInfo", back_populates="owners")
    addresses = relationship("VehicleOwnerAddress", back_populates="owner", cascade="all, delete-orphan")

class VehicleOwnerAddress(Base):
    __tablename__ = "vehicle_owner_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey('vehicle_owners.id'))
    direccion = Column(String)
    departamento = Column(String)
    ciudad = Column(String)
    telefono = Column(String)
    celular = Column(String)
    email = Column(String)
    
    owner = relationship("VehicleOwner", back_populates="addresses")

class VehicleSoat(Base):
    __tablename__ = "vehicle_soat"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey('vehicle_info.id'))
    no_poliza = Column(String)
    fecha_expedicion = Column(DateTime)
    fecha_vigencia = Column(DateTime)
    fecha_vencimiento = Column(DateTime)
    nit_entidad = Column(String)
    entidad_expide = Column(String)
    estado = Column(String)
    
    vehicle = relationship("VehicleInfo", back_populates="soats")

class VehicleRtm(Base):
    __tablename__ = "vehicle_rtm"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey('vehicle_info.id'))
    nro_rtm = Column(String)
    tipo_revision = Column(String)
    fecha_expedicion = Column(DateTime)
    fecha_vigente = Column(DateTime)
    cda_expide = Column(String)
    vigente = Column(Boolean)
    
    vehicle = relationship("VehicleInfo", back_populates="rtms")

class VehicleCivilPolicy(Base):
    __tablename__ = "vehicle_civil_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey('vehicle_info.id'))
    numero_poliza = Column(String)
    fecha_expedicion = Column(DateTime)
    fecha_vigencia = Column(DateTime)
    tipo_documento = Column(String)
    numero_documento = Column(String)
    nombre_aseguradora = Column(String)
    tipo_poliza = Column(String)
    fecha_inicio = Column(DateTime)
    estado_poliza = Column(String)
    
    vehicle = relationship("VehicleInfo", back_populates="civil_policies")
    details = relationship("PolicyDetail", back_populates="policy")

class PolicyDetail(Base):
    __tablename__ = "policy_details"
    
    id = Column(Integer, primary_key=True, index=True)
    policy_id = Column(Integer, ForeignKey('vehicle_civil_policies.id'))
    nro_poliza = Column(String)
    tipo_doc_tomador = Column(String)
    nro_doc_tomador = Column(String)
    cobertura = Column(String)
    monto = Column(DECIMAL)
    
    policy = relationship("VehicleCivilPolicy", back_populates="details")

class GeneratedPdf(Base):
    __tablename__ = "generated_pdfs"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("pdf_templates.id"))
    vehicle_id = Column(Integer, ForeignKey("vehicle_info.id"))
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    vehicle = relationship("VehicleInfo", back_populates="generated_pdfs")
    template = relationship("PdfTemplate", back_populates="generated_pdfs")
