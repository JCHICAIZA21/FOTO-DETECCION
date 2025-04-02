from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

logger = logging.getLogger(__name__)

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/json_processor")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    try:
        # Importar todos los modelos aquí para asegurar que están registrados
        from models import VehicleInfo, Event, VehicleOwner, VehicleOwnerAddress, VehicleSoat, VehicleRtm, VehicleCivilPolicy, PolicyDetail, GeneratedPdf
        
        # Crear todas las tablas
        Base.metadata.create_all(bind=engine)
        logger.info("Base de datos inicializada correctamente")
        
        # Verificar que la tabla events existe
        with engine.connect() as conn:
            result = conn.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'events')"))
            exists = result.scalar()
            if not exists:
                logger.error("La tabla 'events' no se creó correctamente")
                raise Exception("La tabla 'events' no se creó correctamente")
            logger.info("La tabla 'events' existe correctamente")
            
    except Exception as e:
        logger.error(f"Error inicializando la base de datos: {str(e)}")
        raise
