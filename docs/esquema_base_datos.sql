-- =====================================================
-- ESQUEMA DE BASE DE DATOS
-- Sistema de Gestión de Mitigación de Accidentes
-- =====================================================
--
-- Origen del núcleo de dominio: alineado con Inicialesquema_base_datos.sql
-- (incidentes, víctimas, catálogos, vistas). Tras la sección de dominio se
-- añaden tablas compatibles con Django (auth, sesiones, migraciones) y el
-- modelo de rol/perfil de aplicación.
--
-- =====================================================

-- Tablas Catálogo
-- =====================================================

-- Tabla: SEXO
CREATE TABLE sexo (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) UNIQUE NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: GRUPO_EDAD
CREATE TABLE grupo_edad (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    edad_minima INTEGER NOT NULL,
    edad_maxima INTEGER,
    orden INTEGER NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: CONDICION
CREATE TABLE condicion (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: GRAVEDAD_VICTIMA
CREATE TABLE gravedad_victima (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(50) NOT NULL,
    descripcion TEXT,
    orden INTEGER NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: CLASE_INCIDENTE
CREATE TABLE clase_incidente (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: COMUNA
CREATE TABLE comuna (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: BARRIO
CREATE TABLE barrio (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    comuna_id INTEGER REFERENCES comuna(id),
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: VIA
CREATE TABLE via (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    tipo_via VARCHAR(50), -- Carrera, Calle, Avenida, Diagonal, Transversal, etc.
    numero_via VARCHAR(50), -- Número o nombre de la vía
    comuna_id INTEGER REFERENCES comuna(id),
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: PUNTO_CRITICO
CREATE TABLE punto_critico (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    latitud DECIMAL(10, 8) NOT NULL,
    longitud DECIMAL(11, 8) NOT NULL,
    radio_metros INTEGER DEFAULT 50, -- Radio en metros para agrupar incidentes
    via_id INTEGER REFERENCES via(id),
    comuna_id INTEGER REFERENCES comuna(id),
    barrio_id INTEGER REFERENCES barrio(id),
    prioridad INTEGER DEFAULT 3, -- 1=Alta, 2=Media, 3=Baja
    tipo_punto VARCHAR(100), -- Intersección, Cruce, Curva, Paso peatonal, etc.
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tablas Principales
-- =====================================================

-- Tabla: INCIDENTE
CREATE TABLE incidente (
    id SERIAL PRIMARY KEY,
    radicado VARCHAR(50) UNIQUE NOT NULL,
    fecha_incidente DATE NOT NULL,
    hora_incidente TIME NOT NULL,
    fecha_hora_incidente TIMESTAMP NOT NULL,
    clase_incidente_id INTEGER REFERENCES clase_incidente(id),
    direccion_incidente VARCHAR(255), -- Dirección original del texto
    via_id INTEGER REFERENCES via(id), -- Vía normalizada
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8),
    comuna_id INTEGER REFERENCES comuna(id),
    barrio_id INTEGER REFERENCES barrio(id),
    punto_critico_id INTEGER REFERENCES punto_critico(id), -- Punto crítico asignado (opcional)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: VICTIMA
CREATE TABLE victima (
    id SERIAL PRIMARY KEY,
    incidente_id INTEGER NOT NULL REFERENCES incidente(id) ON DELETE CASCADE,
    sexo_id INTEGER REFERENCES sexo(id),
    edad INTEGER,
    grupo_edad_id INTEGER REFERENCES grupo_edad(id),
    condicion_id INTEGER REFERENCES condicion(id),
    gravedad_victima_id INTEGER REFERENCES gravedad_victima(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para Optimización
-- =====================================================

-- Índices en INCIDENTE
CREATE INDEX idx_incidente_fecha ON incidente(fecha_incidente);
CREATE INDEX idx_incidente_fecha_hora ON incidente(fecha_hora_incidente);
CREATE INDEX idx_incidente_comuna ON incidente(comuna_id);
CREATE INDEX idx_incidente_barrio ON incidente(barrio_id);
CREATE INDEX idx_incidente_clase ON incidente(clase_incidente_id);
CREATE INDEX idx_incidente_radicado ON incidente(radicado);
CREATE INDEX idx_incidente_via ON incidente(via_id);
CREATE INDEX idx_incidente_punto_critico ON incidente(punto_critico_id);
CREATE INDEX idx_incidente_direccion ON incidente(direccion_incidente);

-- Índice espacial para consultas geográficas (PostgreSQL con PostGIS)
-- CREATE INDEX idx_incidente_geografico ON incidente USING GIST (ST_MakePoint(longitud, latitud));

-- Índices en VICTIMA
CREATE INDEX idx_victima_incidente ON victima(incidente_id);
CREATE INDEX idx_victima_sexo ON victima(sexo_id);
CREATE INDEX idx_victima_gravedad ON victima(gravedad_victima_id);
CREATE INDEX idx_victima_condicion ON victima(condicion_id);
CREATE INDEX idx_victima_grupo_edad ON victima(grupo_edad_id);

-- Índices en BARRIO
CREATE INDEX idx_barrio_comuna ON barrio(comuna_id);

-- Índices en VIA
CREATE INDEX idx_via_comuna ON via(comuna_id);
CREATE INDEX idx_via_nombre ON via(nombre);

-- Índices en PUNTO_CRITICO
CREATE INDEX idx_punto_critico_via ON punto_critico(via_id);
CREATE INDEX idx_punto_critico_comuna ON punto_critico(comuna_id);
CREATE INDEX idx_punto_critico_barrio ON punto_critico(barrio_id);
CREATE INDEX idx_punto_critico_prioridad ON punto_critico(prioridad);

-- Datos Iniciales (Catálogos)
-- =====================================================

-- Insertar datos de SEXO
INSERT INTO sexo (codigo, nombre) VALUES
('M', 'Masculino'),
('F', 'Femenino'),
('O', 'Otro');

-- Insertar datos de GRUPO_EDAD
INSERT INTO grupo_edad (codigo, nombre, edad_minima, edad_maxima, orden) VALUES
('0-9', '0 - 9 años', 0, 9, 1),
('10-19', '10 - 19 años', 10, 19, 2),
('20-29', '20 - 29 años', 20, 29, 3),
('30-39', '30 - 39 años', 30, 39, 4),
('40-49', '40 - 49 años', 40, 49, 5),
('50-59', '50 - 59 años', 50, 59, 6),
('60-69', '60 - 69 años', 60, 69, 7),
('70-79', '70 - 79 años', 70, 79, 8),
('80+', '80 o más años', 80, NULL, 9);

-- Insertar datos de CONDICION (ajustar según datos reales)
INSERT INTO condicion (codigo, nombre, descripcion) VALUES
('CONDUCTOR', 'Conductor', 'Persona que conducía un vehículo'),
('PASAJERO', 'Pasajero', 'Persona que viajaba como pasajero'),
('PEATON', 'Peatón', 'Persona que transitaba a pie'),
('CICLISTA', 'Ciclista', 'Persona que transitaba en bicicleta'),
('MOTOCICLISTA', 'Motociclista', 'Persona que transitaba en motocicleta'),
('ACOMPAÑANTE_MOTO', 'Acompañante de Motocicleta', 'Acompañante que viaja en motocicleta'),
('OTRO', 'Otro', 'Otra condición');

-- Insertar datos de GRAVEDAD_VICTIMA
INSERT INTO gravedad_victima (codigo, nombre, descripcion, orden) VALUES
('FATAL', 'Fatal', 'Víctima fallecida', 1),
('GRAVE', 'Grave', 'Víctima con lesiones graves', 2),
('LEVE', 'Leve', 'Víctima con lesiones leves', 3),
('SOLO_DANOS', 'Solo daños', 'Solo daños materiales, sin víctimas', 4);

-- Insertar datos de CLASE_INCIDENTE (ajustar según datos reales)
INSERT INTO clase_incidente (codigo, nombre, descripcion) VALUES
('CHOQUE', 'Choque', 'Colisión entre vehículos'),
('ATROPELLO', 'Atropello', 'Atropello a persona'),
('VOLCAMIENTO', 'Volcamiento', 'Volcamiento de vehículo'),
('CAIDA', 'Caída de ocupante', 'Caída de ocupante del vehículo'),
('INCENDIO', 'Incendio', 'Incendio en vehículo'),
('OTRO', 'Otro', 'Otro tipo de incidente');

-- Vistas Útiles para Consultas
-- =====================================================

-- Vista: Vista completa de incidentes con información relacionada
CREATE OR REPLACE VIEW vista_incidentes_completa AS
SELECT 
    i.id,
    i.radicado,
    i.fecha_incidente,
    i.hora_incidente,
    i.fecha_hora_incidente,
    i.direccion_incidente,
    i.latitud,
    i.longitud,
    ci.nombre AS clase_incidente,
    co.nombre AS comuna,
    b.nombre AS barrio,
    COUNT(v.id) AS total_victimas,
    COUNT(CASE WHEN gv.codigo = 'FATAL' THEN 1 END) AS victimas_fatales,
    COUNT(CASE WHEN gv.codigo = 'GRAVE' THEN 1 END) AS victimas_graves,
    COUNT(CASE WHEN gv.codigo = 'LEVE' THEN 1 END) AS victimas_leves
FROM incidente i
LEFT JOIN clase_incidente ci ON i.clase_incidente_id = ci.id
LEFT JOIN comuna co ON i.comuna_id = co.id
LEFT JOIN barrio b ON i.barrio_id = b.id
LEFT JOIN victima v ON i.id = v.incidente_id
LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
GROUP BY i.id, i.radicado, i.fecha_incidente, i.hora_incidente, i.fecha_hora_incidente,
         i.direccion_incidente, i.latitud, i.longitud, ci.nombre, co.nombre, b.nombre;

-- Vista: Estadísticas de víctimas por incidente
CREATE OR REPLACE VIEW vista_estadisticas_victimas AS
SELECT 
    i.id AS incidente_id,
    i.radicado,
    i.fecha_incidente,
    COUNT(v.id) AS total_victimas,
    COUNT(CASE WHEN s.codigo = 'M' THEN 1 END) AS victimas_masculino,
    COUNT(CASE WHEN s.codigo = 'F' THEN 1 END) AS victimas_femenino,
    COUNT(CASE WHEN gv.codigo = 'FATAL' THEN 1 END) AS victimas_fatales,
    COUNT(CASE WHEN gv.codigo = 'GRAVE' THEN 1 END) AS victimas_graves,
    COUNT(CASE WHEN gv.codigo = 'LEVE' THEN 1 END) AS victimas_leves,
    COUNT(CASE WHEN c.codigo = 'PEATON' THEN 1 END) AS victimas_peaton,
    COUNT(CASE WHEN c.codigo = 'CONDUCTOR' THEN 1 END) AS victimas_conductor,
    COUNT(CASE WHEN c.codigo = 'CICLISTA' THEN 1 END) AS victimas_ciclista
FROM incidente i
LEFT JOIN victima v ON i.id = v.incidente_id
LEFT JOIN sexo s ON v.sexo_id = s.id
LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
LEFT JOIN condicion c ON v.condicion_id = c.id
GROUP BY i.id, i.radicado, i.fecha_incidente;

-- =====================================================
-- AUTENTICACIÓN, USUARIO, ROL Y SESIÓN (Django + dominio app)
-- =====================================================
--
-- Tablas con nombres y columnas alineados a django.contrib.auth,
-- django.contrib.sessions, django.contrib.contenttypes y
-- django.contrib.admin. La tabla auth_user es el "usuario" del sistema;
-- rol y perfil_usuario amplían el modelo sin alterar el núcleo de Django.
--
-- Uso:
--   • Base vacía: puede crearse solo el dominio y luego `manage.py migrate`
--     para auth/sessions (evitar duplicar si ya ejecutó este script).
--   • Script completo: crear todo y sincronizar migraciones Django con
--     --fake-initial o registro en django_migrations según proceda.
-- =====================================================

-- Metadatos de modelos (requerido por permisos de Django)
CREATE TABLE django_content_type (
    id SERIAL PRIMARY KEY,
    app_label VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model)
);

CREATE INDEX django_content_type_django_co_app_label_76bd3d3b_idx
    ON django_content_type (app_label);

-- Permisos granulares (admin, DRF opcional)
CREATE TABLE auth_permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content_type_id INTEGER NOT NULL REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED,
    codename VARCHAR(100) NOT NULL,
    CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename)
);

CREATE INDEX auth_permission_content_type_id_2f476e4b ON auth_permission (content_type_id);

-- Grupos de permisos de Django (opcional para agrupar permisos de staff)
CREATE TABLE auth_group (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);

CREATE INDEX auth_group_name_a6ea08ec_like ON auth_group (name varchar_pattern_ops);

-- USUARIO: tabla oficial User de Django (login, registro, hash de contraseña)
CREATE TABLE auth_user (
    id SERIAL PRIMARY KEY,
    password VARCHAR(128) NOT NULL,
    last_login TIMESTAMP WITH TIME ZONE NULL,
    is_superuser BOOLEAN NOT NULL,
    username VARCHAR(150) NOT NULL UNIQUE,
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    is_staff BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL,
    date_joined TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX auth_user_username_6821ab7c_like ON auth_user (username varchar_pattern_ops);

-- Relación muchos a muchos: usuarios pertenecen a grupos (auth.Group)
CREATE TABLE auth_user_groups (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id)
);

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON auth_user_groups (user_id);
CREATE INDEX auth_user_groups_group_id_97559544 ON auth_user_groups (group_id);

CREATE TABLE auth_group_permissions (
    id BIGSERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id)
);

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON auth_group_permissions (group_id);
CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON auth_group_permissions (permission_id);

CREATE TABLE auth_user_user_permissions (
    id BIGSERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED,
    permission_id INTEGER NOT NULL REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id)
);

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON auth_user_user_permissions (user_id);
CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON auth_user_user_permissions (permission_id);

-- SESIÓN: almacena sessionid y datos serializados (login persistente, CSRF asociado en app)
CREATE TABLE django_session (
    session_key VARCHAR(40) NOT NULL PRIMARY KEY,
    session_data TEXT NOT NULL,
    expire_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX django_session_expire_date_a5c62663 ON django_session (expire_date);

-- Historial de migraciones de Django
CREATE TABLE django_migrations (
    id BIGSERIAL PRIMARY KEY,
    app VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    applied TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Log de acciones del Admin de Django (opcional)
CREATE TABLE django_admin_log (
    id SERIAL PRIMARY KEY,
    action_time TIMESTAMP WITH TIME ZONE NOT NULL,
    object_id TEXT NULL,
    object_repr VARCHAR(200) NOT NULL,
    action_flag SMALLINT NOT NULL,
    change_message TEXT NOT NULL,
    content_type_id INTEGER NULL REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON django_admin_log (content_type_id);
CREATE INDEX django_admin_log_user_id_c564eba6 ON django_admin_log (user_id);

-- ROL: catálogo de roles de negocio (independiente de auth_group de Django)
CREATE TABLE rol (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(32) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO rol (codigo, nombre, descripcion) VALUES
('ciudadano', 'Ciudadano', 'Usuario general / consulta'),
('autoridad', 'Autoridad', 'Perfil institucional / priorización'),
('analista', 'Analista', 'Análisis y reportes'),
('administrador', 'Administrador', 'Gestión de usuarios y configuración');

-- PERFIL: extiende auth_user con rol de aplicación y datos opcionales (1:1 con usuario)
CREATE TABLE perfil_usuario (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE,
    rol_id INTEGER NOT NULL REFERENCES rol(id),
    telefono VARCHAR(30) NULL,
    organizacion VARCHAR(255) NULL,
    acepta_notificaciones BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_perfil_usuario_rol_id ON perfil_usuario (rol_id);

COMMENT ON TABLE auth_user IS 'Usuarios del sistema (django.contrib.auth.User); credenciales y estado.';
COMMENT ON TABLE rol IS 'Roles de negocio del tablero; enlazados desde perfil_usuario.';
COMMENT ON TABLE perfil_usuario IS 'Perfil 1:1 con auth_user; en Django: OneToOneField(User) y ForeignKey(Rol).';
COMMENT ON TABLE django_session IS 'Sesiones de usuario (django.contrib.sessions).';
