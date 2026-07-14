-- 1. Usuarios (Tabla base para conductores y finanzas)
CREATE TABLE IF NOT EXISTS usuarios (
    cedula VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(150),
    telefono VARCHAR(50),
    email VARCHAR(100),
    direccion TEXT,
    contrasena VARCHAR(255),
    rol VARCHAR(50),
    activo VARCHAR(10) DEFAULT 'Sí',
    fecha_baja VARCHAR(50),
    departamento VARCHAR(100),
    banco VARCHAR(100),
    numero_cuenta VARCHAR(100)
);

-- 2. Conductores
CREATE TABLE IF NOT EXISTS conductores (
    cedula VARCHAR(50) PRIMARY KEY REFERENCES usuarios(cedula) ON DELETE RESTRICT,
    vehiculo VARCHAR(100),
    placa VARCHAR(20),
    propio VARCHAR(10) DEFAULT 'No',
    disponible VARCHAR(10) DEFAULT 'Sí',
    vence_certificado VARCHAR(50),
    vence_rotc VARCHAR(50),
    capacidad_carga VARCHAR(50)
);

-- 3. Finanzas Personal
CREATE TABLE IF NOT EXISTS finanzas_personal (
    cedula VARCHAR(50) PRIMARY KEY REFERENCES usuarios(cedula) ON DELETE RESTRICT,
    tipo_pago VARCHAR(50) DEFAULT 'Sueldo Fijo',
    monto_base NUMERIC(12,2) DEFAULT 0.0,
    cestaticket NUMERIC(12,2) DEFAULT 0.0,
    pago_por_viaje NUMERIC(12,2) DEFAULT 0.0,
    bono_empresa NUMERIC(12,2) DEFAULT 0.0,
    bono_decreto NUMERIC(12,2) DEFAULT 0.0,
    otros_ingresos NUMERIC(12,2) DEFAULT 0.0
);

