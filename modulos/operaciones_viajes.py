import streamlit as st
import pandas as pd
import time
import os  
import sys
import datetime
import datetime as dt
from datetime import datetime


# 🔍 CONTROL DE RUTAS CRÍTICO (Evita fallas de importación en subcarpetas de Railway)
ruta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ruta_raiz not in sys.path:
    sys.path.insert(0, ruta_raiz)

# Importamos el pool global de Postgres y la pestaña correspondiente
from modulos.utils import obtener_conexion_db
from modulos.asignacion_previa import renderizar_pestana_asignar

import streamlit as st
import pandas as pd
from modulos.utils import obtener_conexion_db  # O como tengas tu importación aquí
# =============================================================================================================
# Gestión de tarifas
# =============================================================================================================

def seccion_tarifas_admin():
    st.header("⚙️ Gestión de Tarifas Tentativas")
    st.write("Administra el listado de precios de fletes por zona geográfica.")

    tab1, tab2 = st.tabs(["🔎 Ver y Buscar Tarifas", "➕ Agregar / Modificar Tarifa"])

    # --- TAB 1: BUSCADOR ---
    with tab1:
        busqueda = st.text_input("Buscar zona existente:", placeholder="Ej. Valencia...").strip()
        query_base = "SELECT zona AS 'Zona', monto_aproximado AS 'Precio ($)', observaciones AS 'Observaciones', fecha_actualizacion AS 'Última Actualización' FROM tarifas_tentativas"
        
        conn = None
        df = pd.DataFrame()
        try:
            conn = obtener_conexion_db()
            if busqueda:
                query = query_base + " WHERE zona ILIKE %s ORDER BY zona ASC"
                df = pd.read_sql(query, conn, params=(f"%{busqueda}%",))
            else:
                query = query_base + " ORDER BY zona ASC"
                df = pd.read_sql(query, conn)
        except Exception as e:
            st.error(f"❌ Error al consultar las tarifas: {e}")
        finally:
            if conn is not None:
                conn.close()

        if not df.empty:
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.warning("No hay tarifas registradas que coincidan.")

    # --- TAB 2: AGREGAR/MODIFICAR ---
    with tab2:
        st.subheader("Registrar o Actualizar Destino")
        with st.form("nueva_tarifa_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nueva_zona = st.text_input("Nombre de la Zona/Destino:", placeholder="Ej. Barquisimeto").strip()
            with col2:
                nuevo_monto = st.number_input("Monto aproximado ($):", min_value=0.0, step=5.0, format="%.2f")
            
            nuevas_observaciones = st.text_area("Notas adicionales:", placeholder="Tarifa base. Puede variar según volumen.")
            boton_guardar = st.form_submit_button("Guardar Cambios")
            
            if boton_guardar:
                if not nueva_zona:
                    st.error("❌ El nombre de la zona no puede estar vacío.")
                else:
                    query_upsert = """
                        INSERT INTO tarifas_tentativas (zona, monto_aproximado, observaciones, fecha_actualizacion)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (zona) 
                        DO UPDATE SET 
                            monto_aproximado = EXCLUDED.monto_aproximado,
                            observaciones = EXCLUDED.observaciones,
                            fecha_actualizacion = CURRENT_TIMESTAMP;
                    """
                    conn = None
                    try:
                        conn = obtener_conexion_db()
                        with conn.cursor() as cur:
                            cur.execute(query_upsert, (nueva_zona, nuevo_monto, nuevas_observaciones))
                        conn.commit()
                        st.success(f"✅ ¡Guardado! '{nueva_zona}' ahora está en ${nuevo_monto:.2f}.")
                    except Exception as e:
                        if conn is not None:
                            conn.rollback()
                        st.error(f"❌ Error al guardar: {e}")
                    finally:
                        if conn is not None:
                            conn.close()
# ==============================================================================================================
# Función principal
# ==============================================================================================================

def mostrar_modulo_operaciones():
    st.markdown("### 🎯 Control Operativo de Rutas")
    st.write("Seguimiento en tiempo real de unidades, despachos, contingencias e historial consolidado.")
    
    # Pestañas de control operativo
    tab_asignar, tab_despacho, tab_carretera, tab_contingencia, tab_historial, tab_gestion_tarifas = st.tabs([
        "📋 Solicitudes / Por Asignar",
        "📝 Registrar Despacho",
        "🚚 Unidades en Carretera", 
        "🔄 Modificar Viaje (Contingencias)",
        "📊 Historial y Auditoría",
        "💰 Gestión de Tarifas"
    ])
    
    # =========================================================================
    # LÓGICA DE LA PESTAÑA SOLICITUDES POR ASIGNAR
    # =========================================================================
    with tab_asignar:
        # 🛠️ Se elimina el argumento 'exprex.db' ya que la pestaña interna 
        # usará directamente el pool centralizado de PostgreSQL.
        renderizar_pestana_asignar()        
    #
    # =========================================================================
    # PESTAÑA 2: PROCESAR Y REGISTRAR DESPACHO (MIGRADO A POSTGRESQL)
    # =========================================================================
    with tab_despacho:
        st.write("### 🎫 Panel de Despacho de Fletes Solicitados")
        st.info("Seleccione una solicitud asignada para completar la información logística final y emitir la orden de salida.")
        
        try:
            with obtener_conexion_db() as conexion:
                # 1. Traer conductores activos usando PostgreSQL y guardarlos firmemente en session_state
                df_cb_conductores = pd.read_sql_query(
                    "SELECT cedula, nombre FROM usuarios WHERE rol = 'Conductor' AND activo = 'Sí'", 
                    conexion
                )
                # Forzamos que la columna 'cedula' sea string en Postgres para evitar conflictos de tipo de datos
                df_cb_conductores['cedula'] = df_cb_conductores['cedula'].astype(str).str.strip()
                st.session_state['df_cb_conductores'] = df_cb_conductores
                
                # 2. Filtramos para traer SOLO solicitudes con conductor pre-asignado
                df_solicitudes_pendientes = pd.read_sql_query('''
                    SELECT v.*, c.razon_social 
                    FROM viajes v
                    JOIN clientes c ON v.id_cliente = c.id_cliente
                    WHERE v.estatus_viaje = 'Solicitado'
                      AND v.cedula_conductor IS NOT NULL
                    ORDER BY CASE WHEN v.tipo_viaje = 'Express' THEN 1 ELSE 2 END, v.id_viaje DESC
                ''', conexion)
                
        except Exception as e:
            st.error(f"Error en comunicación de base de datos en despacho: {e}")
            df_solicitudes_pendientes = pd.DataFrame()

        if df_solicitudes_pendientes.empty:
            st.success("✅ ¡Al día! No existen solicitudes listas para despacho definitivo en este momento.")
        else:
            # MAPEO SEGURO: Convertimos el DataFrame en un diccionario de Python puro
            dicc_despacho = {}
            for _, fila in df_solicitudes_pendientes.iterrows():
                prefijo = "🚨 [EXPRESS]" if fila['tipo_viaje'] == 'Express' else "🕒 [Normal]"
                dicc_despacho[fila['id_viaje']] = f"{prefijo} Flete N° {fila['id_viaje']} - {fila['razon_social']} (Pedido: {fila['num_pedido']})"

            lista_solicitudes_ids = list(dicc_despacho.keys())
            
            id_viaje_seleccionado = st.selectbox(
                "🔍 Seleccione la Solicitud a Despachar:", 
                options=lista_solicitudes_ids, 
                format_func=lambda x: dicc_despacho.get(x, f"Flete N° {x}")
            )

            # ESCUDO DEFENSIVO ANTES DE MOSTRAR DETALLES
            coincidencia_despacho = df_solicitudes_pendientes[df_solicitudes_pendientes['id_viaje'] == id_viaje_seleccionado]
            
            if coincidencia_despacho.empty:
                st.warning("🔄 Sincronizando datos de despacho...")
            else:
                viaje_sel = coincidencia_despacho.iloc[0]
                
                # VISTA DE AUDITORÍA: Una sola tarjeta informativa limpia
                st.markdown(f"""
                <div style="background-color:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {'#ff4b4b' if viaje_sel['tipo_viaje']=='Express' else '#3b82f6'};">
                    <h4>📦 Datos Registrados por el Cliente y Asignación</h4>
                    <p><b>Cliente:</b> {viaje_sel['razon_social']} | <b>Pedido:</b> {viaje_sel['num_pedido']}</p>
                    <p><b>Origen:</b> {viaje_sel['origen']} | <b>Destino:</b> {viaje_sel['destino']}</p>
                    <p><b>Tipo de Carga:</b> {viaje_sel['tipo_material']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("")
                
                # Enlace interactivo a mapas
                destino_solicitado = viaje_sel['destino']
                direccion_url = str(destino_solicitado).replace(" ", "+")
                url_maps = f"https://www.google.com/maps/search/?api=1&query={direccion_url}"
                st.markdown(f"🗺️ [**Click aquí para ubicar '{destino_solicitado}' en Google Maps**]({url_maps})")
                st.caption("💡 *Haga clic derecho en el destino para extraer las coordenadas geográficas exactas e ingresarlas abajo.*")

                # FORMULARIO DE DESPACHO INTERACTIVO
                st.write("#### 🛠️ Completar Información Logística de Salida")
                
                # =========================================================================
                # SANEAMIENTO DE CONDUCTORES (OPTIMIZADO Y PROTEGIDO)
                # =========================================================================
                lista_cedulas_choferes = []
                mapeo_conductores = {}

                # Buscamos de forma robusta la fuente de datos cargada de Postgres
                if 'df_cb_conductores' in st.session_state and st.session_state['df_cb_conductores'] is not None:
                    df_conductores_seguro = st.session_state['df_cb_conductores']
                elif 'df_cb_conductores' in locals() and locals()['df_cb_conductores'] is not None:
                    df_conductores_seguro = locals()['df_cb_conductores']
                else:
                    df_conductores_seguro = pd.DataFrame(columns=['cedula', 'nombre'])

                # Generamos listas y diccionarios de mapeo
                if not df_conductores_seguro.empty:
                    lista_cedulas_choferes = df_conductores_seguro['cedula'].astype(str).str.strip().tolist()
                    mapeo_conductores = dict(zip(
                        df_conductores_seguro['cedula'].astype(str).str.strip(), 
                        df_conductores_seguro['nombre']
                    ))

                # Buscamos el índice preasignado de forma segura asegurando la comparación de texto
                index_chofer_preasig = 0
                try:
                    if 'viaje_sel' in locals() and viaje_sel['cedula_conductor'] is not None:
                        chofer_preasig = str(viaje_sel['cedula_conductor']).strip()
                        if chofer_preasig in lista_cedulas_choferes:
                            index_chofer_preasig = lista_cedulas_choferes.index(chofer_preasig)
                except (ValueError, KeyError):
                    index_chofer_preasig = 0
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Validamos si hay conductores usando la lista nativa
                    if lista_cedulas_choferes:
                        conductor_seleccionado = st.selectbox(
                            "👤 Conductor Asignado para la Ruta",
                            options=lista_cedulas_choferes,
                            index=index_chofer_preasig,
                            format_func=lambda x: mapeo_conductores.get(x, "Desconocido")
                        )
                    else:
                        st.warning("⚠️ No hay conductores activos disponibles.")
                        conductor_seleccionado = None

                    from datetime import date
                    fecha_despacho = st.date_input("📅 Fecha de Salida Real", value=date.today()).strftime("%Y-%m-%d")
                    num_factura = st.text_input("🧾 Número de Factura / Control Interno (Opcional)").strip().upper()

                with col2:
                    col_dest_lat, col_dest_lon = st.columns(2)
                    with col_dest_lat:
                        lat_input = st.text_input("🌐 Latitud Destino", value="0.0").strip()
                    with col_dest_lon:
                        lon_input = st.text_input("🌐 Longitud Destino", value="0.0").strip()
                    
                    distancia_calculada = float(viaje_sel['distancia_km']) if viaje_sel['distancia_km'] else 0.0
                    
                    # Validamos coordenadas y aseguramos que el ID del viaje no sea None ni cero
                    if (lat_input != "0.0" and lon_input != "0.0" and 
                        lat_input != "" and lon_input != "" and 
                        id_viaje_seleccionado is not None and str(id_viaje_seleccionado).strip() != "0"):
                        
                        try:
                            from geopy.distance import geodesic
                            id_viaje_seguro = int(id_viaje_seleccionado)
                            
                            # BUSQUEDA DIRECTA EN POSTGRESQL
                            with obtener_conexion_db() as conexion:
                                with conexion.cursor() as cursor:
                                    cursor.execute("""
                                        SELECT s.latitud, s.longitud 
                                        FROM sucursales s
                                        JOIN viajes v ON v.id_sucursal_origen = s.id_sucursal
                                        WHERE v.id_viaje = %s
                                    """, (id_viaje_seguro,))
                                    
                                    resultado = cursor.fetchone()

                            if resultado:
                                lat_origen_dinamico = float(resultado[0])
                                lng_origen_dinamico = float(resultado[1])
                                
                                punto_origen = (lat_origen_dinamico, lng_origen_dinamico)
                                punto_destino = (float(lat_input), float(lon_input))
                                
                                dist_lineal = geodesic(punto_origen, punto_destino).kilometers
                                distancia_calculada = round(dist_lineal * 1.3, 2)
                            
                        except Exception:
                            pass
                    
                    distancia_km = st.number_input(
                        "📏 Distancia Real del Mapa (Km):", 
                        min_value=0.0, 
                        value=float(distancia_calculada), 
                        step=0.1
                    )

                # --- CÁLCULO INFORMATIVO DE COSTOS EN PANTALLA ---
                precio_por_km = 4.0 if viaje_sel['tipo_viaje'] == "Express" else 2.50
                distancia_a_cobrar = max(distancia_km, 8.0) if distancia_km > 0 else 0.0
                monto_calculado = distancia_a_cobrar * precio_por_km
                
                if distancia_km > 0:
                    st.success(f"💰 **Monto Referencial del Flete: ${monto_calculado:,.2f} USD** (Mínimo de 8 Km aplicado si corresponde)")

                _, sub_col_centro, _ = st.columns([1, 2, 1])
                with sub_col_centro:
                    boton_despachar = st.button("🚀 Confirmar Despacho y Pasar a 'Por Salir'", use_container_width=True, type="primary")
                
                if boton_despachar:
                    if distancia_km <= 0:
                        st.error("⚠️ Debe ingresar la distancia en kilómetros calculada para la ruta.")
                    elif id_viaje_seleccionado is None or str(id_viaje_seleccionado).strip() == "" or str(id_viaje_seleccionado) == "0":
                        st.error("❌ Error: No hay un ID de viaje válido seleccionado para despachar.")
                    else:
                        try:
                            id_viaje_seguro = int(id_viaje_seleccionado)
                            factura_segura = str(num_factura).strip() if num_factura else ""
                            
                            if conductor_seleccionado:
                                conductor_seguro = str(conductor_seleccionado).strip()
                            else:
                                if 'viaje_sel' in locals() and viaje_sel['cedula_conductor']:
                                    conductor_seguro = str(viaje_sel['cedula_conductor']).strip()
                                else:
                                    conductor_seguro = None
                            
                            # ESCRITURA EN BASE DE DATOS CENTRALIZADA (POSTGRESQL)
                            with obtener_conexion_db() as conexion:
                                with conexion.cursor() as cursor:
                                    cursor.execute("""
                                        UPDATE viajes 
                                        SET cedula_conductor = %s,
                                            fecha_despacho = %s,
                                            distancia_km = %s,
                                            monto_flete_usd = %s,
                                            num_factura = %s,
                                            latitud_entrega = %s,
                                            longitud_entrega = %s,
                                            estatus_viaje = 'Por Salir'
                                        WHERE id_viaje = %s
                                    """, (
                                        conductor_seguro if conductor_seguro else None,
                                        fecha_despacho, 
                                        float(distancia_km), 
                                        float(monto_calculado),
                                        factura_segura,
                                        float(lat_input) if lat_input else 0.0, 
                                        float(lon_input) if lon_input else 0.0,
                                        id_viaje_seguro
                                    ))
                                    conexion.commit()
                            
                            st.success(f"🎉 Flete N° {id_viaje_seguro} despachado con éxito. Cambiado a estatus 'Por Salir'.")
                            time.sleep(2)
                            st.rerun()
                        except ValueError:
                            st.error("❌ Error de tipo: El ID del viaje o los montos numéricos no tienen un formato válido.")
                        except Exception as e:
                            st.error(f"❌ Error crítico al actualizar despacho: {e}")
    #
    # =========================================================================
    # PESTAÑA 3: UNIDADES EN CARRETERA (MIGRADO A POSTGRESQL)
    # =========================================================================
    with tab_carretera:
        st.write("### 🛣️ Monitoreo de Unidades Activas")
        st.write("### 🚚 Control de Fletes Activos")
        try:
            with obtener_conexion_db() as conexion:
                # 🎯 ALIAS EN POSTGRESQL: Deben usar comillas dobles para nombres de columna
                sql_consulta = """
                    SELECT 
                        v.id_viaje AS "Código",
                        v.estatus_viaje AS "Estado Actual",
                        v.num_pedido AS "Pedido",
                        v.num_factura AS "Factura",
                        c.razon_social AS "Cliente",
                        s.nombre_agencia AS "Origen (Agencia)",
                        v.cliente_solicitante AS "Solicitante",
                        v.destino AS "Destino",
                        u.nombre AS "Conductor",
                        v.fecha_despacho AS "Salida",
                        v.tipo_viaje AS "Tipo",
                        v.distancia_km AS "Km Reales",
                        v.monto_flete_usd AS "Flete USD",
                        v.observaciones AS "Notas"
                    FROM viajes v
                    JOIN clientes c ON v.id_cliente = c.id_cliente
                    LEFT JOIN sucursales s ON v.id_sucursal_origen = s.id_sucursal
                    JOIN usuarios u ON v.cedula_conductor = u.cedula
                    WHERE v.estatus_viaje IN ('Por Salir', 'En Ruta')
                      AND v.id_viaje IS NOT NULL
                    ORDER BY v.id_viaje DESC
                """
                df_viajes = pd.read_sql_query(sql_consulta, conexion)
            
            if not df_viajes.empty:
                st.dataframe(df_viajes, use_container_width=True, hide_index=True)
                st.markdown("---")
                
                # 1️⃣ FUNCIÓN DE FORMATO SEGURA: Evita IndexError en tiempo de ejecución
                def formatear_viaje_selectbox(id_buscar):
                    if id_buscar is None:
                        return ""
                    filtro = df_viajes[df_viajes['Código'] == id_buscar]
                    if not filtro.empty:
                        pedido = filtro['Pedido'].values[0] if pd.notna(filtro['Pedido'].values[0]) else "S/P"
                        cliente = filtro['Cliente'].values[0] if pd.notna(filtro['Cliente'].values[0]) else "..."
                        return f"📦 Viaje #{id_buscar} - Pedido: {pedido} [{cliente}]"
                    return f"📦 Viaje #{id_buscar}"

                # Buscador desplegable de viajes
                id_seleccionado = st.selectbox(
                    "Seleccione el Viaje a Procesar:", 
                    options=df_viajes['Código'].tolist(),
                    format_func=formatear_viaje_selectbox
                )
                
                # 2️⃣ VALIDACIÓN E INICIALIZACIÓN DE ID SEGURO PARA PYLANCE
                if id_seleccionado is None or str(id_seleccionado).strip() == "" or str(id_seleccionado) == "0":
                    st.warning("⚠️ Seleccione un ID de viaje válido para operar.")
                else:
                    # Garantizamos el tipo entero para todo el bloque interno
                    id_viaje_seguro = int(id_seleccionado)
                    
                    fila_seleccionada = df_viajes[df_viajes['Código'] == id_viaje_seguro]
                    if not fila_seleccionada.empty:
                        estado_actual = fila_seleccionada['Estado Actual'].values[0]
                    else:
                        estado_actual = "Por Salir"
                        
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if estado_actual == "Por Salir":
                            if st.button("🚀 Dar Salida (Marcar 'En Ruta')", use_container_width=True):
                                try:
                                    with obtener_conexion_db() as conexion:
                                        with conexion.cursor() as cursor:
                                            cursor.execute(
                                                "UPDATE viajes SET estatus_viaje = 'En Ruta' WHERE id_viaje = %s", 
                                                (id_viaje_seguro,)
                                            )
                                            conexion.commit()
                                    st.success("¡Unidad en carretera!")
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error al dar salida: {e}")
                                
                    with col_btn2:
                        if st.button("🏁 Ir al Cierre (Completar Viaje)", use_container_width=True, type="primary"):
                            st.session_state["cerrando_viaje"] = id_viaje_seguro

                    with col_btn3:
                        if estado_actual == "Por Salir":
                            if st.button("🗑️ Anular Orden (Borrar)", use_container_width=True, type="secondary"):
                                try:
                                    with obtener_conexion_db() as conexion:
                                        with conexion.cursor() as cursor:
                                            cursor.execute("DELETE FROM viajes WHERE id_viaje = %s", (id_viaje_seguro,))
                                            conexion.commit()
                                    st.success("🛑 Orden duplicada eliminada correctamente.")
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Error al anular: {e}")

                    # Manejo del estado del cierre
                    if st.session_state.get("cerrando_viaje") == id_viaje_seguro:
                        st.markdown("---")
                        archivo_foto = st.file_uploader("Suba la foto de la factura firmada:", type=["jpg", "jpeg", "png"])
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button("❌ Cancelar Cierre", use_container_width=True):
                                st.session_state["cerrando_viaje"] = None
                                st.rerun()
                        with c2:
                            if st.button("💾 Confirmar Entrega y Guardar", use_container_width=True, type="primary"):
                                ruta_foto_guardada = ""
                                if archivo_foto is not None:
                                    if not os.path.exists("fotos_entregas"):
                                        os.makedirs("fotos_entregas")
                                    ext = archivo_foto.name.split(".")[-1]
                                    ruta_foto_guardada = f"fotos_entregas/viaje_{id_viaje_seguro}_evidencia.{ext}"
                                    with open(ruta_foto_guardada, "wb") as f:
                                        f.write(archivo_foto.getbuffer())
                                
                                try:
                                    with obtener_conexion_db() as conexion:
                                        with conexion.cursor() as cursor:
                                            
                                            # 1️⃣ Traemos la información financiera base del flete
                                            cursor.execute("""
                                                SELECT monto_flete_usd, cedula_conductor, distancia_km, tipo_viaje 
                                                FROM viajes 
                                                WHERE id_viaje = %s
                                            """, (id_viaje_seguro,))
                                            res_v = cursor.fetchone()
                                            
                                            if res_v:
                                                monto_flete_bd = res_v[0]
                                                cedula_chofer = res_v[1]
                                                distancia_bd = res_v[2]
                                                tipo_viaje = res_v[3]
                                                
                                                # --- SALVAVIDAS CONTRA NONETYPE ---
                                                if monto_flete_bd is not None:
                                                    monto_flete_total = float(monto_flete_bd)
                                                else:
                                                    distancia_km = float(distancia_bd) if distancia_bd is not None else 0.0
                                                    distancia_calculo = max(distancia_km, 8.0) if distancia_km > 0 else 0.0
                                                    tarifa_por_km = 4.0 if tipo_viaje == 'Express' else 2.5
                                                    monto_flete_total = distancia_calculo * tarifa_por_km
                                                
                                                # 2️⃣ Buscamos si el vehículo es propio
                                                cursor.execute("SELECT propio FROM conductores WHERE cedula = %s", (str(cedula_chofer),))
                                                res_c = cursor.fetchone()
                                                es_propio = res_c[0] if res_c and res_c[0] else "No"
                                                
                                                # 3️⃣ Fórmulas Financieras de Liquidación
                                                descuento = monto_flete_total * 0.15
                                                importe_neto = monto_flete_total - descuento
                                                porcentaje_chofer = 0.75 if es_propio == "Sí" else 0.37
                                                pago_chofer = importe_neto * porcentaje_chofer
                                                beneficio_exprex = importe_neto - pago_chofer
                                                
                                                # 4️⃣ Guardado definitivo en PostgreSQL
                                                sql_update = """
                                                    UPDATE viajes 
                                                    SET estatus_viaje = 'Entregado', 
                                                        foto_evidencia = %s, 
                                                        monto_flete_usd = %s,
                                                        descuento_usd = %s,
                                                        importe_neto_usd = %s, 
                                                        pago_chofer_usd = %s, 
                                                        beneficio_exprex_usd = %s  
                                                    WHERE id_viaje = %s
                                                """
                                                cursor.execute(sql_update, (
                                                    str(ruta_foto_guardada), 
                                                    float(monto_flete_total),
                                                    float(descuento), 
                                                    float(importe_neto), 
                                                    float(pago_chofer), 
                                                    float(beneficio_exprex), 
                                                    id_viaje_seguro
                                                ))
                                                conexion.commit()
                                                st.success("🎉 Viaje completado. Cuentas calculadas y registradas con éxito.")
                                                time.sleep(2)
                                            else:
                                                st.error("No se encontraron los datos del viaje para procesar el cierre.")
                                    
                                    st.session_state["cerrando_viaje"] = None
                                    time.sleep(1)
                                    st.rerun()    
                                except Exception as e:
                                    st.error(f"❌ Error crítico en el procesamiento del cierre: {e}")
            else:
                st.info("🟢 No hay viajes activos en este momento ('Por Salir' o 'En Ruta').")
        except Exception as e:
            st.error(f"❌ Error en monitor: {e}")
    #    
    # =========================================================================
    # PESTAÑA 4: CONTROL DE CONTINGENCIAS (MIGRADO A POSTGRESQL)
    # =========================================================================
    with tab_contingencia:
        st.write("### 🔄 Control de Contingencias: Modificar Viaje Activo")
        st.info("Utilice esta sección para resolver imprevistos en ruta (cambio de chofer, modificaciones de destino o datos de entrega).")
    
        try:
            with obtener_conexion_db() as conexion:
                query_viajes = """
                    SELECT v.id_viaje, v.num_pedido, u.nombre AS "Conductor", v.destino, v.estatus_viaje
                    FROM viajes v
                    JOIN usuarios u ON v.cedula_conductor = u.cedula
                    WHERE v.estatus_viaje IN ('Por Salir', 'En Ruta')
                """
                df_viajes_activos = pd.read_sql_query(query_viajes, conexion)
                
                query_choferes = "SELECT cedula, nombre FROM usuarios WHERE rol = 'Conductor' AND activo = 'Sí'"
                df_choferes = pd.read_sql_query(query_choferes, conexion)
        except Exception as e:
            st.error(f"Error al cargar datos de contingencia: {e}")
            df_viajes_activos = pd.DataFrame()
            df_choferes = pd.DataFrame()
        
        if df_viajes_activos.empty:
            st.success("✨ No hay viajes activos en este momento para modificar.")
        else:
            opciones_viajes = ["-- Seleccione el Viaje a Modificar --"] + [
                f"ID: {f['id_viaje']} | Pedido: {f['num_pedido']} | Chofer: {f['Conductor']} ➡️ Destino: {f['destino']} ({f['estatus_viaje']})"
                for _, f in df_viajes_activos.iterrows()
            ]
            
            viaje_seleccionado = st.selectbox("Seleccione el viaje que presenta el imprevisto:", opciones_viajes, key="sb_contingencia_viaje")
            
            if viaje_seleccionado != "-- Seleccione el Viaje a Modificar --":
                id_viaje_mod = int(viaje_seleccionado.split("ID: ")[1].split(" |")[0])
                
                try:
                    with obtener_conexion_db() as conexion:
                        with conexion.cursor() as cursor:
                            cursor.execute("""
                                SELECT cedula_conductor, destino, persona_contacto_entrega, telefono_contacto_entrega, observaciones
                                FROM viajes WHERE id_viaje = %s
                            """, (id_viaje_mod,))
                            datos_actuales = cursor.fetchone()
                except Exception as e:
                    st.error(f"Error al consultar el viaje seleccionado: {e}")
                    datos_actuales = None

                if datos_actuales:
                    ced_chofer_act, destino_act, persona_act, tel_act, obs_act = datos_actuales
                    
                    st.markdown("---")
                    st.markdown(f"#### 🛠️ Formulario de Modificación (Viaje ID #`{id_viaje_mod}`)")
                    
                    with st.form("form_contingencia_viaje", clear_on_submit=False):
                        st.markdown("**1️⃣ Reasignación de Personal y Logística**")
                        
                        lista_cedulas = df_choferes["cedula"].tolist()
                        lista_nombres_choferes = [f"{r['nombre']} (C.I. {r['cedula']})" for _, r in df_choferes.iterrows()]
                        
                        try:
                            idx_chofer = lista_cedulas.index(ced_chofer_act)
                        except ValueError:
                            idx_chofer = 0
                            
                        nuevo_chofer_sel = st.selectbox("Asignar Nuevo Conductor:", lista_nombres_choferes, index=idx_chofer)
                        nueva_cedula_conductor = lista_cedulas[lista_nombres_choferes.index(nuevo_chofer_sel)]
                        
                        st.markdown("---")
                        st.markdown("**2️⃣ Modificación de Destino y Entrega**")
                        nuevo_destino = st.text_input("Dirección de Destino / Entrega:", value=destino_act)
                        nueva_persona_recibe = st.text_input("Persona encargada de recibir:", value=persona_act)
                        nuevo_telefono_recibe = st.text_input("Teléfono de contacto en destino:", value=tel_act)
                        
                        st.markdown("---")
                        st.markdown("**3️⃣ Reporte de Novedad (Bitácora)**")
                        nuevas_observaciones = st.text_area("Motivo del cambio / Observaciones:", value=obs_act)
                        
                        boton_guardar_cambios = st.form_submit_button("🚨 Aplicar Modificaciones de Emergencia")
                    #    
                    if boton_guardar_cambios:
                        if id_viaje_mod is None or str(id_viaje_mod).strip() == "" or str(id_viaje_mod) == "0":
                            st.error("❌ Error: No hay un ID de viaje válido seleccionado para modificar.")
                        else:
                            try:
                                # 1️⃣ CASTEO SEGURO Y PROTECCIÓN CONTRA NULOS (Fuera de la tupla)
                                id_viaje_seguro = int(id_viaje_mod)
                                cedula_segura = str(nueva_cedula_conductor).strip() if nueva_cedula_conductor else ""
                                
                                # Convertimos a texto PRIMERO y luego aplicamos strip si no son None
                                destino_seguro = str(nuevo_destino).strip() if nuevo_destino is not None else ""
                                persona_segura = str(nueva_persona_recibe).strip() if nueva_persona_recibe is not None else ""
                                telefono_seguro = str(nuevo_telefono_recibe).strip() if nuevo_telefono_recibe is not None else ""
                                observaciones_seguras = str(nuevas_observaciones).strip() if nuevas_observaciones is not None else ""
                                
                                # 2️⃣ ESCRITURA EN POSTGRESQL CON VARIABLES SANEADAS
                                with obtener_conexion_db() as conexion:
                                    with conexion.cursor() as cursor:
                                        sql_update_viaje = """
                                            UPDATE viajes 
                                            SET cedula_conductor = %s, 
                                                destino = %s, 
                                                persona_contacto_entrega = %s, 
                                                telefono_contacto_entrega = %s, 
                                                observaciones = %s
                                            WHERE id_viaje = %s
                                        """
                                        cursor.execute(sql_update_viaje, (
                                            cedula_segura,
                                            destino_seguro,
                                            persona_segura,
                                            telefono_seguro,
                                            observaciones_seguras,
                                            id_viaje_seguro
                                        ))
                                        conexion.commit()
                                        
                                st.success(f"✅ ¡Viaje ID #{id_viaje_seguro} modificado y reasignado con éxito!")
                                time.sleep(2)
                                st.rerun()
                            except ValueError:
                                st.error("❌ Error de tipo: El ID del flete a modificar no es un número válido.")
                            except Exception as e:
                                st.error(f"❌ Error al actualizar la contingencia: {e}")
    #
    # =========================================================================
    # PESTAÑA 5: HISTORIAL Y AUDITORÍA (MIGRADO A POSTGRESQL)
    # =========================================================================
    with tab_historial:
        st.subheader("📊 Centro de Consultas y Auditoría de Servicios")
        
        tab_general, tab_consulta_clientes, tab_individual = st.tabs([
            "📋 Historial General (Cuentas)", 
            "Auditoría Individual (Detalles Clientes)",
            "🔍 Auditoría Individual (Detalles Fletes)"
        ])
        
        # Historial general financiero
        with tab_general:
            st.write("#### 🚛 Bitácora Consolidada de Fletes Liquidados")
            try:
                with obtener_conexion_db() as conexion:
                    # 🎯 ALIAS EN POSTGRESQL: Se usan comillas dobles obligatoriamente para nombres de columnas con espacios o caracteres especiales
                    sql_general = """
                        SELECT 
                            v.id_viaje AS "ID Viaje",
                            v.fecha_despacho AS "Fecha",
                            c.razon_social AS "Cliente",
                            v.num_factura AS "N° Factura",
                            v.num_pedido AS "N° Pedido",
                            v.cliente_solicitante AS "Solicitante",
                            v.monto_flete_usd AS "Total ($)",
                            v.descuento_usd AS "Desc ($)",
                            v.importe_neto_usd AS "Importe ($)",
                            v.pago_chofer_usd AS "Chofer ($)",
                            v.beneficio_exprex_usd AS "Beneficio ($)",
                            v.estatus_viaje AS "Estatus"
                        FROM viajes v
                        JOIN clientes c ON v.id_cliente = c.id_cliente
                        ORDER BY v.id_viaje DESC
                    """
                    df_gen = pd.read_sql_query(sql_general, conexion)
                
                if not df_gen.empty:
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Total Fletes", f"{len(df_gen)}")
                    with m2:
                        total_facturado = df_gen['Total ($)'].sum()
                        st.metric("Facturación Bruta", f"$ {total_facturado:,.2f}")
                    with m3:
                        total_choferes = df_gen['Chofer ($)'].sum()
                        st.metric("Total Choferes", f"$ {total_choferes:,.2f}", delta="- Nómina", delta_color="inverse")
                    with m4:
                        total_beneficio = df_gen['Beneficio ($)'].sum()
                        st.metric("Utilidad ExpreX", f"$ {total_beneficio:,.2f}", delta="+ Neto", delta_color="normal")
                    
                    st.markdown("---")
                    st.dataframe(df_gen, use_container_width=True, hide_index=True)
                else:
                    st.info("💡 No se encontraron registros de fletes en la base de datos.")
            except Exception as e:
                st.error(f"Error en consulta general: {e}")
    #
    # =========================================================================
    # PESTAÑA 6: CONSULTA INDIVIDUAL DE CLIENTES POR PERÍODOS (MIGRADO A POSTGRESQL)
    # =========================================================================
    with tab_consulta_clientes:
        st.write("#### 🏢 Expediente y Consulta Individual de Clientes")
        
        try:
            with obtener_conexion_db() as conexion:
                # Traemos la lista de clientes para el buscador
                df_lista_clientes = pd.read_sql_query(
                    "SELECT id_cliente, razon_social FROM clientes ORDER BY razon_social ASC", 
                    conexion
                )
            
            if not df_lista_clientes.empty:
                # 1️⃣ FUNCIÓN DE FORMATO SEGURA: Evita crasheos si el ID no existe o es None
                def obtener_razon_social_segura(id_buscar):
                    if id_buscar is None:
                        return ""
                    filtro = df_lista_clientes[df_lista_clientes['id_cliente'] == id_buscar]
                    if not filtro.empty:
                        return str(filtro['razon_social'].values[0])
                    return "Cliente Desconocido"

                # Buscador desplegable de clientes
                cliente_seleccionado_id = st.selectbox(
                    "🔍 Seleccione el cliente que desea consultar:",
                    options=df_lista_clientes['id_cliente'].tolist(),
                    format_func=obtener_razon_social_segura
                )
                
                # --- CONTROLADORES DE FECHA POR PERÍODOS ---
                st.markdown("📅 **Filtrar por rango de fechas (Fecha de Despacho):**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    # Inicializa el inicio del mes actual de forma segura
                    fecha_inicio = st.date_input("Desde:", value=dt.date.today().replace(day=1), key="f_cliente_desde")
                with col_f2:
                    fecha_fin = st.date_input("Hasta:", value=dt.date.today(), key="f_cliente_hasta")
                
                # Convertimos las fechas a formato string 'YYYY-MM-DD'
                f_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
                f_fin_str = fecha_fin.strftime('%Y-%m-%d')
                
                # 2️⃣ VALIDACIÓN DE ID SEGURO PARA PYLANCE
                if cliente_seleccionado_id is None or str(cliente_seleccionado_id).strip() == "" or str(cliente_seleccionado_id) == "0":
                    st.warning("⚠️ Por favor, seleccione un cliente válido de la lista.")
                else:
                    # Extraemos el nombre con nuestra lógica segura
                    nombre_cliente = obtener_razon_social_segura(cliente_seleccionado_id)
                    st.markdown(f"📊 **Resumen Operativo y Financiero: {nombre_cliente}** (Del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')})")
                    
                    # Forzamos el entero en una variable previa garantizada por el bloque else
                    id_cliente_seguro = int(cliente_seleccionado_id)
                    
                    with obtener_conexion_db() as conexion:
                        # --- CONSULTA DE METRICAS DEL CLIENTE CON FILTRO DE FECHAS ---
                        sql_metricas = """
                            SELECT 
                                COUNT(id_viaje) as total_fletes,
                                SUM(CASE WHEN estatus_viaje IN ('Por Salir', 'En Ruta', 'Descargando') THEN 1 ELSE 0 END) as activos,
                                SUM(CASE WHEN estatus_viaje = 'Entregado' THEN 1 ELSE 0 END) as completados,
                                SUM(monto_flete_usd) as total_facturado
                            FROM viajes 
                            WHERE id_cliente = %s 
                              AND fecha_despacho::date BETWEEN %s::date AND %s::date
                        """
                        df_metrics = pd.read_sql_query(sql_metricas, conexion, params=(id_cliente_seguro, f_inicio_str, f_fin_str))
                        
                        # --- CONSULTA DEL HISTORIAL DETALLADO CON FILTRO DE FECHAS ---
                        sql_historial = """
                            SELECT 
                                v.id_viaje AS "Código",
                                v.estatus_viaje AS "Estado",
                                v.num_pedido AS "Pedido",
                                v.num_factura AS "Factura",
                                v.destino AS "Destino",
                                u.nombre AS "Conductor",
                                v.fecha_despacho AS "Fecha Salida",
                                v.monto_flete_usd AS "Flete USD",
                                v.importe_neto_usd AS "Neto USD"
                            FROM viajes v
                            JOIN usuarios u ON v.cedula_conductor = u.cedula
                            WHERE v.id_cliente = %s
                              AND v.fecha_despacho::date BETWEEN %s::date AND %s::date
                            ORDER BY v.id_viaje DESC
                        """
                        df_historial = pd.read_sql_query(sql_historial, conexion, params=(id_cliente_seguro, f_inicio_str, f_fin_str))
                    
                    # Extraemos valores para las tarjetas (manejando None de forma segura)
                    total_fletes = int(df_metrics['total_fletes'].values[0]) if not df_metrics.empty and df_metrics['total_fletes'].values[0] is not None else 0
                    activos = int(df_metrics['activos'].values[0]) if not df_metrics.empty and df_metrics['activos'].values[0] is not None else 0
                    completados = int(df_metrics['completados'].values[0]) if not df_metrics.empty and df_metrics['completados'].values[0] is not None else 0
                    facturado = float(df_metrics['total_facturado'].values[0]) if not df_metrics.empty and df_metrics['total_facturado'].values[0] is not None else 0.0
                    
                    # Renderizamos las tarjetas de indicadores en filas
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("📋 Total Fletes", total_fletes)
                    with c2:
                        st.metric("🛣️ Viajes Activos", activos, delta=f"{activos} en ruta" if activos > 0 else None, delta_color="normal" if activos > 0 else "off")
                    with c3:
                        st.metric("✅ Completados", completados)
                    with c4:
                        st.metric("💰 Total Facturado", f"${facturado:,.2f}")
                    
                    st.markdown("---")
                    st.write("### 🕒 Historial de Viajes en el Período Seleccionado")
                    
                    # Mostramos la tabla del historial del cliente seleccionado
                    if not df_historial.empty:
                        st.dataframe(df_historial, use_container_width=True, hide_index=True)
                    else:
                        st.info("ℹ️ Este cliente no registra fletes cargados en el rango de fechas seleccionado.")
                        
            else:
                st.info("⚠️ No hay clientes registrados en el sistema para consultar.")
                
        except Exception as e:
            st.error(f"❌ Error al consultar el expediente del cliente: {e}")

        #
        # =========================================================================
    # PESTAÑA 7: CONSULTA INDIVIDUAL DE FLETES (MIGRADO A POSTGRESQL)
    # =========================================================================
    with tab_individual:
        st.write("#### 🔍 Auditoría de Flete por ID")
        
        try:
            with obtener_conexion_db() as conexion:
                df_ids = pd.read_sql_query("SELECT num_pedido FROM viajes ORDER BY num_pedido DESC", conexion)
        except Exception as e:
            st.error(f"Error al cargar los códigos de fletes: {e}")
            df_ids = pd.DataFrame()
            
        if df_ids.empty:
            st.info("No hay fletes disponibles para consulta individual.")
        else:
            id_seleccionado = st.selectbox(
                "Seleccione el ID del flete a inspeccionar:",
                options=df_ids['num_pedido'].tolist(),
                format_func=lambda x: f"Flete N° {x}"
            )
            
            st.markdown("---")
            
            try:
                with obtener_conexion_db() as conexion:
                    with conexion.cursor() as cursor:
                        sql_individual = """
                            SELECT 
                                v.id_viaje, v.fecha_despacho, c.razon_social, c.rif,
                                u.nombre, v.cedula_conductor, v.origen, v.destino,
                                v.tipo_material, v.peso_carga_kg, v.distancia_km, v.monto_flete_usd,
                                v.num_pedido, v.num_factura, v.persona_contacto_entrega, v.telefono_contacto_entrega,
                                v.observaciones, v.estatus_viaje, v.foto_evidencia,
                                v.descuento_usd, v.importe_neto_usd, v.pago_chofer_usd, v.beneficio_exprex_usd,
                                v.tipo_viaje,
                                v.cliente_solicitante, v.telefono_cliente
                            FROM viajes v
                            JOIN clientes c ON v.id_cliente = c.id_cliente
                            JOIN usuarios u ON v.cedula_conductor = u.cedula
                            WHERE v.num_pedido = %s
                        """
                        # Se pasa el parámetro como tupla garantizando su correspondencia con %s
                        cursor.execute(sql_individual, (str(id_seleccionado),))
                        flete = cursor.fetchone()
                
                if flete:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"#### 📋 Información General")
                        st.write(f"**🗓️ Fecha:** {flete[1]}")
                        st.write(f"**🏢 Cliente:** {flete[2]} (RIF: {flete[3]})")
                        st.write(f"**🧾 Factura:** {flete[13]} | **📦 Pedido:** {flete[12]}")
                        st.write(f"**👤 Solicita:** {flete[24]}") 
                        st.write(f"**📞 Telf:** {flete[25]}")                  
                        st.write(f"**⚡ Tipo de Viaje:** `{flete[23]}`") 
                        st.write(f"**📍 Ruta:** {flete[6]} ➡️ {flete[7]}")
                        st.write(f"**🛣️ Distancia:** {flete[10]} Km | **⚖️ Peso:** {flete[9]} Kg")
                        st.write(f"**🪵 Material:** {flete[8]}")
                        st.write(f"**🚦 Estatus Actual:** `{flete[17]}`")
                    
                    with col2:
                        st.markdown("#### 💰 Liquidación de Cuentas (Fijo)")
                        st.write(f"**Monto Inicial del Flete (Total):** ${flete[11]:,.2f}") if flete[11] is not None else st.write("**Monto inicial del Flete (Total):** $0.00")
                        st.write(f"**Descuento Comercial (15%):** ${flete[19]:,.2f}") if flete[19] is not None else st.write("**Descuento Comercial (15%):** $0.00")
                        st.markdown(f"**Importe Neto:** `${flete[20]:,.2f}`") if flete[20] is not None else st.write("**Importe Neto:** $0.00")
                        st.write(f"**Pago al Transportista (Chofer):** ${flete[21]:,.2f}") if flete[21] is not None else st.write("**Pago al Transportista (Chofer):** $0.00")
                        st.markdown(f"#### 🟩 Beneficio ExpreX: ${flete[22]:,.2f}") if flete[22] is not None else st.write("#### 🟩 **Beneficio ExpreX:** $0.00")

                        st.markdown("---")
                        st.write(f"**🧑‍✈️ Conductor:** {flete[4]} (C.I. {flete[5]})")
                        st.write(f"**👤 Recibe:** {flete[14]} | **📞 Telf:** {flete[15]}")
                        st.write(f"**📝 Observaciones:** {flete[16] if flete[16] else 'Ninguna'}")
                    
                    st.markdown("---")
                    st.markdown("#### 📸 Soporte Físico Digitalizado (Factura Firmada)")
                    
                    ruta_foto = flete[18]
                    if ruta_foto and os.path.exists(ruta_foto):
                        st.image(ruta_foto, caption=f"Evidencia fotográfica vinculada al Flete N° {id_seleccionado}", use_container_width=True)
                    else:
                        st.warning("⚠️ No se ha cargado soporte fotográfico para este flete o el archivo no se encuentra en el servidor local.")
                        
            except Exception as e:
                st.error(f"Error al cargar el detalle del flete: {e}")

    with tab_gestion_tarifas:
        seccion_tarifas_admin()