import requests
from typing import Dict, Any
from database import SessionLocal
import crud

class RuntAPIClient:
    def __init__(self):
        self.db = SessionLocal()

    def get_global_var(self, name: str) -> str:
        var = crud.get_global_variable(self.db, name)
        return var.value if var else ""

    def get_endpoint_config(self, name: str) -> Dict[str, Any]:
        endpoint = crud.get_api_endpoint(self.db, name)
        if not endpoint:
            raise ValueError(f"Endpoint {name} no encontrado")
        
        # Procesar headers reemplazando variables globales
        headers = endpoint.headers.copy()
        for key, value in headers.items():
            if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                var_name = value[2:-2]
                headers[key] = self.get_global_var(var_name)
        
        return {
            "url": endpoint.url,
            "method": endpoint.method,
            "headers": headers
        }

    def generate_key(self) -> Dict[str, Any]:
        try:
            config = self.get_endpoint_config("generarLlave")
            response = requests.request(
                method=config["method"],
                url=config["url"],
                headers=config["headers"]
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.request(
                method=method,
                url=url,
                headers=self.get_headers(),
                json=data
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": str(e)} 