# template_generator.py - Versión optimizada y profesional
import os
import base64
import uuid
import logging
from typing import Dict, Tuple, List
from jinja2 import Environment, FileSystemLoader, Template
from weasyprint import HTML
import streamlit as st
import requests

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TemplateGenerator:
    def __init__(self, template_dir: str = "templates", output_dir: str = "output/pdfs"):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_html(self, record_data: Dict) -> str:
        """Genera contenido HTML desde la plantilla y los datos del registro."""
        try:
            template: Template = self.env.get_template("report.html")
        except Exception as e:
            logger.error(f"Error cargando la plantilla: {e}")
            raise

        template_data = {
            "item": {
                "image1_base64": None,
                "image2_base64": None,
                "plate": record_data.get("plate", "unknown"),
                "infraction_data": record_data
            }
        }

        images = self._extract_base64_images(record_data)
        template_data["item"].update(images)

        return template.render(**template_data)

    def _extract_base64_images(self, data: Dict) -> Dict[str, str]:
        """Extrae y convierte a base64 las dos primeras rutas de imagen válidas."""
        result = {"image1_base64": None, "image2_base64": None}
        found = 0

        for value in data.values():
            if isinstance(value, str) and value.startswith("output/images/") and os.path.isfile(value):
                try:
                    with open(value, "rb") as img_file:
                        encoded = base64.b64encode(img_file.read()).decode("utf-8")
                        result[f"image{found + 1}_base64"] = f"data:image/png;base64,{encoded}"
                        found += 1
                        if found == 2:
                            break
                except Exception as e:
                    logger.warning(f"No se pudo procesar la imagen {value}: {e}")

        return result

    def generate_pdf(self, html_content: str, plate: str) -> Tuple[str, str]:
        """Convierte el HTML en PDF y lo guarda."""
        try:
            unique_id = str(uuid.uuid4())
            filename = f"reporte_{plate}_{unique_id}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            HTML(string=html_content).write_pdf(output_path)
            logger.info(f"PDF generado: {output_path}")
            return output_path, filename
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            raise

    def generate_pdfs_for_records(self, records: List[Dict]) -> List[Dict]:
        """Genera PDFs para una lista de registros."""
        results = []
        for record in records:
            plate = record.get("plate", "unknown")
            try:
                html = self.generate_html(record)
                path, filename = self.generate_pdf(html, plate)
                results.append({"plate": plate, "path": path, "filename": filename, "success": True})
            except Exception as e:
                logger.error(f"Error con placa {plate}: {e}")
                results.append({"plate": plate, "error": str(e), "success": False})
        return results

def show_template_editor():
    st.title("Editor de Plantillas")
    
    # Obtener plantillas existentes
    templates = get_templates()
    
    # Crear nueva plantilla o editar existente
    action = st.radio("Acción", ["Crear Nueva Plantilla", "Editar Plantilla Existente"])
    
    if action == "Editar Plantilla Existente":
        if not templates:
            st.warning("No hay plantillas disponibles para editar")
            return
            
        selected_template = st.selectbox(
            "Seleccionar Plantilla",
            templates,
            format_func=lambda x: x["name"]
        )
        
        name = st.text_input("Nombre de la Plantilla", value=selected_template["name"])
        content = st_quill(
            value=selected_template["content"],
            html=True,
            key="quill_editor"
        )
        
        # Editor de variables
        st.subheader("Variables de la Plantilla")
        st.info("Las variables se pueden usar en la plantilla usando la sintaxis {{variable}}")
        
        # Obtener variables existentes
        existing_variables = selected_template.get("variables", {})
        
        # Crear campos para editar variables existentes y agregar nuevas
        variables = {}
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("Variables Existentes")
            for var_name, var_value in existing_variables.items():
                new_value = st.text_input(f"Variable: {var_name}", value=var_value)
                variables[var_name] = new_value
        
        with col2:
            st.write("Agregar Nueva Variable")
            new_var_name = st.text_input("Nombre de la Variable")
            new_var_value = st.text_input("Valor por Defecto")
            if st.button("Agregar Variable"):
                if new_var_name:
                    variables[new_var_name] = new_var_value
                    st.success(f"Variable {new_var_name} agregada")
        
        if st.button("Guardar Cambios"):
            try:
                response = requests.put(
                    f"{RUNT_SERVICE_URL}/templates/{selected_template['id']}",
                    json={
                        "name": name,
                        "content": content,
                        "variables": variables
                    }
                )
                if response.ok:
                    st.success("Plantilla actualizada exitosamente")
                else:
                    st.error(f"Error actualizando plantilla: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                
    else:  # Crear nueva plantilla
        name = st.text_input("Nombre de la Plantilla")
        content = st_quill(
            placeholder="Contenido de la plantilla...",
            html=True,
            key="quill_editor"
        )
        
        # Editor de variables para nueva plantilla
        st.subheader("Variables de la Plantilla")
        st.info("Las variables se pueden usar en la plantilla usando la sintaxis {{variable}}")
        
        variables = {}
        new_var_name = st.text_input("Nombre de la Variable")
        new_var_value = st.text_input("Valor por Defecto")
        if st.button("Agregar Variable"):
            if new_var_name:
                variables[new_var_name] = new_var_value
                st.success(f"Variable {new_var_name} agregada")
        
        if st.button("Crear Plantilla"):
            if name and content:
                try:
                    response = requests.post(
                        f"{RUNT_SERVICE_URL}/templates",
                        json={
                            "name": name,
                            "content": content,
                            "variables": variables
                        }
                    )
                    if response.ok:
                        st.success("Plantilla creada exitosamente")
                    else:
                        st.error(f"Error creando plantilla: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Por favor complete todos los campos")