-- 4. Vehículos
CREATE TABLE IF NOT EXISTS vehiculos (
    placa VARCHAR(20) PRIMARY KEY,
    marca VARCHAR(100) NOT NULL,
    modelo VARCHAR(100) NOT NULL,
    tipo_vehiculo VARCHAR(50),
    anio INTEGER,
    kilometraje_actual NUMERIC(12,2) DEFAULT 0,
    serial_motor VARCHAR(100),
    serial_carroceria VARCHAR(100),
    capacidad_peso_kg NUMERIC(12,2) DEFAULT 0,
    capacidad_volumen_m3 NUMERIC(12,2) DEFAULT 0,
    vencimiento_rcv VARCHAR(50),
    vencimiento_trimestres VARCHAR(50),
    chofer_asignado VARCHAR(50),
    propietario_tipo VARCHAR(50) DEFAULT 'Propio',
    propietario_cedula VARCHAR(50),
    propietario_nombre VARCHAR(150),
    estatus VARCHAR(50) DEFAULT 'Operativo',
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Control de Combustible (Humano/Rastreo)
CREATE TABLE IF NOT EXISTS control_combustible (
    id SERIAL PRIMARY KEY,
    placa VARCHAR(20),
    cedula VARCHAR(50) REFERENCES usuarios(cedula),
    fecha VARCHAR(50),
    km_actual INTEGER,
    litros_comprados NUMERIC(12,2),
    costo_usd NUMERIC(12,2),
    tasa_cambio NUMERIC(12,4),
    costo_bs NUMERIC(12,2),
    estacion_servicio TEXT
);

-- 6. Combustible (Módulo alterno)
CREATE TABLE IF NOT EXISTS combustible (
    id_registro SERIAL PRIMARY KEY,
    cedula VARCHAR(50) NOT NULL REFERENCES usuarios(cedula) ON DELETE RESTRICT,
    fecha VARCHAR(50) NOT NULL,
    km_actual NUMERIC(12,2) NOT NULL,
    litros_comprados NUMERIC(12,2) NOT NULL,
    costo_usd NUMERIC(12,2) NOT NULL,
    tasa_cambio NUMERIC(12,4) NOT NULL,
    costo_bs NUMERIC(12,2) NOT NULL,
    estacion_servicio TEXT
);

-- 7. Gastos Generales
CREATE TABLE IF NOT EXISTS gastos (
    id_gasto SERIAL PRIMARY KEY,
    fecha VARCHAR(50) NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    monto_usd NUMERIC(12,2) NOT NULL,
    observaciones TEXT DEFAULT '',
    placa_vehiculo VARCHAR(20) DEFAULT 'General'
);

-- 8. Configuración
CREATE TABLE IF NOT EXISTS configuracion (
    clave VARCHAR(100) PRIMARY KEY,
    valor TEXT NOT NULL
);

-- 9. Gastos Operativos de Viaje
CREATE TABLE IF NOT EXISTS gastos_operativos_viaje (
    id SERIAL PRIMARY KEY,
    fecha VARCHAR(50) NOT NULL,
    placa VARCHAR(20) NOT NULL,
    tipo_gasto VARCHAR(100) NOT NULL,
    monto_bs NUMERIC(12,2) NOT NULL,
    tasa_cambio NUMERIC(12,4) NOT NULL,
    monto_usd NUMERIC(12,2) NOT NULL,
    estacion_origen_destino TEXT,
    observaciones TEXT
);

-- 10. CXC Independiente
CREATE TABLE IF NOT EXISTS cxc_independiente (
    id_cxc SERIAL PRIMARY KEY,
    deudor VARCHAR(150),
    concepto TEXT,
    monto_inicial NUMERIC(12,2),
    monto_pendiente NUMERIC(12,2),
    fecha_registro VARCHAR(50),
    estatus VARCHAR(50) DEFAULT 'Pendiente',
    notas TEXT
);

-- 11. CXP Independiente
CREATE TABLE IF NOT EXISTS cxp_independiente (
    id_cxp SERIAL PRIMARY KEY,
    acreedor VARCHAR(150),
    concepto TEXT,
    monto_inicial NUMERIC(12,2),
    monto_pendiente NUMERIC(12,2),
    fecha_registro VARCHAR(50),
    estatus VARCHAR(50) DEFAULT 'Pendiente',
    notas TEXT
);

-- 12. Clientes
CREATE TABLE IF NOT EXISTS clientes (
    id_cliente SERIAL PRIMARY KEY,
    rif VARCHAR(50) UNIQUE,
    razon_social VARCHAR(200),
    telefono_contacto VARCHAR(50),
    email_contacto VARCHAR(100),
    direccion_fiscal TEXT,
    dias_credito INTEGER,
    limite_credito_usd NUMERIC(12,2),
    saldo_pendiente_usd NUMERIC(12,2),
    credito_disponible_usd NUMERIC(12,2),
    contrasena VARCHAR(255)
);

-- 13. Sucursales
CREATE TABLE IF NOT EXISTS sucursales (
    id_sucursal SERIAL PRIMARY KEY,
    id_cliente INTEGER NOT NULL,
    nombre_agencia VARCHAR(150) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    direccion TEXT NOT NULL,
    telefono_sucursal VARCHAR(50),
    latitud NUMERIC(10,6) NOT NULL,
    longitud NUMERIC(10,6) NOT NULL,
    activa VARCHAR(10) NOT NULL DEFAULT 'Sí'
);

-- 14. Cuentas por Cobrar
CREATE TABLE IF NOT EXISTS cuentas_por_cobrar (
    id_factura SERIAL PRIMARY KEY,
    rif_cliente VARCHAR(50) NOT NULL REFERENCES clientes(rif),
    id_sucursal INTEGER NOT NULL REFERENCES sucursales(id_sucursal),
    id_viaje INTEGER NOT NULL,
    fecha_emision VARCHAR(50) NOT NULL,
    fecha_vencimiento VARCHAR(50) NOT NULL,
    monto_usd NUMERIC(12,2) NOT NULL,
    estatus_pago VARCHAR(50) DEFAULT 'Pendiente'
);

-- 15. Viajes
CREATE TABLE IF NOT EXISTS viajes (
    id_viaje SERIAL PRIMARY KEY,
    id_cliente INTEGER,
    id_sucursal_origen INTEGER,
    cedula_conductor VARCHAR(50),
    fecha_despacho VARCHAR(50),
    origen TEXT,
    destino TEXT,
    tipo_material VARCHAR(150),
    distancia_km NUMERIC(10,2),
    tipo_viaje VARCHAR(50),
    peso_carga_kg NUMERIC(12,2),
    monto_flete_usd NUMERIC(12,2),
    persona_contacto_entrega VARCHAR(150),
    telefono_contacto_entrega VARCHAR(50),
    observaciones TEXT,
    num_pedido VARCHAR(100),
    num_factura VARCHAR(100),
    estatus_viaje VARCHAR(50),
    cliente_solicitante VARCHAR(150),
    telefono_cliente VARCHAR(50),
    latitud_entrega NUMERIC(10,6),
    longitud_entrega NUMERIC(10,6),
    foto_evidencia TEXT,
    descuento_usd NUMERIC(12,2),
    importe_neto_usd NUMERIC(12,2),
    pago_chofer_usd NUMERIC(12,2),
    beneficio_exprex_usd NUMERIC(12,2)
);
