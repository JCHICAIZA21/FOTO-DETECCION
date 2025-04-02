import requests
import os

RUNT_SERVICE_URL = os.getenv('RUNT_SERVICE_URL', 'http://runt-service:8002')

def get_templates():
    response = requests.get(f"{RUNT_SERVICE_URL}/templates")
    return response.json() if response.ok else []

def get_template_variables():
    response = requests.get(f"{RUNT_SERVICE_URL}/template-variables")
    return response.json() if response.ok else []

def get_database_fields():
    response = requests.get(f"{RUNT_SERVICE_URL}/database-fields")
    return response.json() if response.ok else {}

def create_template(template_data):
    response = requests.post(f"{RUNT_SERVICE_URL}/templates", json=template_data)
    return response.json() if response.ok else None

def update_template(template_id, template_data):
    response = requests.put(
        f"{RUNT_SERVICE_URL}/templates/{template_id}", 
        json=template_data
    )
    return response.json() if response.ok else None

def create_template_variable(variable_data):
    response = requests.post(
        f"{RUNT_SERVICE_URL}/template-variables", 
        json=variable_data
    )
    return response.json() if response.ok else None 