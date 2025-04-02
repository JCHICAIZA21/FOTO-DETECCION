from typing import Dict, Any, List
import requests
from sqlalchemy.orm import Session
import crud
import schemas
import json
import base64
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA1
from models import ApiEndpoint, GlobalVariable
import os
import subprocess
import time
import hmac
import hashlib

class RuntService:
    def get_global_var(self, db: Session, name: str) -> str:
        var = crud.get_global_variable(db, name)
        return var.value if var else ""

    def sign_with_rsa(self, db: Session, data: str) -> str:
        try:
            # Ejecutar el script de Node.js solo con los datos a firmar
            process = subprocess.Popen(
                ['node', 'sign.js', data],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Obtener la salida
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                print(f"Error en el script de firma: {stderr.decode()}")
                raise ValueError("Error al generar la firma")
            
            # La firma está en la salida estándar
            firma_base64 = stdout.decode().strip()
            
            print("\nDebug información:")
            print(f"Data a firmar: {data}")
            print(f"Base64 signature: {firma_base64}")
            
            return firma_base64

        except Exception as e:
            print(f"\nError completo en sign_with_rsa: {str(e)}")
            raise ValueError(f"Error al firmar: {str(e)}")

    def verify_signature(self, data: str, signature_base64: str) -> bool:
        try:
            # Convertir la firma de base64 a bytes
            signature = base64.b64decode(signature_base64)
            
            # Leer la llave pública (si la tienes)
            cert_path = "claveprivada.pkcs8.pem"  # o la ruta a tu llave pública
            with open(cert_path, 'r') as f:
                key_pem = f.read().strip()
            
            # Crear objeto de llave
            key = RSA.import_key(key_pem)
            
            # Crear el hash SHA1 de los datos
            h = SHA1.new(data.encode('utf-8'))
            
            # Verificar la firma
            try:
                pkcs1_15.new(key).verify(h, signature)
                return True
            except (ValueError, TypeError):
                return False
            
        except Exception as e:
            print(f"Error en verify_signature: {str(e)}")
            return False

    def get_endpoint_url(self, db: Session, endpoint_name: str) -> str:
        """
        Obtiene la URL del endpoint desde la base de datos
        """
        try:
            # Consultar la tabla de endpoints
            endpoint = db.query(ApiEndpoint).filter(
                ApiEndpoint.name == endpoint_name
            ).first()
            
            if not endpoint:
                raise ValueError(f"No se encontró el endpoint: {endpoint_name}")
                
            return endpoint.url
        except Exception as e:
            print(f"Error obteniendo URL del endpoint: {str(e)}")
            raise

    def generate_key(self, db: Session) -> dict:
        try:
            usuario = self.get_global_var(db, "usuarioAseguradoraCliente")
            body = json.dumps({"idUsuario": usuario}, separators=(',', ':'))
            firma = self.sign_with_rsa(db, body)
            
            # URL corregida con /admin/
            url = "http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/admin/generarLlave"
            
            # Comando curl exactamente como en Postman
            curl_command = [
                'curl',
                '--location',
                '--request', 'POST',
                url,
                '--header', 'Content-Type: application/json',
                '--header', f'X-Runt-Id-Usuario: {usuario}',
                '--header', f'X-Runt-Firma: {firma}',
                '--header', 'X-Forwarded-For: 201.184.19.178',
                '--data', body,
                '-i'
            ]
            
            print("\nGenerando llave HMAC...")
            print(f"URL: {url}")
            print(f"Body: {body}")
            print(f"Firma: {firma}")
            
            process = subprocess.Popen(
                curl_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate()
            stdout_output = stdout.decode().strip()
            stderr_output = stderr.decode().strip()
            
            # Separar headers y body
            response_parts = stdout_output.split('\r\n\r\n')
            headers = response_parts[0] if response_parts else ''
            response_body = response_parts[1] if len(response_parts) > 1 else ''
            
            # Verificar si la respuesta es exitosa
            if response_body and not "Error" in response_body:
                llave = response_body.strip()
                
                # Actualizar la variable global
                self.update_variable(
                    db,
                    "llavehmaccliente",
                    schemas.GlobalVariableUpdate(
                        value=llave,
                        description="Llave HMAC generada por el servicio"
                    )
                )
                
                return {
                    "success": True,
                    "data": {
                        "llave": llave,
                        "mensaje": "Llave HMAC generada y almacenada exitosamente"
                    }
                }
            
            return {
                "success": False,
                "error": "Error en la respuesta del servidor",
                "details": {
                    "request": {
                        "url": url,
                        "method": "POST",
                        "headers": {
                            "Content-Type": "application/json",
                            "X-Runt-Id-Usuario": usuario,
                            "X-Runt-Firma": firma,
                            "X-Forwarded-For": "201.184.19.178"
                        },
                        "body": body
                    },
                    "response": {
                        "headers": headers,
                        "body": response_body,
                        "raw_response": stdout_output,
                        "stderr": stderr_output
                    }
                }
            }
            
        except Exception as e:
            print(f"\nError en generate_key: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "details": {
                    "exception": str(e)
                }
            }

    def test_connection(self, db: Session) -> Dict[str, Any]:
        try:
            endpoint = crud.get_api_endpoint(db, "generarLlave")
            if not endpoint:
                return {"error": "Endpoint no configurado"}

            usuario = self.get_global_var(db, "usuarioAseguradoraCliente")
            body = {"idUsuario": usuario}
            body_str = json.dumps(body, separators=(',', ':'))
            
            return {
                "url": endpoint.url,
                "headers": {
                    "Content-Type": "application/json",
                    "X-Runt-Id-Usuario": usuario,
                    "X-Runt-Firma": self.sign_with_rsa(db, body_str),
                    "X-Forwarded-For": "201.184.19.178"
                },
                "body": body,
                "test_data": {
                    "usuario": usuario,
                    "body_to_sign": body_str
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def get_all_endpoints(self, db: Session) -> List[schemas.ApiEndpoint]:
        return crud.get_api_endpoints(db)

    def create_endpoint(
        self, 
        db: Session, 
        endpoint: schemas.ApiEndpointCreate
    ) -> schemas.ApiEndpoint:
        return crud.create_api_endpoint(
            db,
            name=endpoint.name,
            url=endpoint.url,
            method=endpoint.method,
            headers=endpoint.headers,
            description=endpoint.description
        )

    def get_all_variables(self, db: Session) -> List[schemas.GlobalVariable]:
        return crud.get_global_variables(db)

    def create_variable(
        self, 
        db: Session, 
        variable: schemas.GlobalVariableCreate
    ) -> schemas.GlobalVariable:
        return crud.create_global_variable(
            db,
            name=variable.name,
            value=variable.value,
            description=variable.description
        )

    def update_variable(
        self, 
        db: Session, 
        name: str, 
        variable: schemas.GlobalVariableUpdate
    ) -> schemas.GlobalVariable:
        var = crud.get_global_variable(db, name)
        if var:
            var.value = variable.value
            if variable.description is not None:
                var.description = variable.description
            db.commit()
            db.refresh(var)
        return var

    def load_jsrsasign(self) -> str:
        """
        Carga la biblioteca jsrsasign desde el archivo
        """
        try:
            with open('jsrsasign-js.txt', 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error cargando jsrsasign: {str(e)}")
            return None

    def validate_key(self, db: Session) -> dict:
        try:
            usuario = self.get_global_var(db, "usuarioAseguradoraCliente")
            llave_hmac = self.get_global_var(db, "llavehmaccliente")
            
            # URL corregida para incluir /admin/
            url = "http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/admin/validarLlave"
            
            body = json.dumps({
                "idUsuario": usuario,
                "llave": llave_hmac
            }, separators=(',', ':'))
            
            firma = self.sign_with_rsa(db, body)
            
            curl_command = [
                'curl',
                '--location',
                '--request', 'POST',
                url,
                '--header', 'Content-Type: application/json',
                '--header', f'X-Runt-Id-Usuario: {usuario}',
                '--header', f'X-Runt-Firma: {firma}',
                '--header', 'X-Forwarded-For: 201.184.19.178',
                '--data', body,
                '-i'
            ]
            
            print(f"\nValidando llave HMAC...")
            print(f"URL: {url}")
            print(f"Body: {body}")
            
            process = subprocess.Popen(
                curl_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate()
            stdout_output = stdout.decode().strip()
            
            # Separar headers y body
            response_parts = stdout_output.split('\r\n\r\n')
            response_body = response_parts[1] if len(response_parts) > 1 else ''
            
            if "Error" not in response_body:
                return {
                    "success": True,
                    "data": {
                        "mensaje": "Llave validada exitosamente",
                        "respuesta": response_body.strip()
                    }
                }
            
            return {
                "success": False,
                "error": "Error al validar la llave",
                "details": {
                    "response": response_body,
                    "full_response": stdout_output
                }
            }
            
        except Exception as e:
            print(f"\nError en validate_key: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def query_vehicle(self, db: Session, plate: str) -> dict:
        try:
            usuario = self.get_global_var(db, "usuarioAseguradoraCliente")
            llave_hmac = self.get_global_var(db, "llavehmaccliente")
            
            # Primero validar la llave antes de consultar
            print("\nValidando llave antes de consultar...")
            validate_result = self.validate_key(db)
            if not validate_result.get("success"):
                print("Error al validar llave, intentando regenerar...")
                # Intentar regenerar y validar la llave
                key_result = self.generate_key(db)
                if not key_result.get("success"):
                    return {
                        "success": False,
                        "error": "Error al regenerar llave HMAC",
                        "details": key_result
                    }
                
                # Obtener la nueva llave
                llave_hmac = self.get_global_var(db, "llavehmaccliente")
                
                # Validar la nueva llave
                validate_result = self.validate_key(db)
                if not validate_result.get("success"):
                    return {
                        "success": False,
                        "error": "Error al validar la nueva llave HMAC",
                        "details": validate_result
                    }
            
            print("Llave validada exitosamente, procediendo con la consulta...")
            
            # URL sin /admin/
            url = "http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/consulta/vehiculos"
            
            # Preparar el body con el formato exacto
            body_dict = {
                "tipoConsulta": "PLACA",
                "noPlaca": plate.upper(),  # Asegurar que la placa esté en mayúsculas
                "llave": llave_hmac.strip()  # Eliminar espacios en blanco
            }
            
            # Convertir a JSON manteniendo el orden de las claves
            body = json.dumps(body_dict, separators=(',', ':'))
            
            # Generar firma
            firma = self.sign_with_rsa(db, body)
            
            # Construir comando curl
            curl_command = [
                'curl',
                '--location',
                url,
                '--header', 'Content-Type: application/json',
                '--header', f'X-Runt-Id-Usuario: {usuario}',
                '--header', f'X-Runt-Firma: {firma}',
                '--header', 'X-Forwarded-For: 201.184.19.178',
                '--data-raw', body,
                '-i'
            ]
            
            print(f"\nConsultando vehículo con placa {plate}...")
            print(f"URL: {url}")
            print(f"Body: {body}")
            print(f"Headers:")
            print(f"  X-Runt-Id-Usuario: {usuario}")
            print(f"  X-Runt-Firma: {firma}")
            
            process = subprocess.Popen(
                curl_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate()
            stdout_output = stdout.decode().strip()
            stderr_output = stderr.decode().strip()
            
            # Separar headers y body
            response_parts = stdout_output.split('\r\n\r\n')
            headers = response_parts[0] if response_parts else ''
            response_body = response_parts[1] if len(response_parts) > 1 else ''
            
            print("\nRespuesta completa:")
            print(f"Headers: {headers}")
            print(f"Body: {response_body}")
            
            try:
                # Verificar si hay errores específicos
                if "Debe validar la llave" in response_body:
                    return {
                        "success": False,
                        "error": "La llave no está validada",
                        "details": {
                            "message": response_body,
                            "validation_status": validate_result
                        }
                    }
                
                # Intentar parsear la respuesta como JSON
                if response_body and not "Error" in response_body:
                    try:
                        response_data = json.loads(response_body)
                        return {
                            "success": True,
                            "data": response_data
                        }
                    except json.JSONDecodeError:
                        # Si no es JSON pero no hay error, devolver el texto
                        return {
                            "success": True,
                            "data": {
                                "response": response_body
                            }
                        }
                else:
                    return {
                        "success": False,
                        "error": "Error en la respuesta del servidor",
                        "details": {
                            "response": response_body,
                            "full_response": stdout_output,
                            "stderr": stderr_output,
                            "request": {
                                "url": url,
                                "method": "POST",
                                "headers": {
                                    "Content-Type": "application/json",
                                    "X-Runt-Id-Usuario": usuario,
                                    "X-Runt-Firma": firma,
                                    "X-Forwarded-For": "201.184.19.178"
                                },
                                "body": body
                            }
                        }
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error al procesar la respuesta: {str(e)}",
                    "details": {
                        "response": response_body,
                        "full_response": stdout_output,
                        "stderr": stderr_output
                    }
                }
            
        except Exception as e:
            print(f"\nError en query_vehicle: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def process_runt_sequence(self, db: Session, plates: list) -> dict:
        try:
            print(f"\nIniciando consulta para {len(plates)} placas")
            usuario = self.get_global_var(db, "usuarioAseguradoraCliente")
            
            # Paso 1: Generar llave HMAC (solo una vez para todas las consultas)
            print("\nPaso 1: Generando llave HMAC...")
            gen_body = json.dumps({"idUsuario": usuario}, separators=(',', ':'))
            gen_firma = self.sign_with_rsa(db, gen_body)
            
            gen_command = [
                'curl',
                '--location',
                'http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/admin/generarLlave',
                '--header', 'Content-Type: application/json',
                '--header', f'X-Runt-Id-Usuario: {usuario}',
                '--header', f'X-Runt-Firma: {gen_firma}',
                '--header', 'X-Forwarded-For: 201.184.19.178',
                '--data', gen_body
            ]
            
            gen_process = subprocess.Popen(
                gen_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            gen_stdout, _ = gen_process.communicate()
            llave_hmac = gen_stdout.decode().strip()
            
            if not llave_hmac or "Error" in llave_hmac:
                return {
                    "success": False,
                    "error": "Error al generar llave HMAC",
                    "details": {"response": llave_hmac}
                }
            
            print(f"Llave HMAC generada: {llave_hmac}")
            
            # Paso 2: Validar llave
            print("\nPaso 2: Validando llave HMAC...")
            val_body = json.dumps({
                "idUsuario": usuario,
                "llave": llave_hmac
            }, separators=(',', ':'))
            
            val_firma = self.sign_with_rsa(db, val_body)
            
            val_command = [
                'curl',
                '--location',
                'http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/admin/validarLlave',
                '--header', 'Content-Type: application/json',
                '--header', f'X-Runt-Id-Usuario: {usuario}',
                '--header', f'X-Runt-Firma: {val_firma}',
                '--header', 'X-Forwarded-For: 201.184.19.178',
                '--data', val_body
            ]
            
            val_process = subprocess.Popen(
                val_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            val_stdout, _ = val_process.communicate()
            val_response = val_stdout.decode().strip()
            
            if "Error" in val_response:
                return {
                    "success": False,
                    "error": "Error al validar llave HMAC",
                    "details": {"response": val_response}
                }
            
            print("Llave validada exitosamente")
            
            # Paso 3: Consultar vehículos
            vehicles_info = []
            
            for plate in plates:
                print(f"\nConsultando vehículo con placa {plate}...")
                
                query_body = json.dumps({
                    "tipoConsulta": "PLACA",
                    "noPlaca": plate.upper(),
                    "idUsuario": usuario,
                    "fecha": datetime.now().strftime("%Y-%m-%d")
                }, separators=(',', ':'))
                
                # Generar firma HMAC para la consulta
                import base64
                import hmac
                import hashlib
                
                llave_hmac_bytes = base64.b64decode(llave_hmac)
                hmac_firma = hmac.new(
                    llave_hmac_bytes,
                    query_body.encode('utf-8'),
                    hashlib.sha256
                ).digest()
                
                hmac_firma_base64 = base64.b64encode(hmac_firma).decode('utf-8')
                
                query_command = [
                    'curl',
                    '--location',
                    'http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/consulta/vehiculos',
                    '--header', 'Content-Type: application/json',
                    '--header', f'X-Runt-Id-Usuario: {usuario}',
                    '--header', f'X-Runt-Firma: {hmac_firma_base64}',
                    '--header', 'X-Forwarded-For: 201.184.19.178',
                    '--data', query_body
                ]
                
                query_process = subprocess.Popen(
                    query_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                query_stdout, query_stderr = query_process.communicate()
                query_response = query_stdout.decode().strip()
                
                try:
                    if not "Error" in query_response:
                        response_data = json.loads(query_response)
                        vehicles_info.append({
                            "plate": plate,
                            "success": True,
                            "data": response_data
                        })
                    else:
                        vehicles_info.append({
                            "plate": plate,
                            "success": False,
                            "error": "Error en consulta",
                            "details": query_response
                        })
                except Exception as e:
                    vehicles_info.append({
                        "plate": plate,
                        "success": False,
                        "error": str(e),
                        "details": query_response
                    })
                
                # Esperar un momento entre consultas para no sobrecargar el servicio
                time.sleep(1)
            
            return {
                "success": True,
                "data": {
                    "key_generation": {"llave": llave_hmac},
                    "key_validation": {"mensaje": "Llave validada exitosamente"},
                    "vehicles": vehicles_info
                }
            }
            
        except Exception as e:
            print(f"\nError en process_runt_sequence: {str(e)}")
            return {
                "success": False,
                "error": f"Error en proceso RUNT: {str(e)}"
            } 