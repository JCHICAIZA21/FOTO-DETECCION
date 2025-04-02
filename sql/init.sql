-- Eliminar la línea que crea la base de datos
-- CREATE DATABASE json_processor;

\c json_processor;

-- Eliminar tablas si existen (para evitar conflictos)
DROP TABLE IF EXISTS user_roles CASCADE;
DROP TABLE IF EXISTS role_permissions CASCADE;
DROP TABLE IF EXISTS permissions CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS global_variables CASCADE;
DROP TABLE IF EXISTS api_endpoints CASCADE;
DROP TABLE IF EXISTS attributes CASCADE;
DROP TABLE IF EXISTS vehicle_info CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS vehicle_owners CASCADE;
DROP TABLE IF EXISTS vehicle_owner_addresses CASCADE;
DROP TABLE IF EXISTS vehicle_soat CASCADE;
DROP TABLE IF EXISTS vehicle_rtm CASCADE;
DROP TABLE IF EXISTS vehicle_civil_policies CASCADE;
DROP TABLE IF EXISTS policy_details CASCADE;
DROP TABLE IF EXISTS pdf_templates CASCADE;
DROP TABLE IF EXISTS generated_pdfs CASCADE;

-- Crear las tablas necesarias
CREATE TABLE IF NOT EXISTS attributes (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    type VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS global_variables (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    value TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS api_endpoints (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    url TEXT NOT NULL,
    method VARCHAR NOT NULL,
    headers JSONB,
    description TEXT
);

-- Crear tablas para templates PDF
CREATE TABLE IF NOT EXISTS pdf_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pdf_variables (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES pdf_templates(id),
    name VARCHAR NOT NULL,
    default_value TEXT,
    description TEXT
);

-- Crear tablas para usuarios y roles
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL UNIQUE,
    email VARCHAR NOT NULL UNIQUE,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role_id INTEGER REFERENCES roles(id)
);

CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER REFERENCES roles(id),
    permission_id INTEGER REFERENCES permissions(id)
);

-- Tablas para almacenar información de vehículos RUNT
CREATE TABLE IF NOT EXISTS vehicle_info (
    id SERIAL PRIMARY KEY,
    plate VARCHAR NOT NULL UNIQUE,
    no_registro VARCHAR,
    no_licencia_transito VARCHAR,
    fecha_expedicion_lic_transito DATE,
    estado_vehiculo VARCHAR,
    tipo_servicio VARCHAR,
    clase_vehiculo VARCHAR,
    marca VARCHAR,
    linea VARCHAR,
    modelo VARCHAR,
    color VARCHAR,
    no_serie VARCHAR,
    no_motor VARCHAR,
    no_chasis VARCHAR,
    no_vin VARCHAR,
    cilindraje VARCHAR,
    tipo_carroceria VARCHAR,
    fecha_matricula DATE,
    tiene_gravamenes BOOLEAN,
    organismo_transito VARCHAR,
    prendas BOOLEAN,
    prendario VARCHAR,
    clasificacion VARCHAR,
    capacidad_carga VARCHAR,
    peso_bruto_vehicular VARCHAR,
    no_ejes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla para almacenar eventos de detección
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicle_info(id) ON DELETE CASCADE,
    event_id VARCHAR,
    device_id VARCHAR,
    date TIMESTAMP,
    evidences JSONB,
    video_filename VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vehicle_owners (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicle_info(id),
    tipo_documento VARCHAR,
    numero_documento VARCHAR,
    nombre_completo VARCHAR,
    primer_nombre VARCHAR,
    segundo_nombre VARCHAR,
    primer_apellido VARCHAR,
    segundo_apellido VARCHAR,
    tipo_propiedad INTEGER,
    detalle_propiedad VARCHAR,
    fecha_nacimiento DATE,
    fecha_inicio_propiedad DATE,
    fecha_fin_propiedad DATE,
    is_current BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS vehicle_owner_addresses (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER REFERENCES vehicle_owners(id),
    direccion VARCHAR,
    departamento VARCHAR,
    ciudad VARCHAR,
    telefono VARCHAR,
    celular VARCHAR,
    email VARCHAR
);

CREATE TABLE IF NOT EXISTS vehicle_soat (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicle_info(id),
    no_poliza VARCHAR,
    fecha_expedicion DATE,
    fecha_vigencia DATE,
    fecha_vencimiento DATE,
    nit_entidad VARCHAR,
    entidad_expide VARCHAR,
    estado VARCHAR
);

CREATE TABLE IF NOT EXISTS vehicle_rtm (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicle_info(id),
    nro_rtm VARCHAR,
    tipo_revision VARCHAR,
    fecha_expedicion DATE,
    fecha_vigente DATE,
    cda_expide VARCHAR,
    vigente BOOLEAN
);

CREATE TABLE IF NOT EXISTS vehicle_civil_policies (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicle_info(id),
    numero_poliza VARCHAR,
    fecha_expedicion DATE,
    fecha_vigencia DATE,
    tipo_documento VARCHAR,
    numero_documento VARCHAR,
    nombre_aseguradora VARCHAR,
    tipo_poliza VARCHAR,
    fecha_inicio DATE,
    estado_poliza VARCHAR
);

CREATE TABLE IF NOT EXISTS policy_details (
    id SERIAL PRIMARY KEY,
    policy_id INTEGER REFERENCES vehicle_civil_policies(id),
    nro_poliza VARCHAR,
    tipo_doc_tomador VARCHAR,
    nro_doc_tomador VARCHAR,
    cobertura VARCHAR,
    monto DECIMAL
);

-- Tabla para almacenar los PDFs generados
CREATE TABLE IF NOT EXISTS generated_pdfs (
    id SERIAL PRIMARY KEY,
    vehicle_id INTEGER REFERENCES vehicle_info(id),
    template_id INTEGER REFERENCES pdf_templates(id),
    pdf_path VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar datos iniciales necesarios
INSERT INTO global_variables (name, value, description) 
VALUES 
    ('usuarioAseguradoraCliente', '900133384', 'Usuario aseguradora'),
    ('llavehmaccliente', '', 'Llave HMAC generada por el servicio')
ON CONFLICT (name) DO NOTHING;

-- Insertar endpoint
INSERT INTO api_endpoints (name, url, method, headers, description) VALUES
    ('generarLlave', 
    'http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/admin/generarLlave',
    'POST',
    '{
        "Content-Type": "application/json"
    }',
    'Endpoint para generar llave'
) ON CONFLICT (name) DO NOTHING;

-- Actualizar el endpoint con la URL correcta
UPDATE api_endpoints 
SET url = 'http://10.1.0.4:8080/servicios/runt/api/consultaAseguradora/admin/generarLlave'
WHERE name = 'generarLlave';

-- Insertar usuario administrador
INSERT INTO users (username, email, hashed_password) 
VALUES ('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewqxbQb4fxD8AdXC');

-- Insertar rol administrador
INSERT INTO roles (name, description)
VALUES ('admin', 'Administrador del sistema con acceso completo');

-- Asignar rol admin al usuario admin
INSERT INTO user_roles (user_id, role_id)
VALUES (1, 1);
