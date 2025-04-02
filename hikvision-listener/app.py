from flask import Flask, request
import os
import json
import base64
import uuid
import xmltodict
import xml.etree.ElementTree as ET
from datetime import datetime
from email.parser import BytesParser
from email.policy import default

app = Flask(__name__)

FILE_PATH = "/eventos/eventos_consolidados.json"
XML_FOLDER = "/eventos/xmls"
IMG_FOLDER = "/eventos/imagenes"
VIDEO_FOLDER = "/eventos/videos"

os.makedirs(XML_FOLDER, exist_ok=True)
os.makedirs(IMG_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

def strip_namespace(xml):
    try:
        tree = ET.ElementTree(ET.fromstring(xml))
        root = tree.getroot()
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
        return ET.tostring(root, encoding='utf-8')
    except Exception as e:
        print(f"\u274c Error limpiando namespace: {e}")
        return xml

@app.route('/eventos', methods=['POST'])
def recibir_evento():
    try:
        content_type = request.headers.get("Content-Type")
        raw_data = request.get_data()

        msg = BytesParser(policy=default).parsebytes(
            b"Content-Type: " + content_type.encode() + b"\n\n" + raw_data
        )

        xml_dict = None
        xml_raw_original = None
        imagenes = {}
        video_bytes = None

        for part in msg.iter_parts():
            content_disposition = part.get("Content-Disposition", "")
            content_type = part.get_content_type()

            if "anpr.xml" in content_disposition:
                xml_raw_original = part.get_payload(decode=True)
                xml_clean = strip_namespace(xml_raw_original)
                xml_dict = xmltodict.parse(xml_clean)

            elif content_type == "image/jpeg":
                filename = part.get_filename()
                if filename:
                    imagenes[filename] = part.get_payload(decode=True)

            elif content_type in ["video/mp4", "application/octet-stream"]:
                video_bytes = part.get_payload(decode=True)

        if xml_dict and xml_raw_original:
            alert = xml_dict.get("EventNotificationAlert", {})
            anpr = alert.get("ANPR", {})
            vehicle_info = anpr.get("vehicleInfo", {})
            gps_info = alert.get("DeviceGPSInfo", {})

            plate = anpr.get("licensePlate", "").strip()
            if plate.lower() == "unknown":
                print("\u26a0\ufe0f Evento descartado: placa 'unknown'")
                return "OK", 200

            latitude = gps_info.get("Latitude", {}).get("degree", "")
            longitude = gps_info.get("Longitude", {}).get("degree", "")
            speed = int(vehicle_info.get("speed", 0)) if vehicle_info.get("speed") else 0

            event_id = str(uuid.uuid4())

            # Guardar XML crudo
            with open(os.path.join(XML_FOLDER, f"{event_id}.xml"), "wb") as f:
                f.write(xml_raw_original)

            # Guardar imágenes en disco y base64 para el JSON
            evidencia_base64 = {}
            for nombre, datos in imagenes.items():
                ruta_img = os.path.join(IMG_FOLDER, f"{event_id}_{nombre}")
                with open(ruta_img, "wb") as f:
                    f.write(datos)
                evidencia_base64[nombre] = base64.b64encode(datos).decode("utf-8")

            # Guardar video si llega
            video_nombre = None
            if video_bytes:
                video_nombre = f"{event_id}.mp4"
                with open(os.path.join(VIDEO_FOLDER, video_nombre), "wb") as f:
                    f.write(video_bytes)

            evento = {
                "event_id": event_id,
                "device_id": 88,
                "latitude": latitude,
                "longitude": longitude,
                "location_address": "Col",
                "plate": plate,
                "date": alert.get("dateTime", ""),
                "speed": speed,
                "comments": "Red_Light_Running",
                "infraction_code": "D04",
                "evidences": evidencia_base64,
                "video_filename": video_nombre
            }

            if os.path.exists(FILE_PATH):
                with open(FILE_PATH, "r", encoding="utf-8") as f:
                    eventos = json.load(f)
            else:
                eventos = []

            eventos.append(evento)

            with open(FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(eventos, f, indent=2, ensure_ascii=False)

            print(f"\u2705 Evento guardado: {plate} | UUID: {event_id}")

        else:
            print("\u26a0\ufe0f XML no válido o no encontrado.")

    except Exception as e:
        fallback = "/eventos/error_evento.raw"
        with open(fallback, "wb") as f:
            f.write(request.get_data())
        print(f"\u274c Error procesando evento: {e}")

    return "OK", 200

@app.route('/eventos', methods=['GET'])
def eventos_get():
    return 'Este endpoint solo acepta POST.', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080) 