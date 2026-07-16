import streamlit as st
import os
import time
import sys
import datetime as dt
import pandas as pd
import streamlit.components.v1 as components
#from modulos.version_app import mostrar_version_de_la_app


ruta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ruta_raiz not in sys.path:
    sys.path.insert(0, ruta_raiz)

# Importamos la función de conexión a PostgreSQL que creamos para tu proyecto
from modulos.utils import obtener_conexion_db

# --- CARGAR TEXTO LEGAL DESDE LA CARPETA MODULOS ---
ruta_terminos = os.path.join("modulos", "terminos.txt")

try:
    with open(ruta_terminos, "r", encoding="utf-8") as f:
        texto_legal_choferes = f.read()
except Exception as e:
    texto_legal_choferes = f"⚠️ No se pudo cargar el archivo de términos en `{ruta_terminos}`: {e}"

# =========================================================================
# 🕵️‍♂️ VERIFICACIÓN DE CREDENCIALES CORPORATIVAS
# =========================================================================
def verificar_cliente_b2b(rif: str, contrasena: str):
    """
    Busca en la tabla clientes si coinciden de forma exacta el RIF y la contraseña.
    Retorna los datos esenciales si tiene éxito, o None si fallan las credenciales.
    """
    # Tipamos los parámetros para evitar alertas de Pylance
    rif_limpio = rif.strip().upper()
    pass_limpia = contrasena.strip()
    
    query = """
        SELECT id_cliente, rif, razon_social 
        FROM clientes 
        WHERE UPPER(rif) = %s AND contrasena = %s
    """
    
    try:
        # Usamos el bloque 'with' seguro para manejar la conexión y el cursor de Postgres
        with obtener_conexion_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(query, (rif_limpio, pass_limpia))
                resultado = cursor.fetchone()
                return resultado  # Retorna la tupla (id_cliente, rif, razon_social) o None
    except Exception as e:
        st.error(f"❌ Error al conectar con la base de datos PostgreSQL: {e}")
        return None
