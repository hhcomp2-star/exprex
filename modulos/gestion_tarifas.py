import streamlit as st
import pandas as pd

from modulos.utils import obtener_conexion_db



def seccion_tarifas_admin():
    st.header("⚙️ Gestión de Tarifas Tentativas")
    st.write("Administra las distancias y tarifas estructuradas por Cliente y sus respectivas Sucursales.")

    tab1, tab2 = st.tabs(["🔎 Ver y Buscar Tarifas", "➕ Agregar / Modificar Tarifa"])

    # --- CARGA DE CLIENTES (Para ambos Tabs) ---
    conn = None
    dict_clientes = {}
    try:
        conn = obtener_conexion_db()
        df_cli = pd.read_sql("SELECT id_cliente, razon_social FROM clientes ORDER BY razon_social ASC", conn)
        dict_clientes = dict(zip(df_cli['razon_social'], df_cli['id_cliente']))
    except Exception as e:
        st.error(f"Error cargando los clientes: {e}")
    finally:
        if conn is not None:
            conn.close()

    # --- TAB 1: BUSCADOR GENERAL ---
    with tab1:
        st.subheader("Buscador de Tarifas por Cliente")
        
        col_filtro1, col_filtro2 = st.columns(2)
        with col_filtro1:
            cliente_ver = st.selectbox("Filtrar por Cliente:", ["Todos"] + list(dict_clientes.keys()), key="cli_ver")
        with col_filtro2:
            busqueda = st.text_input("Buscar zona/destino:", placeholder="Ej. Valencia, Caracas...").strip()
        
        query_base = """
            SELECT c.razon_social AS "Cliente",
                   s.nombre_agencia AS "Origen (Sucursal)",
                   t.zona AS "Destino (Zona)", 
                   t.kilometros_estimados AS "Km Aprox.", 
                   t.monto_normal AS "Normal ($)",
                   t.monto_express AS "Express ($)",
                   t.observaciones AS "Observaciones"
            FROM tarifas_tentativas t
            JOIN sucursales s ON t.id_sucursal = s.id_sucursal
            JOIN clientes c ON s.id_cliente = c.id_cliente
        """
        
        conn = None
        df = pd.DataFrame()
        condiciones = []
        parametros = []
        
        if cliente_ver != "Todos":
            condiciones.append("c.id_cliente = %s")
            parametros.append(dict_clientes[cliente_ver])
        if busqueda:
            condiciones.append("(t.zona ILIKE %s OR s.nombre_agencia ILIKE %s)")
            parametros.extend([f"%{busqueda}%", f"%{busqueda}%"])
            
        if condiciones:
            query = query_base + " WHERE " + " AND ".join(condiciones) + " ORDER BY c.razon_social, s.nombre_agencia, t.zona ASC"
        else:
            query = query_base + " ORDER BY c.razon_social, s.nombre_agencia, t.zona ASC"
            
        try:
            conn = obtener_conexion_db()
            df = pd.read_sql(query, conn, params=parametros if parametros else None)
        except Exception as e:
            st.error(f"❌ Error al consultar las tarifas: {e}")
        finally:
            if conn is not None:
                conn.close()

        if not df.empty:
            st.dataframe(
                df.style.format({
                    "Km Aprox.": "{:.1f} Km",
                    "Normal ($)": "${:.2f}",
                    "Express ($)": "${:.2f}"
                }),
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning("No se encontraron tarifas registradas que coincidan con los filtros.")

    # --- TAB 2: REGISTRAR / MODIFICAR TARIFA CON BOTÓN CALCULAR ---
    with tab2:
        st.subheader("Registrar o Actualizar Tarifa")
        st.info("Selecciona el cliente y sucursal. Ingresa los kilómetros y presiona 'Calcular' antes de guardar si deseas usar la fórmula estándar.")
        
        # 1. Selección del Cliente
        cliente_sel = st.selectbox("1. Seleccione el Cliente:", list(dict_clientes.keys()), key="cli_form")
        id_cliente_sel = dict_clientes[cliente_sel]
        
        # 2. Carga de Sucursales
        conn = None
        dict_sucursales_form = {}
        try:
            conn = obtener_conexion_db()
            df_suc_form = pd.read_sql(
                "SELECT id_sucursal, nombre_agencia, ciudad FROM sucursales WHERE id_cliente = %s AND activa = 'Sí' ORDER BY nombre_agencia ASC", 
                conn, 
                params=(id_cliente_sel,)
            )
            df_suc_form['etiqueta'] = df_suc_form['nombre_agencia'] + " (" + df_suc_form['ciudad'] + ")"
            dict_sucursales_form = dict(zip(df_suc_form['etiqueta'], df_suc_form['id_sucursal']))
        except Exception as e:
            st.error(f"Error al cargar las sucursales de este cliente: {e}")
        finally:
            if conn is not None:
                conn.close()
                
        # 3. Interfaz de registro
        if dict_sucursales_form:
            sucursal_sel = st.selectbox("2. Sucursal de Origen:", list(dict_sucursales_form.keys()), key="suc_form")
            id_suc_form = dict_sucursales_form[sucursal_sel]
            
            nueva_zona = st.text_input("3. Zona / Ciudad de Destino:", placeholder="Ej. Zona Industrial Valencia", key="zona_form").strip()
            
            # Inicializamos variables en el session_state si no existen
            if "monto_normal_val" not in st.session_state:
                st.session_state.monto_normal_val = 25.0
            if "monto_express_val" not in st.session_state:
                st.session_state.monto_express_val = 40.0

            col_km, col_btn = st.columns([2, 1])
            with col_km:
                nuevos_km = st.number_input("Distancia Estimada (Km):", min_value=0.1, value=10.0, step=1.0, format="%.1f", key="km_form")
            
            with col_btn:
                st.write("") # Espaciador para alinear con el input
                st.write("")
                if st.button("🧮 Calcular Tarifas", use_container_width=True):
                    # Aplicamos la regla del mínimo logístico de 8 Km
                    km_para_calculo = max(8.0, nuevos_km)
                    st.session_state.monto_normal_val = km_para_calculo * 2.5
                    st.session_state.monto_express_val = km_para_calculo * 4.0
                    st.success(f"Calculado sobre {km_para_calculo:.1f} Km (Normal: ${st.session_state.monto_normal_val:.2f} | Express: ${st.session_state.monto_express_val:.2f})")

            col1, col2 = st.columns(2)
            with col1:
                monto_n = st.number_input("Tarifa Normal ($):", min_value=0.0, value=st.session_state.monto_normal_val, step=1.0, format="%.2f", key="input_normal")
            with col2:
                monto_e = st.number_input("Tarifa Express ($):", min_value=0.0, value=st.session_state.monto_express_val, step=1.0, format="%.2f", key="input_express")
            
            nuevas_observaciones = st.text_area("Notas / Observaciones del tramo:", placeholder="Ej. Requiere pernocta, control de retorno, etc.", key="obs_form")
            
            # Botón de guardado
            if st.button("💾 Guardar o Actualizar Tarifa", type="primary", use_container_width=True):
                if not nueva_zona:
                    st.error("❌ Debes especificar una zona de destino para el flete.")
                else:
                    query_upsert = """
                        INSERT INTO tarifas_tentativas (id_sucursal, zona, kilometros_estimados, monto_normal, monto_express, observaciones, fecha_actualizacion)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (id_sucursal, zona) 
                        DO UPDATE SET 
                            kilometros_estimados = EXCLUDED.kilometros_estimados,
                            monto_normal = EXCLUDED.monto_normal,
                            monto_express = EXCLUDED.monto_express,
                            observaciones = EXCLUDED.observaciones,
                            fecha_actualizacion = CURRENT_TIMESTAMP;
                    """
                    conn = None
                    try:
                        conn = obtener_conexion_db()
                        with conn.cursor() as cur:
                            cur.execute(query_upsert, (id_suc_form, nueva_zona, nuevos_km, monto_n, monto_e, nuevas_observaciones))
                        conn.commit()
                        st.success(f"✅ Tarifa guardada con éxito para **{cliente_sel}** | Ruta: *{sucursal_sel} ➡️ {nueva_zona}*")
                    except Exception as e:
                        if conn is not None:
                            conn.rollback()
                        st.error(f"❌ Error al guardar en base de datos: {e}")
                    finally:
                        if conn is not None:
                            conn.close()
        else:
            st.warning(f"⚠️ El cliente **{cliente_sel}** no tiene sucursales activas registradas. Agrégalas primero antes de definir sus tarifas.")


def seccion_tarifas_clientes(id_cliente_autenticado):
    st.subheader("🔎 Mis Tarifas y Rutas Frecuentes")
    st.write("Consulta los tramos preconfigurados, distancias y costos estimados desde tus sucursales.")

    # Filtro rápido de texto para el cliente
    busqueda_destino = st.text_input("Buscar por sucursal de origen o zona de destino:", placeholder="Ej. Centro de distribución, Valencia...").strip()

    query = """
        SELECT s.nombre_agencia AS "Origen (Sucursal)",
               s.ciudad AS "Ciudad Origen",
               t.zona AS "Destino (Zona)", 
               t.kilometros_estimados AS "Km Aprox.", 
               t.monto_normal AS "Tarifa Normal ($)",
               t.monto_express AS "Tarifa Express ($)",
               t.observaciones AS "Notas/Condiciones"
        FROM tarifas_tentativas t
        JOIN sucursales s ON t.id_sucursal = s.id_sucursal
        WHERE s.id_cliente = %s AND s.activa = 'Sí'
    """
    
    parametros = [id_cliente_autenticado]
    
    if busqueda_destino:
        query += " AND (t.zona ILIKE %s OR s.nombre_agencia ILIKE %s)"
        parametros.extend([f"%{busqueda_destino}%", f"%{busqueda_destino}%"])
        
    query += " ORDER BY s.nombre_agencia, t.zona ASC"

    conn = None
    df_tarifas = pd.DataFrame()
    
    try:
        conn = obtener_conexion_db()
        df_tarifas = pd.read_sql(query, conn, params=parametros)
    except Exception as e:
        st.error(f"Error al cargar el catálogo de tarifas: {e}")
    finally:
        if conn is not None:
            conn.close()

    # Despliegue de los datos
    if not df_tarifas.empty:
        # Combinamos Nombre + Ciudad para hacer una columna de Origen súper limpia si lo deseas,
        # o dejamos que Streamlit muestre ambas.
        st.dataframe(
            df_tarifas.style.format({
                "Km Aprox.": "{:.1f} Km",
                "Tarifa Normal ($)": "${:.2f}",
                "Tarifa Express ($)": "${:.2f}"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No tienes tarifas asignadas para los criterios seleccionados en este momento. Si necesitas cotizar una nueva ruta, contacta a operaciones de ExpreX.")
