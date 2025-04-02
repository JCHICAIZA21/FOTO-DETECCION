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
import logging

class RuntService:
    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.base_url = os.getenv("RUNT_API_URL", "https://www.runt.com.co/consultaCiudadana/")
        self.hmac_key = os.getenv("HMAC_KEY", "your_hmac_key_here")
        self.private_key_path = os.getenv("PRIVATE_KEY_PATH", "claveprivada.pkcs8.pem")
        self.certificate_path = os.getenv("CERTIFICATE_PATH", "certificado.pem")
        self.client_id = os.getenv("CLIENT_ID", "900133384")
        self.client_secret = os.getenv("CLIENT_SECRET", "900133384")
        self.token = None
        self.token_expires_at = None

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
        """Genera una nueva llave HMAC."""
        try:
            # Obtener credenciales
            usuario = self.get_global_var(db, "usuarioAseguradoraCliente")
            if not usuario:
                return {
                    "success": False,
                    "error": "No se encontró el usuario configurado"
                }

            # Preparar datos
            body = json.dumps({"idUsuario": usuario}, separators=(',', ':'))
            firma = self.sign_with_rsa(db, body)

            # URL del servicio
            url = "http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/admin/generarLlave"

            # Headers
            headers = {
                'Content-Type': 'application/json',
                'X-Runt-Id-Usuario': usuario,
                'X-Runt-Firma': firma,
                'X-Forwarded-For': '201.184.19.178'
            }

            # Realizar la petición
            response = requests.post(url, headers=headers, data=body)

            if response.status_code == 200:
                llave = response.text.strip()
                
                # Actualizar la llave en la base de datos
                crud.update_global_variable(
                    db,
                    "llavehmaccliente",
                    llave,
                    "Llave HMAC generada por el servicio"
                )

                return {
                    "success": True,
                    "data": {
                        "llave": llave,
                        "mensaje": "Llave HMAC generada y almacenada exitosamente"
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Error generando llave HMAC",
                    "details": {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error generando llave HMAC: {str(e)}"
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
        """Valida la llave HMAC actual."""
        try:
            # Obtener la llave HMAC actual
            llave_hmac = self.get_global_var(db, "llavehmaccliente")
            if not llave_hmac:
                return {
                    "success": False,
                    "error": "No hay llave HMAC almacenada"
                }

            # Obtener credenciales
            usuario = self.get_global_var(db, "usuarioAseguradoraCliente")
            if not usuario:
                return {
                    "success": False,
                    "error": "No se encontró el usuario configurado"
                }

            # Preparar datos para la validación
            body = json.dumps({"idUsuario": usuario}, separators=(',', ':'))
            firma = self.sign_with_rsa(db, body)

            # URL del servicio de validación
            url = "http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/admin/validarLlave"

            # Generar HMAC
            timestamp = str(int(time.time()))
            message = f"{usuario}{timestamp}"
            hmac_signature = hmac.new(
                llave_hmac.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            # Headers
            headers = {
                'Content-Type': 'application/json',
                'X-Runt-Id-Usuario': usuario,
                'X-Runt-Firma': firma,
                'X-Runt-Timestamp': timestamp,
                'X-Runt-Signature': hmac_signature,
                'X-Forwarded-For': '201.184.19.178'
            }

            # Realizar la petición
            response = requests.post(url, headers=headers, data=body)

            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Llave HMAC válida"
                }
            else:
                return {
                    "success": False,
                    "error": "Llave HMAC inválida",
                    "details": {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error validando llave HMAC: {str(e)}"
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
                
                # Corregir el formato del body según la documentación del servicio
                query_body = json.dumps({
                    "tipoConsulta": "PLACA",
                    "noPlaca": plate.upper(),
                    "idUsuario": usuario,
                    "tipoVehiculo": "VEHICULO",  # Cambiado de "AUTOMOVIL" a "VEHICULO"
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
                
                print(f"Respuesta del servicio RUNT para placa {plate}: {query_response}")
                
                try:
                    if not "Error" in query_response:
                        response_data = json.loads(query_response)
                        print(f"Datos parseados para placa {plate}: {json.dumps(response_data, indent=2)}")
                        
                        # Verificar si la respuesta tiene la estructura esperada
                        if isinstance(response_data, dict):
                            if "vehiculo" in response_data:
                                vehicles_info.append({
                                    "plate": plate,
                                    "success": True,
                                    "data": response_data["vehiculo"]
                                })
                            elif "vehiculos" in response_data and response_data["vehiculos"]:
                                vehicles_info.append({
                                    "plate": plate,
                                    "success": True,
                                    "data": response_data["vehiculos"][0]
                                })
                            else:
                                vehicles_info.append({
                                    "plate": plate,
                                    "success": True,
                                    "data": response_data
                                })
                        else:
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
                    print(f"Error procesando respuesta para placa {plate}: {str(e)}")
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
                    "vehicles": vehicles_info
                }
            }
            
        except Exception as e:
            print(f"\nError en process_runt_sequence: {str(e)}")
            return {
                "success": False,
                "error": f"Error en proceso RUNT: {str(e)}"
            }

    async def process_plate(self, plate: str) -> Dict:
        """
        Procesa una placa individual y retorna la información del vehículo
        """
        try:
            # Obtener token si es necesario
            if not self.token or self.token_expires_at < datetime.now():
                self.token = await self.get_token()
            
            # Obtener información del vehículo
            vehicle_data = await self.get_vehicle_info(plate)
            
            # Obtener información del propietario
            owner_data = await self.get_owner_info(plate)
            
            # Obtener información del SOAT
            soat_data = await self.get_soat_info(plate)
            
            # Obtener información de la RTM
            rtm_data = await self.get_rtm_info(plate)
            
            # Combinar toda la información
            result = {
                "plate": plate,
                "vehicle": vehicle_data,
                "owner": owner_data,
                "soat": soat_data,
                "rtm": rtm_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Guardar en la base de datos
            await self.save_to_database(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error procesando placa {plate}: {str(e)}")
            raise

    async def save_to_database(self, data: Dict):
        """
        Guarda la información del vehículo en la base de datos
        """
        try:
            # Crear o actualizar vehículo
            vehicle = crud.create_or_update_vehicle(
                self.db,
                plate=data["plate"],
                vehicle_data=data["vehicle"],
                owner_data=data["owner"],
                soat_data=data["soat"],
                rtm_data=data["rtm"]
            )
            
            # Crear evento
            event = crud.create_event(
                self.db,
                plate=data["plate"],
                event_type="RUNT_QUERY",
                event_data=data
            )
            
            self.logger.info(f"Datos guardados para placa {data['plate']}")
            
        except Exception as e:
            self.logger.error(f"Error guardando datos en la base de datos: {str(e)}")
            raise 