#    
# =========================================================================
# 🏢 PANEL PRINCIPAL DEL CLIENTE (MÓDULO INDEPENDIENTE)
# =========================================================================
def mostrar_interfaz_cliente():

    # Crear una clave de formulario en el estado de la sesión si no existe
    if "formulario_token" not in st.session_state:
        st.session_state.formulario_token = 0

    # 🚀 MEMORIA INTERNA: Inicializamos las variables de sesión para retener los datos si hay error
    valores_por_defecto = {
        "tmp_destino": "",
        "tmp_material": "Materiales de Construcción",
        "tmp_solicitante": "",
        "tmp_contacto": "",
        "tmp_unidad": "Mini-Truck / Pickup (Hasta 1.5 Ton)",
        "tmp_viaje": "Normal",
        "tmp_peso": 500.0,
        "tmp_pedido": "",
        "tmp_telefono": "",
        "tmp_telefono_contacto": "",
        "tmp_observaciones": ""
    }
    for clave, valor in valores_por_defecto.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor

    # Recuperamos los datos del cliente que guardamos en el session_state al loguearse
    id_cliente = st.session_state.get("cliente_id")
    rif_cliente = st.session_state.get("usuario_cedula") # Reutilizamos la variable de sesión para el RIF
    razon_social = st.session_state.get("usuario_nombre")
    
    # Valores por defecto iniciales por seguridad de tipado
    dias_credito: int = 15
    limite_credito: float = 0.0 
    saldo_pendiente: float = 0.0
    credito_disponible: float = 0.0    

    # Consultamos los saldos actualizados directamente de la base de datos PostgreSQL
    query_finanzas = """
        SELECT dias_credito, limite_credito_usd, saldo_pendiente_usd, credito_disponible_usd 
        FROM clientes 
        WHERE id_cliente = %s
    """
    
    try:
        with obtener_conexion_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(query_finanzas, (id_cliente,))
                finanzas = cursor.fetchone()
                
                if finanzas is not None:
                    dias_credito = int(finanzas[0]) if finanzas[0] is not None else 15
                    limite_credito = float(finanzas[1]) if finanzas[1] is not None else 0.0
                    saldo_pendiente = float(finanzas[2]) if finanzas[2] is not None else 0.0
                    credito_disponible = float(finanzas[3]) if finanzas[3] is not None else 0.0
                else:
                    credito_disponible = limite_credito - saldo_pendiente
    except Exception as e:
        # Caída segura en caso de un fallo de red o base de datos
        credito_disponible = limite_credito - saldo_pendiente


    # -------------------------------------------------------------------------
    # ENCABEZADO Y MÉTRICAS FINANCIERAS
    # -------------------------------------------------------------------------
    st.header("ExpreX - Clientes")
    st.write(f"### 🏢 Panel Corporativo: {razon_social}")
    st.caption(f"RIF: {rif_cliente} | Gestión de Logística y Cuentas por Cobrar ExpreX")
    st.markdown("---")
    
    # 🎨 Bloque de CSS para ajustar quirúrgicamente el tamaño de los métricos
    st.markdown(
        """
        <style>
        [data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
            font-weight: 600 !important;
        }
        [data-testid="stMetricLabel"] p {
            font-size: 0.9rem !important;
            color: #b0b3b8 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Tarjetas visuales con el estado de su crédito
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="💰 Límite de Crédito", value=f"${limite_credito:,.2f}")
    with col2:
        st.metric(label="💵 Consumido a la fecha", value=f"${saldo_pendiente:,.2f}")
    with col3:
        st.metric(label="🛡️ Disponible", value=f"${credito_disponible:,.2f}")
    with col4:
        st.metric(label="📅 Términos de Pago", value=f"{dias_credito} días de crédito")
    
    st.markdown("---")
    #
    # -------------------------------------------------------------------------
    # PESTAÑAS DE TRABAJO
    # -------------------------------------------------------------------------
    pestana_solicitud, pestana_historial, consulta_despachos = st.tabs([
        "🚀 Solicitar Nuevo Flete", 
        "🕒 Historial y Status de Fletes",
        "Consulta Individual"
    ])
    
    # --- PESTAÑA 1: SOLICITAR FLETE ---
    with pestana_solicitud:
        st.write("#### 📦 Registrar Nueva Solicitud de Despacho")
        st.info("Complete los detalles de la carga para que nuestro equipo operativo valide y asigne la unidad.")
        
        # 1. Recuperamos las sucursales de origen del cliente
        df_sucursales = pd.DataFrame()
        try:
            # 💡 Blindaje Pylance: Si id_cliente es None, le asignamos 0 o un valor vacío para que no rompa el tipado
            id_cliente_seguro = id_cliente if id_cliente is not None else 0

            query_sucursales = """
                SELECT id_sucursal, nombre_agencia, ciudad 
                FROM sucursales 
                WHERE id_cliente = %s AND activa = 'Sí'
            """
            with obtener_conexion_db() as conexion:
                df_sucursales = pd.read_sql_query(query_sucursales, conexion, params=(id_cliente_seguro,))
        except Exception as e:
            st.error(f"❌ Error al cargar sucursales: {e}")
            df_sucursales = pd.DataFrame()

        if not df_sucursales.empty:
            lista_sucursales = df_sucursales['id_sucursal'].tolist()
            def formatear_sucursal(id_suc):
                fila = df_sucursales[df_sucursales['id_sucursal'] == id_suc].iloc[0]
                return f"{fila['nombre_agencia']} ({fila['ciudad']})"
            
            # 🎯 CORRECCIÓN: Quitamos clear_on_submit=True para evitar el vaciado inmediato y erróneo de campos
            with st.form(key=f"form_nueva_solicitud_{st.session_state.formulario_token}"):    

                col_f1, col_f2 = st.columns(2)                
                with col_f1:
                    sucursal_origen = st.selectbox("📍 Sucursal de Origen (Despacho):", options=lista_sucursales, format_func=formatear_sucursal)
                    
                    direccion_destino = st.text_area("🏁 Dirección de Destino Final:", value=str(st.session_state.tmp_destino), placeholder="Ej: Almacén Central, Av. Michelena, Valencia, Edo. Carabobo")
                    st.markdown("")
                    st.markdown("")
                    
                    # 🏁 BLOQUE DE MATERIALES SEGURO:
                    opciones_materiales = ["Materiales de Construcción", "Alimentos / Consumo Masivo", "Repuestos / Automotriz", "Línea Blanca / Electrónicos", "Químicos / Materia Prima", "Otros (Especificar en observaciones)"]
                    idx_mat = opciones_materiales.index(st.session_state.tmp_material) if st.session_state.tmp_material in opciones_materiales else 0
                    tipo_material = st.selectbox("📦 Tipo de Material / Mercancía:", opciones_materiales, index=idx_mat)
                    
                    st.markdown("---")
                    solicitante_nombre = st.text_input("👤 Nombre y Apellido (Quien solicita el servicio):", value=str(st.session_state.tmp_solicitante), placeholder="Ej: Carlos Pérez")
                    persona_contacto = st.text_input("👤 Persona de Contacto en Entrega (Destino):", value=str(st.session_state.tmp_contacto))
                
                with col_f2:
                    # 🏁 BLOQUE DE UNIDADES LIMPIO:
                    opciones_unidades = ["Mini-Truck / Pickup (Hasta 1.5 Ton)", "Camión 350 (Hasta 3.5 Ton)", "Camión 750 / Triton (Hasta 5 Ton)", "Chuto / Gandola (Carga Pesada)"]
                    idx_uni = opciones_unidades.index(st.session_state.tmp_unidad) if st.session_state.tmp_unidad in opciones_unidades else 0
                    tipo_unidad_requerida = st.selectbox("Unidad Requerida:", opciones_unidades, index=idx_uni)
                    
                    tipo_viaje = st.radio(
                        "⚡ Tipo de Viaje (Urgencia):", 
                        options=["Normal", "Express"], 
                        index=0 if st.session_state.tmp_viaje == "Normal" else 1,
                        help="Seleccione Express si el despacho requiere prioridad absoluta de asignación.", horizontal=True
                    )
                    
                    peso_carga_kg = st.number_input("⚖️ Peso Estimado de la Carga (Kg):", min_value=1.0, value=float(st.session_state.tmp_peso), step=50.0)
                    num_pedido = st.text_input("🔢 Número de Pedido / Referencia Interna:", value=str(st.session_state.tmp_pedido), placeholder="Ej: PED-2026-99")
                    
                    st.markdown("---")
                    solicitante_telefono = st.text_input("📞 Teléfono Directo / Extensión:", value=str(st.session_state.tmp_telefono), placeholder="Ej: 0412-5551234")
                    telefono_contacto = st.text_input("📞 Teléfono de Contacto en Entrega (Destino):", value=str(st.session_state.tmp_telefono_contacto))
                    
                observaciones = st.text_area("📝 Observaciones o Instrucciones Especiales:", value=str(st.session_state.tmp_observaciones), placeholder="Ej: Llevar precintos de seguridad, despachar en horario de la mañana...")
                
                st.markdown("---")
                boton_solicitar = st.form_submit_button("🚀 Enviar Solicitud de Flete", use_container_width=True, type="primary")
                
                if boton_solicitar:
                    # 🎯 RESPALDO INMEDIATO en la memoria temporal antes de cualquier validación
                    st.session_state.tmp_destino = str(direccion_destino or "").strip()
                    st.session_state.tmp_material = tipo_material
                    st.session_state.tmp_solicitante = str(solicitante_nombre or "").strip()
                    st.session_state.tmp_contacto = str(persona_contacto or "").strip()
                    st.session_state.tmp_unidad = tipo_unidad_requerida
                    st.session_state.tmp_viaje = tipo_viaje
                    st.session_state.tmp_peso = peso_carga_kg
                    st.session_state.tmp_pedido = str(num_pedido or "").strip()
                    st.session_state.tmp_telefono = str(solicitante_telefono or "").strip()
                    st.session_state.tmp_telefono_contacto = str(telefono_contacto or "").strip()
                    st.session_state.tmp_observaciones = str(observaciones or "").strip()

                    # 🛑 VALIDACIONES COMPLETAS
                    if not str(direccion_destino or "").strip():
                        st.error("❌ Por favor, especifique la dirección de destino final.")
                    elif not str(solicitante_nombre or "").strip() or not str(solicitante_telefono or "").strip():
                        st.error("❌ Por favor, indique el nombre y teléfono de la persona que solicita el servicio.")
                    elif credito_disponible <= 0:
                        st.error("⚠️ Solicitud No Registrada: Su empresa ha excedido su límite de crédito disponible. Comuníquese con la Administración de ExpreX.")
                    else:
                        # --- INSERCIÓN SEGURA EN POSTGRESQL ---
                        try:
                            origen_texto = formatear_sucursal(sucursal_origen)
                            
                            query_insertar = """
                                INSERT INTO viajes (
                                    id_cliente, 
                                    id_sucursal_origen, 
                                    fecha_despacho,
                                    origen,
                                    destino, 
                                    tipo_material, 
                                    tipo_viaje,
                                    peso_carga_kg, 
                                    persona_contacto_entrega,
                                    telefono_contacto_entrega,
                                    num_pedido,
                                    observaciones, 
                                    estatus_viaje,
                                    cliente_solicitante,
                                    telefono_cliente
                                ) VALUES (%s, %s, CURRENT_DATE, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Solicitado', %s, %s)
                            """
                            
                            with obtener_conexion_db() as conexion:
                                with conexion.cursor() as cursor:
                                    cursor.execute(query_insertar, (
                                        id_cliente, 
                                        sucursal_origen, 
                                        origen_texto,
                                        st.session_state.tmp_destino, 
                                        st.session_state.tmp_material, 
                                        st.session_state.tmp_viaje,
                                        st.session_state.tmp_peso, 
                                        st.session_state.tmp_contacto,
                                        st.session_state.tmp_telefono_contacto,
                                        st.session_state.tmp_pedido,
                                        st.session_state.tmp_observaciones,
                                        st.session_state.tmp_solicitante,   
                                        st.session_state.tmp_telefono  
                                    ))
                                    # Al usar context managers con psycopg2, se hace commit automático si no hay errores,
                                    # pero forzarlo explícitamente asegura la persistencia en el pool.
                                    conexion.commit()

                            st.success("🎉 ¡Solicitud de flete registrada con éxito en ExpreX!")
                            
                            # 🧹 LIMPIEZA TOTAL DE MEMORIA ÚNICAMENTE AL TENER ÉXITO
                            for k in valores_por_defecto.keys():
                                if k in st.session_state:
                                    del st.session_state[k]

                            # Avanzamos el token del formulario para refrescarlo limpio
                            st.session_state.formulario_token += 1
                            
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error al registrar la solicitud: {e}")
        else:
            st.warning("⚠️ No se encontraron sucursales activas registradas para su cuenta corporativa. Contacte a soporte de ExpreX.")

    # --- PESTAÑA 2: HISTORIAL DIRECTO ---
    #
    # =========================================================================
    # 📌 PESTAÑA: HISTORIAL DE FLETES (FILTRADO POR MESES Y CABECERAS LIMPIAS)
    # =========================================================================
    with pestana_historial:
        st.write("#### 📜 Historial de Despachos Ejecutados")
        
        # --- FILTRO DE MESES INTELIGENTE ---
        meses_dicc = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        
        hoy = dt.date.today()
        ano_actual = hoy.year
        mes_actual = hoy.month
        
        # Lista desplegable para el mes actual y los 5 meses anteriores
        opciones_meses = []
        for i in range(6):
            m = mes_actual - i
            a = ano_actual
            if m <= 0:
                m += 12
                a -= 1
            opciones_meses.append((a, m))

        mes_seleccionado = st.selectbox(
            "📅 Seleccione el mes a consultar:",
            options=opciones_meses,
            format_func=lambda x: f"{meses_dicc[x[1]]} {x[0]}",
            key="filtro_mes_cliente" # Key única para evitar conflictos en Streamlit
        )
        
        # 💡 CONTROL CRÍTICO: Si no hay opciones, evitamos que rompa la app
        if mes_seleccionado is None:
            mes_seleccionado = (hoy.year, hoy.month)

        ano_sel, mes_sel = mes_seleccionado
        f_inicio_mes = f"{ano_sel}-{mes_sel:02d}-01"
        if mes_sel == 12:
            f_fin_mes = f"{ano_sel + 1}-01-01"
        else:
            f_fin_mes = f"{ano_sel}-{mes_sel + 1:02d}-01"
            
        try:
            with obtener_conexion_db() as conexion:
            #conexion = sqlite3.connect('exprex.db')
            
            # 🎯 SOLUCIÓN DEFINITIVA: Filtramos el mes comparando directamente 
            # las cadenas de texto (año y mes) del selector con la columna fecha_despacho.
            # Además, incluimos TODOS los estatus para que puedas ver el historial completo del mes.
                filtro_mes_texto = f"{ano_sel}-{mes_sel:02d}-%"
                
                df_historial = pd.read_sql_query('''
                    SELECT id_viaje, fecha_despacho, origen, cliente_solicitante, destino, estatus_viaje, tipo_material, num_pedido, 
                        monto_flete_usd, descuento_usd, importe_neto_usd
                    FROM viajes 
                    WHERE id_cliente = %s 
                    AND fecha_despacho LIKE %s
                    ORDER BY id_viaje DESC
                ''', conexion, params=(st.session_state.cliente_id, filtro_mes_texto)) 
                #conexion.close()
        except Exception as e:
            st.error(f"❌ Error al cargar historial filtrado: {e}")
            df_historial = pd.DataFrame()

        if df_historial.empty:
            st.info(f"ℹ️ No se registran despachos finalizados en {meses_dicc[mes_sel]} {ano_sel}.")
        else:
            # 🔄 MAPEO DE CABECERAS FINANCIERAS PARA EL CLIENTE
            df_visual = df_historial.rename(columns={
                'id_viaje': 'Flete N°',
                'fecha_despacho': 'Fecha',
                'num_pedido': 'Pedido',
                'origen': 'Origen',
                'cliente_solicitante': 'Cliente',
                'destino': 'Destino',
                'estatus_viaje': 'Estatus',
                'tipo_material': 'Material',
                'monto_flete_usd': 'Monto Flete',
                'descuento_usd': 'Descuento',
                'importe_neto_usd': 'Neto ($)'
            })

            # Removemos del DataFrame visual las columnas de desglose para que no saturen la tabla horizontal
            columnas_visibles = ['Flete N°', 'Fecha', 'Pedido', 'Origen', 'Cliente', 'Destino', 'Estatus', 'Material', 'Monto Flete', 'Descuento', 'Neto ($)']
            st.dataframe(df_visual[columnas_visibles], use_container_width=True, hide_index=True)
            
            st.write("---")
            st.write("🔍 **Consulta Individual Detallada**")
            
            dicc_historial = {}
            for _, row in df_historial.iterrows():
                id_v = int(row['id_viaje'])
                pedido = row['num_pedido'] if pd.notna(row['num_pedido']) and str(row['num_pedido']).strip() != "" else "S/N"
                dicc_historial[id_v] = f"Flete N° {id_v} (Ped: {pedido})"
            
            id_historial_sel = st.selectbox(
                "Seleccione un flete pasado para ver detalles:", 
                options=list(dicc_historial.keys()),
                format_func=lambda x: str(dicc_historial.get(x, f"Flete N° {x}")),
                key="detalle_flete_cliente"
            )
            
            if id_historial_sel:
                try:
                    query_detalle = """
                        SELECT origen, destino, tipo_material, peso_carga_kg, estatus_viaje, num_pedido, tipo_viaje
                        FROM viajes 
                        WHERE id_viaje = %s
                    """
                    with obtener_conexion_db() as conexion:
                        with conexion.cursor() as cursor:
                            cursor.execute(query_detalle, (id_historial_sel,))
                            v_det = cursor.fetchone()
                    
                    if v_det:
                        st.info(f"""
                        **Detalle del Flete N° {id_historial_sel}**
                        * **N° Pedido:** {v_det[5] if v_det[5] else "S/N"}
                        * **Ruta:** {v_det[0]} ➡️ {v_det[1]}
                        * **Material:** {v_det[2]} ({v_det[3]} Kg)
                        * **Tipo de viaje:** {v_det[6]}
                        * **Estatus Final:** {v_det[4]}
                        """)
                except Exception as e:
                    st.error(f"Error al abrir detalle individual: {e}")

        # 🔄 BOTÓN DE RETORNO AL MENÚ PRINCIPAL
        st.write("---")

        st.info("Para ir a la pantalla inicial haga clic en la pestaña Solicitar Nuevo Flete")
        #if st.button("🏠 Volver al Menú Principal", key="btn_home_hist_cli", use_container_width=True):
        #    st.session_state["cliente_pagina"] = "Menu Principal"
        st.rerun()
    #
    # =========================================================================
    # PESTAÑA: CONSULTOR INDIVIDUAL DE DESPACHOS (PARA CLIENTES)
    # =========================================================================
    with consulta_despachos:
        st.write("### 🔍 Consulta y Rastreo Individual de Despachos")
        st.markdown("---")
        
        # Formulario de búsqueda limpio
        col_busq1, col_busq2 = st.columns([3, 1])
        with col_busq1:
            dato_busqueda = st.text_input(
                "Mete el Número de Pedido, Factura, Código de Viaje o Nombre del cliente:",
                placeholder="Ej. PED-10023, FAC-5540 o Juan González...",
                key="input_rastreo_despacho"
            ).strip()
        with col_busq2:
            st.write("##") # Espacio visual para alinear el botón
            btn_buscar = st.button("🔍 Rastrear", use_container_width=True, type="primary")
            
        if dato_busqueda or btn_buscar:
            try:
                # Importamos el cursor de diccionarios de psycopg2 para mantener la compatibilidad con tu código
                from psycopg2.extras import RealDictCursor
                
                # Buscamos de forma flexible si coincide con id_viaje, num_pedido o num_factura
                # Convertimos id_viaje a TEXT para evitar errores de tipado si buscan un string
                sql_rastreo = """
                    SELECT 
                        v.id_viaje,
                        v.estatus_viaje,
                        v.num_pedido,
                        v.num_factura,
                        c.razon_social AS cliente,
                        s.nombre_agencia AS origen,
                        v.destino,
                        v.cliente_solicitante,
                        v.persona_contacto_entrega,
                        v.telefono_contacto_entrega,
                        u.nombre AS conductor,
                        v.fecha_despacho,
                        v.foto_evidencia
                    FROM viajes v
                    JOIN clientes c ON v.id_cliente = c.id_cliente
                    LEFT JOIN sucursales s ON v.id_sucursal_origen = s.id_sucursal
                    JOIN usuarios u ON v.cedula_conductor = u.cedula
                    WHERE (CAST(v.id_viaje AS TEXT) = %s 
                       OR v.num_pedido LIKE %s 
                       OR v.num_factura LIKE %s 
                       OR v.cliente_solicitante LIKE %s)
                """
                param_like = f"%{dato_busqueda}%"
                
                with obtener_conexion_db() as conexion:
                    # Usamos RealDictCursor para poder indexar las columnas por su nombre literal
                    with conexion.cursor(cursor_factory=RealDictCursor) as cursor:
                        cursor.execute(sql_rastreo, (dato_busqueda, param_like, param_like, param_like))
                        viaje = cursor.fetchone()
                
                if viaje:
                    st.success(f"📦 ¡Despacho Localizado! - **Viaje #{viaje['id_viaje']}**")
                    
                    # 🚦 BARRA DE PROGRESO VISUAL DEL ESTATUS
                    estatus = str(viaje['estatus_viaje'])
                    
                    # Definimos el porcentaje y el color de la barra según el estatus real
                    if estatus == 'Por Salir':
                        porcentaje_progreso = 25
                        info_bandera = "📋 **Estatus actual:** Listo en Andén. El transporte está cargando la mercancía."
                    elif estatus == 'En Ruta':
                        porcentaje_progreso = 60
                        info_bandera = "🛣️ **Estatus actual:** En Carretera. El flete va en tránsito hacia el destino."
                    elif estatus == 'En Descarga' or estatus == 'Descargando':
                        porcentaje_progreso = 85
                        info_bandera = "⏳ **Estatus actual:** En Descarga. El vehículo llegó al sitio del cliente y está entregando."
                    elif estatus == 'Entregado':
                        porcentaje_progreso = 100
                        info_bandera = "🎉 **Estatus actual:** Entregado. El flete finalizó y el soporte fue firmado."
                    else:
                        porcentaje_progreso = 0
                        info_bandera = f"ℹ️ **Estatus actual:** {estatus}"
                        
                    st.progress(porcentaje_progreso)
                    st.info(info_bandera)
                    
                    st.markdown("#### 📋 Datos de la Hoja de Ruta")
                    
                    # Mostramos los datos estéticos ordenados en dos columnas
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**🏢 Cliente          :** {viaje['cliente']}")
                        st.markdown(f"**📦 Número de Pedido :** {viaje['num_pedido'] if viaje['num_pedido'] else 'N/A'}")
                        st.markdown(f"**🧾 Número de Factura:** {viaje['num_factura'] if viaje['num_factura'] else 'N/A'}")
                        st.markdown(f"**📅 Fecha de Despacho:** {viaje['fecha_despacho']}")
                    with c2:
                        st.markdown(f"**🏭 Agencia de Origen   :** {viaje['origen'] if viaje['origen'] else 'Galpón Principal'}")
                        st.markdown(f"**📍 Dirección de Entrega:** {viaje['destino']}")
                        st.markdown(f"**👤 Recibe:** {viaje['persona_contacto_entrega']}, **Tel:** {viaje['telefono_contacto_entrega']}")
                        st.markdown(f"**🚛 Conductor Asignado  :** {viaje['conductor']}")
                    
                    # 📸 MOSTRAR FOTO DEL COMPROBANTE AL CLIENTE SI YA ESTÁ ENTREGADO
                    if estatus == 'Entregado':
                        st.markdown("---")
                        st.markdown("#### 📸 Soporte Digital de Entrega")
                        ruta_foto = str(viaje['foto_evidencia']) if viaje['foto_evidencia'] else ""
                        
                        if ruta_foto and os.path.exists(ruta_foto):
                            # Abrimos y mostramos la foto firmada
                            with open(ruta_foto, "rb") as file_foto:
                                st.image(file_foto.read(), caption=f"Evidencia física del Pedido {viaje['num_pedido']}", width=350)
                        else:
                            st.warning("⚠️ El flete está marcado como entregado, pero el archivo físico de la foto no se localizó en el servidor o no se tomó la foto.")
                            
                else:
                    st.error(f"❌ No se encontró ningún despacho activo o histórico que coincida con: '{dato_busqueda}'")
                    st.info("💡 Consejo: Verifique que no falte ningún número o intente buscando solo el número de factura.")
                    
            except Exception as e:
                st.error(f"❌ Error al procesar el rastreo del despacho: {e}")
    #
    # =========================================================================
    # 📌 SECCIÓN DE AYUDA Y SOPORTE EN LA BARRA LATERAL
    # =========================================================================
    with st.sidebar:
        st.write("---")
        st.caption("⚙️ DOCUMENTACIÓN Y SOPORTE EXPREX")
        
        # Un expander dentro del sidebar para que no ocupe espacio visual directo
        with st.expander("❓ Manual de Uso", expanded=False):
            st.markdown("""
            **Guía Rápida de Uso:**
            
            * 📊 **Monitoreo:** Revise sus despachos en tiempo real desde la pestaña principal.
            * 📋 **Detalles:** Haga clic en cualquier viaje para ver el peso (`peso_carga_kg`) y número de pedido.
            * 🔍 **Filtro Mensual:** Si busca fletes pasados, recuerde cambiar el mes en el selector superior.
            * 🔄 **Sincronización:** Los datos provienen directamente del centro logístico. Use el botón de actualización si realiza cambios.
            
            ---
            💬 **¿Problemas con la App?**  
            Comunícate de inmediato con el administrador del sistema para reportar fallas o solicitar soporte técnico.
            """)
            
            # Pie de página sutil con la versión que congelamos con Engrampa
            mostrar_version_de_la_app()
            #st.caption("ExpreX v1.7.5 • 2026 🚛")

        # --- OPCIÓN 2: MARCO LEGAL Y OPERATIVO ---
        with st.expander("📄 Marco Legal y Políticas", expanded=False):
            st.markdown("""
            ### Contrato de Uso y Condiciones de Servicio
            *ExpreX Logística — v1.7.8 (2026)*
            
            Al utilizar esta plataforma, usted acepta las siguientes políticas operativas:
            
            ---
            
            #### 1. Cuentas y Accesos
            El acceso al panel se otorga exclusivamente a personal autorizado por la empresa contratante. Está prohibido compartir credenciales con terceros.
            
            #### 2. Solicitud y Cancelación de Fletes
            * **Tiempos de Solicitud:** Todo flete debe programarse en el sistema con un mínimo de **24 horas** de anticipación.
            * **Cancelaciones:** Válidas sin penalización antes de que el vehículo cambie a estatus *'En Ruta'*.
            
            #### 3. Responsabilidad sobre la Carga
            La empresa se hace responsable de la mercancía desde el enganche y salida del origen hasta la entrega en destino, conforme a las leyes de transporte terrestre vigentes.
            
            #### 4. Tiempos de Espera (Demoras)
            El servicio incluye **2 horas libres** para la carga en origen y **2 horas libres** para la descarga en destino. Excedido este tiempo, se aplicará la tarifa de demoras estándar contractual.
            
            #### 5. Uso de Datos y Privacidad
            Los volúmenes de carga, rutas y datos de facturación son tratados bajo estricta confidencialidad comercial.
            
            ---
            *El uso continuado de la aplicación ExpreX implica la aceptación total de estos términos.*
            """)

        # --- TÉRMINOS Y CONDICIONES DESDE TERMINOS.TXT ---
        with st.expander("📄 Términos y Condiciones", expanded=False):
            # Mostramos el contenido exacto del archivo txt en pantalla
            st.markdown(texto_legal_choferes)

        st.markdown("---")

        # =========================================================================
        # ⚙️ CAMBIO DEL BOTÓN DE SOPORTE POR EL LINK_BUTTON DINÁMICO
        # =========================================================================
        #import urllib.parse

        # 1. Obtenemos el teléfono del chofer logueado (si está en session_state, si no usamos el tuyo por defecto)
        #telefono_chofer = st.session_state.get('usuario_telefono', '584140335554')
        
        # 2. Armamos y codificamos el mensaje
        #mensaje_soporte = "Hola, soy chofer de ExpreX y necesito soporte técnico con mi usuario en la aplicación de Exprex Logística."
        #mensaje_codificado = urllib.parse.quote(mensaje_soporte)
        
        # 3. Generamos la URL
        #url_whatsapp = f"https://wa.me/{telefono_chofer}?text={mensaje_codificado}"

        # 4. Colocamos el link_button directo en el sidebar
        #st.link_button("❓ Soporte", url=url_whatsapp, use_container_width=True)

        # =========================================================================

        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario_cedula = ""
            st.session_state.usuario_nombre = ""
            st.session_state.usuario_rol = ""
            st.session_state.cliente_id = None
            st.session_state.vista_login = "login"
            st.rerun()

        # Pequeño pie de página unificado abajo de los dos módulos
    #mostrar_version_de_la_app()
       