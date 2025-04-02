from sqlalchemy.orm import Session
from models import Attribute, GlobalVariable, ApiEndpoint
from typing import Dict, Any

def get_attributes(db: Session):
    return db.query(Attribute).all()

def create_attribute(db: Session, name: str, type: str):
    attr = Attribute(name=name, type=type)
    db.add(attr)
    db.commit()
    db.refresh(attr)
    return attr

def get_global_variables(db: Session):
    return db.query(GlobalVariable).all()

def get_global_variable(db: Session, name: str):
    return db.query(GlobalVariable).filter(GlobalVariable.name == name).first()

def create_global_variable(db: Session, name: str, value: str, description: str = None):
    var = GlobalVariable(name=name, value=value, description=description)
    db.add(var)
    db.commit()
    db.refresh(var)
    return var

def update_global_variable(db: Session, name: str, value: str):
    var = get_global_variable(db, name)
    if var:
        var.value = value
        db.commit()
        db.refresh(var)
    return var

def get_api_endpoints(db: Session):
    return db.query(ApiEndpoint).all()

def get_api_endpoint(db: Session, name: str):
    return db.query(ApiEndpoint).filter(ApiEndpoint.name == name).first()

def create_api_endpoint(
    db: Session, 
    name: str, 
    url: str, 
    method: str, 
    headers: Dict[str, Any],
    description: str = None
):
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
