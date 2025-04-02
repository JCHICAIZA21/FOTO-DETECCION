from pydantic import BaseModel
from typing import Dict, Optional

class ApiEndpointBase(BaseModel):
    name: str
    url: str
    method: str
    headers: Dict
    description: Optional[str] = None

class ApiEndpointCreate(ApiEndpointBase):
    pass

class ApiEndpoint(ApiEndpointBase):
    id: int

    class Config:
        from_attributes = True

class GlobalVariableBase(BaseModel):
    name: str
    value: str
    description: Optional[str] = None

class GlobalVariableCreate(GlobalVariableBase):
    pass

class GlobalVariableUpdate(BaseModel):
    value: str
    description: Optional[str] = None

class GlobalVariable(GlobalVariableBase):
    id: int

    class Config:
        from_attributes = True 