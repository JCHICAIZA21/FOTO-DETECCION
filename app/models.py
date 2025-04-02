from sqlalchemy import Column, Integer, String, JSON
from database import Base

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
