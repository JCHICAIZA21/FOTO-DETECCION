# frontend.py optimizado y mejorado visualmente en un solo archivo
import streamlit as st
import requests
import os
import re
import json
from bs4 import BeautifulSoup
from streamlit_quill import st_quill
import time
from datetime import datetime

# Constantes de entorno
RUNT_SERVICE_URL = os.getenv('RUNT_SERVICE_URL', 'http://runt-service:8002')
API_CONSUMER_URL = os.getenv('API_CONSUMER_URL', 'http://api-consumer:8000')

# Agregar después de la inicialización de la sesión
if 'logs' not in st.session_state:
    st.session_state.logs = []

def add_log(message):
    """Agrega un mensaje al log con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")
    # Mantener solo los últimos 100 logs
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]

def main():
    st.set_page_config(page_title="Panel Administrativo", layout="wide")
    st.sidebar.title("📂 Menú Principal")
    option = st.sidebar.radio("Seleccione una opción", [
        "🔐 Variables Globales",
        "🔀 Configuración de Atributos",
        "📂 Procesar JSON",
        "📄 Generar PDF",
        "🚗 RUNT API",
        "📃 Editor de Plantillas"
    ])

    views = {
        "🔐 Variables Globales": show_global_vars,
        "🔀 Configuración de Atributos": show_attributes_config,
        "📂 Procesar JSON": show_json_processor,
        "📄 Generar PDF": show_pdf_generator,
        "🚗 RUNT API": show_runt_api,
        "📃 Editor de Plantillas": show_template_editor
    }
    views[option]()

def show_attributes_config():
    st.title("Configuración de Atributos")
    name = st.text_input("Nombre del Atributo", key="attr_name")
    type = st.selectbox("Tipo", ["image", "video", "text"], key="attr_type")
    if st.button("Guardar Atributo", key="btn_save_attr"):
        res = requests.post(f"{API_CONSUMER_URL}/attributes/", params={"name": name, "type": type})
        st.success("Atributo guardado")
    st.markdown("---")
    st.subheader("Atributos Registrados")
    res = requests.get(f"{API_CONSUMER_URL}/attributes/")
    if res.status_code == 200:
        for i, attr in enumerate(res.json()):
            st.write(f"- **{attr['name']}** ({attr['type']})")


def show_json_processor():
    st.title("Procesar JSON")
    
    # Inicialización del estado
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'last_process_time' not in st.session_state:
        st.session_state.last_process_time = 0
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'last_check' not in st.session_state:
        st.session_state.last_check = 0
    
    # Contenedor principal
    st.markdown("### 📋 Logs del Sistema")
    
    # Verificar actualizaciones de logs cada 2 segundos
    current_time = time.time()
    if current_time - st.session_state.last_check > 2:
        try:
            # Primero verificar la salud del servicio
            health_response = requests.get(f"{API_CONSUMER_URL}/health", timeout=5)
            if health_response.status_code == 200:
                health_data = health_response.json()
                if not health_data.get("monitoring_active"):
                    st.warning("El monitoreo automático no está activo")
                
                # Obtener el último proceso
                last_process = health_data.get("last_process", {})
                if last_process:
                    timestamp = datetime.fromtimestamp(last_process["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                    log_message = f"[{timestamp}] {last_process['message']} (Fuente: {last_process['source']})"
                    
                    # Solo agregar si es un mensaje nuevo
                    if log_message not in st.session_state.logs:
                        st.session_state.logs.append(log_message)
                        # Mantener solo los últimos 100 logs
                        if len(st.session_state.logs) > 100:
                            st.session_state.logs = st.session_state.logs[-100:]
            else:
                st.error(f"Error al verificar la salud del servicio: {health_response.status_code} - {health_response.text}")
        except requests.exceptions.Timeout:
            st.error("Tiempo de espera agotado al obtener logs")
        except requests.exceptions.ConnectionError:
            st.error("Error de conexión al obtener logs")
        except Exception as e:
            st.error(f"Error al obtener logs: {str(e)}")
        
        st.session_state.last_check = current_time
    
    # Mostrar logs en una tabla con scroll
    if st.session_state.logs:
        st.markdown("""
            <style>
            .stTable {
                max-height: 400px;
                overflow-y: auto;
            }
            </style>
        """, unsafe_allow_html=True)
        st.table([{"Timestamp": log.split("]")[0].strip("["), 
                  "Mensaje": log.split("]")[1].strip()} 
                 for log in st.session_state.logs])
    else:
        st.info("No hay logs disponibles")
    
    # Botones en una fila
    col1, col2 = st.columns(2)
    
    with col1:
        # Verificar si hay un proceso en ejecución o si el último proceso fue hace menos de 5 segundos
        current_time = time.time()
        can_process = not st.session_state.processing and (current_time - st.session_state.last_process_time) > 5
        
        if st.button("🔄 Ejecutar Proceso", disabled=not can_process):
            if can_process:
                st.session_state.processing = True
                st.session_state.last_process_time = current_time
                
                try:
                    with st.spinner("Procesando..."):
                        response = requests.post(f"{API_CONSUMER_URL}/process", timeout=30)
                        
                        if response.status_code == 200:
                            data = response.json()
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            log_message = f"[{timestamp}] Proceso ejecutado: {data.get('message', 'N/A')}"
                            st.session_state.logs.append(log_message)
                            st.success(data.get('message', 'Proceso ejecutado correctamente'))
                        else:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            error_message = f"[{timestamp}] Error: {response.text}"
                            st.session_state.logs.append(error_message)
                            st.error(f"Error al ejecutar el proceso: {response.text}")
                except requests.Timeout:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    error_message = f"[{timestamp}] Error: Tiempo de espera agotado"
                    st.session_state.logs.append(error_message)
                    st.error("El proceso tardó demasiado tiempo en completarse")
                except requests.exceptions.ConnectionError:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    error_message = f"[{timestamp}] Error: Error de conexión"
                    st.session_state.logs.append(error_message)
                    st.error("Error de conexión al ejecutar el proceso")
                except Exception as e:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    error_message = f"[{timestamp}] Error: {str(e)}"
                    st.session_state.logs.append(error_message)
                    st.error(f"Error al ejecutar el proceso: {str(e)}")
                finally:
                    st.session_state.processing = False
            else:
                if st.session_state.processing:
                    st.warning("Ya hay un proceso en ejecución. Por favor espere.")
                else:
                    st.warning("Por favor espere unos segundos antes de intentar nuevamente.")


def show_pdf_generator():
    st.title("Generador de PDFs")
    
    # Inicializar el estado si no existe
    if 'generated_pdfs' not in st.session_state:
        st.session_state.generated_pdfs = []
    
    # Obtener plantillas
    templates = get_templates()
    if not templates:
        st.warning("No hay plantillas disponibles")
        return

    # Seleccionar plantilla
    selected_template = st.selectbox(
        "Seleccionar Plantilla",
        templates,
        format_func=lambda x: x["name"]
    )

    # Obtener placas disponibles
    try:
        response = requests.get(f"{RUNT_SERVICE_URL}/get-plate")
        if response.ok:
            data = response.json()
            if data.get("success"):
                plates = data.get("plates", [])
                if plates:
                    # Modo de generación
                    mode = st.radio("Modo de generación", ["Individual", "Masivo"])
                    
                    if mode == "Individual":
                        selected_plate = st.selectbox("Seleccionar Placa", plates)
                        plates_to_process = [selected_plate]
                    else:
                        plates_to_process = st.multiselect("Seleccionar Placas", plates)

                    if st.button("Generar PDF(s)"):
                        with st.spinner("Generando PDF(s)..."):
                            generated_pdfs = []
                            for plate in plates_to_process:
                                try:
                                    # Preparar los datos para la solicitud
                                    request_data = {
                                        "template_id": selected_template["id"],
                                        "plate": plate,
                                        "output_filename": f"reporte_{plate}.pdf"
                                    }
                                    
                                    # Realizar la solicitud al servicio RUNT
                                    response = requests.post(
                                        f"{RUNT_SERVICE_URL}/generate-pdf",
                                        json=request_data
                                    )
                                    
                                    if response.ok:
                                        pdf_data = response.content
                                        generated_pdfs.append({
                                            "plate": plate,
                                            "data": pdf_data,
                                            "filename": f"reporte_{plate}.pdf"
                                        })
                                        st.success(f"PDF generado para placa {plate}")
                                    else:
                                        st.error(f"Error generando PDF para placa {plate}: {response.text}")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                            
                            # Guardar los PDFs generados en el estado de la sesión
                            st.session_state.generated_pdfs = generated_pdfs

                    # Mostrar opciones de descarga
                    if st.session_state.generated_pdfs:
                        st.subheader("Descargar PDFs")
                        
                        # Opción para descargar individualmente
                        for pdf in st.session_state.generated_pdfs:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"PDF para placa: {pdf['plate']}")
                            with col2:
                                st.download_button(
                                    f"⬇️ Descargar",
                                    pdf["data"],
                                    pdf["filename"],
                                    "application/pdf"
                                )
                        
                        # Opción para descargar todos en ZIP
                        if len(st.session_state.generated_pdfs) > 1:
                            import io
                            import zipfile
                            
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for pdf in st.session_state.generated_pdfs:
                                    zip_file.writestr(pdf["filename"], pdf["data"])
                            
                            st.download_button(
                                "⬇️ Descargar todos los PDFs (ZIP)",
                                zip_buffer.getvalue(),
                                "reportes.zip",
                                "application/zip"
                            )
                else:
                    st.warning("No hay placas disponibles")
            else:
                st.error("Error obteniendo placas")
        else:
            st.error(f"Error al obtener placas: {response.text}")
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_runt_api():
    st.title("Consulta RUNT API")
    if st.button("Ver Variables del Servicio"):
        show_response(f"{RUNT_SERVICE_URL}/variables")

    if st.button("Consultar Vehículo por Placa"):
        try:
            plate_response = requests.get(f"{RUNT_SERVICE_URL}/get-plate").json()
            if plate_response.get("success"):
                # Manejar tanto 'plate' como 'plates'
                plate = plate_response.get("plate") or (plate_response.get("plates", []) and plate_response["plates"][0])
                if plate:
                    st.info(f"Consultando info de la placa: {plate}")
                    response = requests.post(f"{RUNT_SERVICE_URL}/process-runt", json={"plate": plate})
                    show_json_response(response)
                else:
                    st.error("No se encontró ninguna placa")
            else:
                st.error("No se pudo obtener la placa")
                st.json(plate_response)
        except Exception as e:
            st.error(f"Error en la consulta: {str(e)}")

def show_global_vars():
    st.title("Variables Globales")
    try:
        res = requests.get(f"{RUNT_SERVICE_URL}/variables")
        if res.ok:
            for i, var in enumerate(res.json()):
                name = var['name']
                value = st.text_input(name, var['value'], key=f"var_input_{i}")
                if st.button(f"Actualizar {name}", key=f"btn_update_{i}"):
                    updated = requests.put(f"{RUNT_SERVICE_URL}/variables/{name}", json={"value": value})
                    st.success("Actualizado")

            st.markdown("---")
            st.subheader("Agregar Nueva Variable")
            new_name = st.text_input("Nombre", key="new_var_name")
            new_value = st.text_input("Valor", key="new_var_value")
            new_desc = st.text_area("Descripción", key="new_var_desc")
            if st.button("Agregar Variable", key="btn_add_var"):
                r = requests.post(f"{RUNT_SERVICE_URL}/variables", json={"name": new_name, "value": new_value, "description": new_desc})
                st.success("Variable agregada") if r.ok else st.error("Error al agregar")
    except Exception as e:
        st.error(f"Error cargando variables: {str(e)}")

def show_template_editor():
    st.title("Editor de Plantillas")
    
    # Inicializar variables de estado
    if 'templates' not in st.session_state:
        st.session_state.templates = []
    if 'current_template' not in st.session_state:
        st.session_state.current_template = None
    if 'editing' not in st.session_state:
        st.session_state.editing = False
    if 'available_variables' not in st.session_state:
        st.session_state.available_variables = []
    if 'editor_content' not in st.session_state:
        st.session_state.editor_content = ""
    
    # Cargar plantillas existentes
    try:
        response = requests.get(f"{RUNT_SERVICE_URL}/templates")
        if response.status_code == 200:
            st.session_state.templates = response.json()
    except Exception as e:
        st.error(f"Error al cargar plantillas: {str(e)}")
        return

    # Cargar variables disponibles
    try:
        response = requests.get(f"{RUNT_SERVICE_URL}/template-variables")
        if response.status_code == 200:
            st.session_state.available_variables = response.json()
    except Exception as e:
        st.error(f"Error al cargar variables: {str(e)}")
        return

    # Panel izquierdo para lista de plantillas y variables
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Plantillas Existentes")
        for template in st.session_state.templates:
            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
            with col_btn1:
                if st.button(f"📄 {template['name']}", key=f"template_{template['id']}"):
                    st.session_state.current_template = template
                    st.session_state.editing = True
                    st.session_state.editor_content = template.get('content', '')
            with col_btn2:
                if st.button("✏️", key=f"edit_{template['id']}"):
                    st.session_state.current_template = template
                    st.session_state.editing = True
                    st.session_state.editor_content = template.get('content', '')
            with col_btn3:
                if st.button("🗑️", key=f"delete_{template['id']}"):
                    if st.session_state.current_template and st.session_state.current_template['id'] == template['id']:
                        st.session_state.current_template = None
                        st.session_state.editing = False
                        st.session_state.editor_content = ""
                    try:
                        response = requests.delete(f"{RUNT_SERVICE_URL}/templates/{template['id']}")
                        if response.status_code == 200:
                            st.success(f"Plantilla '{template['name']}' eliminada")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar plantilla: {str(e)}")

        st.markdown("---")
        st.subheader("Variables Disponibles")
        for category, vars in st.session_state.available_variables.items():
            with st.expander(category):
                for var in vars:
                    if st.button(f"📎 {var}", key=f"var_{category}_{var}"):
                        # Insertar variable en el editor
                        if st.session_state.editing:
                            var_placeholder = f"{{{{ {category}.{var} }}}}"
                            st.session_state.editor_content += var_placeholder
                            st.rerun()

    # Panel derecho para editor
    with col2:
        st.subheader("Editor de Plantilla")
        if st.session_state.editing and st.session_state.current_template:
            template_name = st.text_input("Nombre de la Plantilla", 
                                        value=st.session_state.current_template.get('name', ''),
                                        key="template_name")
            
            # Editor de contenido
            content = st_quill(
                value=st.session_state.editor_content,
                key="template_content",
                html=True
            )
            
            # Actualizar el contenido en el estado
            st.session_state.editor_content = content
            
            # Guardar cambios
            if st.button("💾 Guardar Cambios"):
                # Verificar si existe una plantilla con el mismo nombre
                name_exists = any(t['name'] == template_name and t['id'] != st.session_state.current_template['id'] 
                                for t in st.session_state.templates)
                
                if name_exists:
                    st.error(f"Ya existe una plantilla con el nombre '{template_name}'")
                else:
                    try:
                        template_data = {
                            "name": template_name,
                            "content": content
                        }
                        
                        if st.session_state.current_template.get('id'):
                            # Actualizar plantilla existente
                            response = requests.put(
                                f"{RUNT_SERVICE_URL}/templates/{st.session_state.current_template['id']}", 
                                json=template_data
                            )
                        else:
                            # Crear nueva plantilla
                            response = requests.post(
                                f"{RUNT_SERVICE_URL}/templates", 
                                json=template_data
                            )
                            
                        if response.status_code in [200, 201]:
                            st.success("Plantilla guardada exitosamente")
                            st.session_state.editing = False
                            st.session_state.current_template = None
                            st.session_state.editor_content = ""
                            st.rerun()
                        else:
                            st.error(f"Error al guardar la plantilla: {response.text}")
                    except Exception as e:
                        st.error(f"Error al guardar la plantilla: {str(e)}")
        else:
            # Formulario para nueva plantilla
            st.markdown("### Nueva Plantilla")
            template_name = st.text_input("Nombre de la Plantilla", key="new_template_name")
            content = st_quill(
                value=st.session_state.editor_content,
                key="new_template_content",
                html=True
            )
            
            # Actualizar el contenido en el estado
            st.session_state.editor_content = content
            
            if st.button("➕ Crear Nueva Plantilla"):
                # Verificar si ya existe una plantilla con el mismo nombre
                name_exists = any(t['name'] == template_name for t in st.session_state.templates)
                
                if name_exists:
                    st.error(f"Ya existe una plantilla con el nombre '{template_name}'")
                else:
                    try:
                        template_data = {
                            "name": template_name,
                            "content": content
                        }
                        response = requests.post(f"{RUNT_SERVICE_URL}/templates", json=template_data)
                        
                        if response.status_code == 201:
                            st.success("Plantilla creada exitosamente")
                            st.session_state.editor_content = ""
                            st.rerun()
                        else:
                            st.error(f"Error al crear la plantilla: {response.text}")
                    except Exception as e:
                        st.error(f"Error al crear la plantilla: {str(e)}")

    # JavaScript para manejar la posición del cursor
    st.markdown("""
        <script>
        const editor = document.querySelector('.quill-editor');
        if (editor) {
            editor.addEventListener('click', function(e) {
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    const cursorPosition = range.startOffset;
                    window.parent.postMessage({
                        type: 'cursor_position',
                        position: cursorPosition
                    }, '*');
                }
            });
        }
        </script>
    """, unsafe_allow_html=True)

# ------------------------
# Funciones Auxiliares
# ------------------------

def get_templates():
    try:
        return requests.get(f"{RUNT_SERVICE_URL}/templates").json()
    except: return []

def get_available_plates():
    try:
        return requests.get(f"{API_CONSUMER_URL}/available-plates").json()
    except: return []

def generate_pdf(data):
    return requests.post(f"{API_CONSUMER_URL}/generate-pdf", json=data).json()

def generate_pdfs_bulk(payload):
    return requests.post(f"{API_CONSUMER_URL}/generate-pdfs", json=payload).json()

def show_response(url):
    try:
        r = requests.get(url)
        if r.ok:
            st.json(r.json())
        else:
            st.error(r.text)
    except Exception as e:
        st.error(f"Error: {str(e)}")

def show_json_response(response):
    try:
        res = response.json()
        if res.get("success"):
            st.json(res)
        else:
            st.error(res.get("error"))
    except Exception as e:
        st.error(f"Error procesando respuesta: {str(e)}")

if __name__ == "__main__":
    main()
