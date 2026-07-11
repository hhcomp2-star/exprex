import streamlit as st
import sqlite3
import pandas as pd
import time
import os  
import datetime as dt
from datetime import datetime
#from geopy.distance import geodesic
from modulos.asignacion_previa import renderizar_pestana_asignar

def mostrar_modulo_operaciones():
    st.markdown("### 🎯 Control Operativo de Rutas")
    st.write("Seguimiento en tiempo real de unidades, despachos, contingencias e historial consolidado.")
    
    # 📝 CORRECCIÓN 2: Añadido el cuarto nombre "📊 Historial y Auditoría" para que coincida con las 4 variables
    tab_asignar, tab_despacho, tab_carretera, tab_contingencia, tab_historial = st.tabs([
        "📋 Solicitudes / Por Asignar",
        "📝 Registrar Despacho",
        "🚚 Unidades en Carretera", 
        "🔄 Modificar Viaje (Contingencias)",
        "📊 Historial y Auditoría"
    ])

    # Base de datos única
    personal_base_datos = "exprex.db"

    
    # =========================================================================
    # LOGICA DE LA PESTAÑA SOLICITUDES POR ASIGNAR
    # =========================================================================
    with tab_asignar:
        renderizar_pestana_asignar('exprex.db')
        

    # =========================================================================
    # PESTAÑA 1: PROCESAR Y REGISTRAR DESPACHO (REPARADA: ESCRITURA SEGURA VIA UPDATE)
    # =========================================================================
    with tab_despacho:
        st.write("### 🎫 Panel de Despacho de Fletes Solicitados")
        st.info("Seleccione una solicitud asignada para completar la información logística final y emitir la orden de salida.")
        
        try:
            conexion = sqlite3.connect('exprex.db')
            df_cb_conductores = pd.read_sql_query("SELECT cedula, nombre FROM usuarios WHERE rol = 'Conductor' AND activo = 'Sí'", conexion)
            
            # 🎯 CORRECCIÓN 1: Filtramos para traer SOLO solicitudes que YA tengan conductor pre-asignado
            df_solicitudes_pendientes = pd.read_sql_query('''
                SELECT v.*, c.razon_social 
                FROM viajes v
                JOIN clientes c ON v.id_cliente = c.id_cliente
                WHERE v.estatus_viaje = 'Solicitado'
                  AND v.cedula_conductor IS NOT NULL
                ORDER BY CASE WHEN v.tipo_viaje = 'Express' THEN 1 ELSE 2 END, v.id_viaje DESC
            ''', conexion)
            conexion.close()
        except Exception as e:
            st.error(f"Error en comunicación de base de datos en despacho: {e}")
            df_solicitudes_pendientes = pd.DataFrame()

        if df_solicitudes_pendientes.empty:
            st.success("✅ ¡Al día! No existen solicitudes listas para despacho definitivo en este momento.")
        else:
            # 1️⃣ MAPEO SEGURO: Convertimos el DataFrame en un diccionario de Python puro
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

            # 2️⃣ ESCUDO DEFENSIVO ANTES DE MOSTRAR DETALLES
            coincidencia_despacho = df_solicitudes_pendientes[df_solicitudes_pendientes['id_viaje'] == id_viaje_seleccionado]
            
            if coincidencia_despacho.empty:
                st.warning("🔄 Sincronizando datos de despacho...")
            else:
                # 🎯 AQUÍ ES DONDE SE DEFINE VIAJE_SEL (¡No puede perderse!)
                viaje_sel = coincidencia_despacho.iloc[0]
                
                # 🏢 VISTA DE AUDITORÍA: Una sola tarjeta informativa limpia
                st.markdown(f"""
                <div style="background-color:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {'#ff4b4b' if viaje_sel['tipo_viaje']=='Express' else '#3b82f6'};">
                    <h4>📦 Datos Registrados por el Cliente y Asignación</h4>
                    ... (resto de tu tabla HTML) ...
                </div>
                """, unsafe_allow_html=True)
                
                st.write("")
                
                # Enlace interactivo a mapas
                destino_solicitado = viaje_sel['destino']
                direccion_url = destino_solicitado.replace(" ", "+")
                url_maps = f"https://www.google.com/maps/search/?api=1&query={direccion_url}"
                st.markdown(f"🗺️ [**Click aquí para ubicar '{destino_solicitado}' en Google Maps**]({url_maps})")
                st.caption("💡 *Haga clic derecho en el destino para extraer las coordenadas geográficas exactas e ingresarlas abajo.*")

                # 3️⃣ FORMULARIO DE DESPACHO INTERACTIVO
                st.write("#### 🛠️ Completar Información Logística de Salida")
                
                # Definimos el índice por defecto para el conductor que ya viene pre-asignado
                lista_cedulas_choferes = df_cb_conductores['cedula'].tolist()
                try:
                    index_chofer_preasig = lista_cedulas_choferes.index(viaje_sel['cedula_conductor'])
                except ValueError:
                    index_chofer_preasig = 0

                # 💡 ROMPEMOS EL st.form PARA HACERLO INTERACTIVO Y EN TIEMPO REAL
                col1, col2 = st.columns(2)
                
                with col1:
                    conductor_seleccionado = st.selectbox(
                        "👤 Conductor Asignado para la Ruta",
                        options=lista_cedulas_choferes,
                        index=index_chofer_preasig,
                        format_func=lambda x: df_cb_conductores[df_cb_conductores['cedula'] == x]['nombre'].values[0]
                    )
                    import datetime
                    fecha_despacho = st.date_input("📅 Fecha de Salida Real", value=datetime.date.today()).strftime("%Y-%m-%d")
                    num_factura = st.text_input("🧾 Número de Factura / Control Interno (Opcional)").strip().upper()

                with col2:
                    col_dest_lat, col_dest_lon = st.columns(2)
                    with col_dest_lat:
                        lat_input = st.text_input("🌐 Latitud Destino", value="0.0").strip()
                    with col_dest_lon:
                        lon_input = st.text_input("🌐 Longitud Destino", value="0.0").strip()
                    
                    distancia_calculada = float(viaje_sel['distancia_km']) if viaje_sel['distancia_km'] else 0.0
                    
                    if lat_input != "0.0" and lon_input != "0.0" and lat_input != "" and lon_input != "":
                        try:
                            from geopy.distance import geodesic
                            
                            # 🎯 BUSQUEDA DIRECTA: Solo vamos por las coordenadas de la sucursal de este viaje
                            conexion = sqlite3.connect('exprex.db')
                            cursor = conexion.cursor()
                            
                            # Buscamos la latitud y longitud en la tabla sucursales usando el id_sucursal_origen del viaje actual
                            cursor.execute("""
                                SELECT s.latitud, s.longitud 
                                FROM sucursales s
                                JOIN viajes v ON v.id_sucursal_origen = s.id_sucursal
                                WHERE v.id_viaje = ?
                            """, (int(id_viaje_seleccionado),))
                            
                            resultado = cursor.fetchone()
                            conexion.close()

                            if resultado:
                                # fetchone() devuelve una tupla (latitud, longitud)
                                lat_origen_dinamico = float(resultado[0])
                                lng_origen_dinamico = float(resultado[1])
                                
                                punto_origen = (lat_origen_dinamico, lng_origen_dinamico)
                                punto_destino = (float(lat_input), float(lon_input))
                                
                                # Calculamos la distancia real entre esa sucursal específica y el destino pegado
                                dist_lineal = geodesic(punto_origen, punto_destino).kilometers
                                distancia_calculada = round(dist_lineal * 1.3, 2)
                            
                        except Exception as e:
                            # Si algo falla, dejamos que el usuario lo meta manual sin romper la app
                            pass 
                    
                    # El campo de distancia se entera solo y se actualiza al instante
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

                # Botón de acción definitivo (Sustituye al form_submit_button)
                _, sub_col_centro, _ = st.columns([1, 2, 1])
                with sub_col_centro:
                    boton_despachar = st.button("🚀 Confirmar Despacho y Pasar a 'Por Salir'", use_container_width=True, type="primary")
            
                if boton_despachar:
                    if distancia_km <= 0:
                        st.error("⚠️ Debe ingresar la distancia en kilómetros calculada para la ruta.")
                    else:
                        try:
                            conexion = sqlite3.connect('exprex.db')
                            cursor = conexion.cursor()
                            
                            cursor.execute("""
                                UPDATE viajes 
                                SET cedula_conductor = ?,
                                    fecha_despacho = ?,
                                    distancia_km = ?,
                                    monto_flete_usd = ?,
                                    num_factura = ?,
                                    latitud_entrega = ?,
                                    longitud_entrega = ?,
                                    estatus_viaje = 'Por Salir'
                                WHERE id_viaje = ?
                            """, (
                                conductor_seleccionado, 
                                fecha_despacho, 
                                distancia_km, 
                                monto_calculado,
                                num_factura,
                                float(lat_input) if lat_input else 0.0, 
                                float(lon_input) if lon_input else 0.0,
                                id_viaje_seleccionado
                            ))
                            
                            conexion.commit()
                            conexion.close()
                            
                            st.success(f"🎉 Flete N° {id_viaje_seleccionado} despachado con éxito. Cambiado a estatus 'Por Salir'.")
                            
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error crítico al actualizar despacho: {e}")

    # =========================================================================
    # PESTAÑA 2: UNIDADES EN CARRETERA (REPARADA: ANTI-CRASH Y PROTEGIDA)
    # =========================================================================
    with tab_carretera:
        st.write("### 🛣️ Monitoreo de Unidades Activas")
        st.write("### 🚚 Control de Fletes Activos")
        try:
            conexion = sqlite3.connect(personal_base_datos)
            sql_consulta = """
                SELECT 
                    v.id_viaje AS 'Código',
                    v.estatus_viaje AS 'Estado Actual',
                    v.num_pedido AS 'Pedido',
                    v.num_factura AS 'Factura',
                    c.razon_social AS 'Cliente',
                    s.nombre_agencia AS 'Origen (Agencia)',
                    v.cliente_solicitante AS 'Solicitante',
                    v.destino AS 'Destino',
                    u.nombre AS 'Conductor',
                    v.fecha_despacho AS 'Salida',
                    v.tipo_viaje AS 'Tipo',
                    v.distancia_km AS 'Km Reales',
                    v.monto_flete_usd AS 'Flete USD',
                    v.observaciones AS 'Notas'
                FROM viajes v
                JOIN clientes c ON v.id_cliente = c.id_cliente
                LEFT JOIN sucursales s ON v.id_sucursal_origen = s.id_sucursal
                JOIN usuarios u ON v.cedula_conductor = u.cedula
                WHERE v.estatus_viaje IN ('Por Salir', 'En Ruta')
                  AND v.id_viaje IS NOT NULL -- 🛡️ ESCUDO 1: Ignora registros fantasmas asíncronos
                ORDER BY v.id_viaje DESC
            """
            df_viajes = pd.read_sql_query(sql_consulta, conexion)
            conexion.close()
            
            if not df_viajes.empty:
                st.dataframe(df_viajes, use_container_width=True, hide_index=True)
                st.markdown("---")
                
                # 🛡️ ESCUDO 2: Evitamos crash si Pandas lee filas vacías en la iteración dinámica
                id_seleccionado = st.selectbox(
                    "Seleccione el Viaje a Procesar:", 
                    options=df_viajes['Código'].tolist(),
                    format_func=lambda x: f"📦 Viaje #{x} - Pedido: {df_viajes[df_viajes['Código'] == x]['Pedido'].values[0] if not df_viajes[df_viajes['Código'] == x]['Pedido'].empty else 'Procesando...'} [{df_viajes[df_viajes['Código'] == x]['Cliente'].values[0] if not df_viajes[df_viajes['Código'] == x]['Cliente'].empty else '...'}]"
                )
                
                fila_seleccionada = df_viajes[df_viajes['Código'] == id_seleccionado]
                if not fila_seleccionada.empty:
                    estado_actual = fila_seleccionada['Estado Actual'].values[0]
                else:
                    estado_actual = "Por Salir"
                    
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if estado_actual == "Por Salir":
                        if st.button("🚀 Dar Salida (Marcar 'En Ruta')", use_container_width=True):
                            conexion = sqlite3.connect(personal_base_datos)
                            cursor = conexion.cursor()
                            cursor.execute("UPDATE viajes SET estatus_viaje = 'En Ruta' WHERE id_viaje = ?", (id_seleccionado,))
                            conexion.commit()
                            conexion.close()
                            st.success("¡Unidad en carretera!")
                            time.sleep(2)
                            st.rerun()
                            
                with col_btn2:
                    if st.button("🏁 Ir al Cierre (Completar Viaje)", use_container_width=True, type="primary"):
                        st.session_state["cerrando_viaje"] = id_seleccionado

                with col_btn3:
                    if estado_actual == "Por Salir":
                        if st.button("🗑️ Anular Orden (Borrar)", use_container_width=True, type="secondary"):
                            try:
                                conexion = sqlite3.connect(personal_base_datos)
                                cursor = conexion.cursor()
                                cursor.execute("DELETE FROM viajes WHERE id_viaje = ?", (id_seleccionado,))
                                conexion.commit()
                                conexion.close()
                                st.success("🛑 Orden duplicada eliminada correctamente.")
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error al anular: {e}")

                if st.session_state.get("cerrando_viaje") == id_seleccionado:
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
                                ruta_foto_guardada = f"fotos_entregas/viaje_{id_seleccionado}_evidencia.{ext}"
                                with open(ruta_foto_guardada, "wb") as f:
                                    f.write(archivo_foto.getbuffer())
                            
                            conexion = sqlite3.connect(personal_base_datos)
                            cursor = conexion.cursor()
                            
                            # 1️⃣ Traemos también la distancia y el tipo de viaje por si el monto vino vacío (None)
                            cursor.execute("""
                                SELECT monto_flete_usd, cedula_conductor, distancia_km, tipo_viaje 
                                FROM viajes 
                                WHERE id_viaje = ?
                            """, (id_seleccionado,))
                            res_v = cursor.fetchone()
                            
                            if res_v:
                                monto_flete_bd = res_v[0]
                                cedula_chofer = res_v[1]
                                distancia_bd = res_v[2]
                                tipo_viaje = res_v[3]
                                
                                # --- SALVAVIDAS CONTRA NONETYPE / CÁLCULO EN TIEMPO REAL ---
                                if monto_flete_bd is not None:
                                    monto_flete_total = float(monto_flete_bd)
                                else:
                                    # Si el monto está vacío, lo reconstruimos quirúrgicamente con la distancia guardada
                                    distancia_km = float(distancia_bd) if distancia_bd is not None else 0.0
                                    distancia_calculo = max(distancia_km, 8.0) if distancia_km > 0 else 0.0
                                    tarifa_por_km = 4.0 if tipo_viaje == 'Express' else 2.5
                                    monto_flete_total = distancia_calculo * tarifa_por_km
                                
                                # 2️⃣ Buscamos si el vehículo es propio
                                cursor.execute("SELECT propio FROM conductores WHERE cedula = ?", (cedula_chofer,))
                                res_c = cursor.fetchone()
                                es_propio = res_c[0] if res_c and res_c[0] else "No"
                                
                                # 3️⃣ Fórmulas Financieras de Liquidación
                                descuento = monto_flete_total * 0.15
                                importe_neto = monto_flete_total - descuento
                                porcentaje_chofer = 0.75 if es_propio == "Sí" else 0.37
                                pago_chofer = importe_neto * porcentaje_chofer
                                beneficio_exprex = importe_neto - pago_chofer
                                
                                # 4️⃣ Guardado definitivo en base de datos (Inyectamos también el monto flete si faltaba)
                                sql_update = """
                                    UPDATE viajes 
                                    SET estatus_viaje = 'Entregado', 
                                        foto_evidencia = ?, 
                                        monto_flete_usd = ?,
                                        descuento_usd = ?,
                                        importe_neto_usd = ?, 
                                        pago_chofer_usd = ?, 
                                        beneficio_exprex_usd = ?  
                                    WHERE id_viaje = ?
                                """
                                cursor.execute(sql_update, (
                                    ruta_foto_guardada, 
                                    monto_flete_total, # Guardamos el flete final en la tabla
                                    descuento, 
                                    importe_neto, 
                                    pago_chofer, 
                                    beneficio_exprex, 
                                    id_seleccionado
                                ))
                                
                                conexion.commit()
                                st.success("🎉 Viaje completado. Cuentas calculadas y registradas con éxito.")
                                time.sleep(2)
                            else:
                                st.error("No se encontraron los datos del viaje para procesar el cierre.")
                            
                            conexion.close()
                            st.session_state["cerrando_viaje"] = None
                            time.sleep(2)
                            st.rerun()    
            else:
                st.info("🟢 No hay viajes activos en este momento ('Por Salir' o 'En Ruta').")
        except Exception as e:
            st.error(f"❌ Error en monitor: {e}")
        
    # =========================================================================
    # PESTAÑA 3: CONTROL DE CONTINGENCIAS
    # =========================================================================
    with tab_contingencia:
        st.write("### 🔄 Control de Contingencias: Modificar Viaje Activo")
        st.info("Utilice esta sección para resolver imprevistos en ruta (cambio de chofer, modificaciones de destino o datos de entrega).")
    
        conexion = sqlite3.connect(personal_base_datos)
        query_viajes = """
            SELECT v.id_viaje, v.num_pedido, u.nombre AS Conductor, v.destino, v.estatus_viaje
            FROM viajes v
            JOIN usuarios u ON v.cedula_conductor = u.cedula
            WHERE v.estatus_viaje IN ('Por Salir', 'En Ruta')
        """
        df_viajes_activos = pd.read_sql_query(query_viajes, conexion)
        
        query_choferes = "SELECT cedula, nombre FROM usuarios WHERE rol = 'Conductor' AND activo = 'Sí'"
        df_choferes = pd.read_sql_query(query_choferes, conexion)
        conexion.close()
        
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
                
                conexion = sqlite3.connect(personal_base_datos)
                cursor = conexion.cursor()
                cursor.execute("""
                    SELECT cedula_conductor, destino, persona_contacto_entrega, telefono_contacto_entrega, observaciones
                    FROM viajes WHERE id_viaje = ?
                """, (id_viaje_mod,))
                datos_actuales = cursor.fetchone()
                conexion.close()
                
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
                    
                if boton_guardar_cambios:
                    try:
                        conexion = sqlite3.connect(personal_base_datos)
                        cursor = conexion.cursor()
                        
                        sql_update_viaje = """
                            UPDATE viajes 
                            SET cedula_conductor = ?, 
                                destino = ?, 
                                persona_contacto_entrega = ?, 
                                telefono_contacto_entrega = ?, 
                                observaciones = ?
                            WHERE id_viaje = ?
                        """
                        cursor.execute(sql_update_viaje, (
                            nueva_cedula_conductor,
                            nuevo_destino.strip(),
                            nueva_persona_recibe.strip(),
                            nuevo_telefono_recibe.strip(),
                            nuevas_observaciones.strip(),
                            id_viaje_mod
                        ))
                        conexion.commit()
                        st.success(f"✅ ¡Viaje ID #{id_viaje_mod} modificado y reasignado con éxito!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al actualizar la contingencia: {e}")
                    finally:
                        conexion.close()

    # =========================================================================
    # PESTAÑA 4: HISTORIAL Y AUDITORÍA (MUDADO CON ÉXITO)
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
                conexion = sqlite3.connect(personal_base_datos)
                sql_general = """
                    SELECT 
                        v.id_viaje AS 'ID Viaje',
                        v.fecha_despacho AS 'Fecha',
                        c.razon_social AS 'Cliente',
                        v.num_factura AS 'N° Factura',
                        v.num_pedido AS 'N° Pedido',
                        v.cliente_solicitante AS 'Solicitante',
                        v.monto_flete_usd AS 'Total ($)',
                        v.descuento_usd AS 'Desc ($)',
                        v.importe_neto_usd AS 'Importe ($)',
                        v.pago_chofer_usd AS 'Chofer ($)',
                        v.beneficio_exprex_usd AS 'Beneficio ($)',
                        v.estatus_viaje AS 'Estatus'
                    FROM viajes v
                    JOIN clientes c ON v.id_cliente = c.id_cliente
                    ORDER BY v.id_viaje DESC
                """
                df_gen = pd.read_sql_query(sql_general, conexion)
                conexion.close()
                
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

    # =========================================================================
    # PESTAÑA 2: CONSULTA INDIVIDUAL DE CLIENTES POR PERÍODOS
    # =========================================================================
    with tab_consulta_clientes:
        st.write("#### 🏢 Expediente y Consulta Individual de Clientes")
        
        try:
            conexion = sqlite3.connect(personal_base_datos)
            # Traemos la lista de clientes para el buscador
            df_lista_clientes = pd.read_sql_query(
                "SELECT id_cliente, razon_social FROM clientes ORDER BY razon_social ASC", 
                conexion
            )
            conexion.close()
            
            if not df_lista_clientes.empty:
                # Buscador desplegable de clientes
                cliente_seleccionado_id = st.selectbox(
                    "🔍 Seleccione el cliente que desea consultar:",
                    options=df_lista_clientes['id_cliente'].tolist(),
                    format_func=lambda x: df_lista_clientes[df_lista_clientes['id_cliente'] == x]['razon_social'].values[0]
                )
                
                # --- CONTROLADORES DE FECHA POR PERÍODOS ---
                st.markdown("📅 **Filtrar por rango de fechas (Fecha de Despacho):**")
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    # Inicializa el inicio del mes actual de forma segura
                    fecha_inicio = st.date_input("Desde:", value=dt.date.today().replace(day=1), key="f_cliente_desde")
                with col_f2:
                    fecha_fin = st.date_input("Hasta:", value=dt.date.today(), key="f_cliente_hasta")
                
                # Convertimos las fechas a formato string 'YYYY-MM-DD' compatible con SQLite
                f_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
                f_fin_str = fecha_fin.strftime('%Y-%m-%d')
                
                # Nombre del cliente para los títulos
                nombre_cliente = df_lista_clientes[df_lista_clientes['id_cliente'] == cliente_seleccionado_id]['razon_social'].values[0]
                st.markdown(f"📊 **Resumen Operativo y Financiero: {nombre_cliente}** (Del {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')})")
                
                # --- CONSULTA DE METRICAS DEL CLIENTE CON FILTRO DE FECHAS ---
                conexion = sqlite3.connect(personal_base_datos)
                sql_metricas = """
                    SELECT 
                        COUNT(id_viaje) as total_fletes,
                        SUM(CASE WHEN estatus_viaje IN ('Por Salir', 'En Ruta', 'Descargando') THEN 1 ELSE 0 END) as activos,
                        SUM(CASE WHEN estatus_viaje = 'Entregado' THEN 1 ELSE 0 END) as completados,
                        SUM(monto_flete_usd) as total_facturado
                    FROM viajes 
                    WHERE id_cliente = ? 
                      AND date(fecha_despacho) BETWEEN date(?) AND date(?)
                """
                df_metrics = pd.read_sql_query(sql_metricas, conexion, params=(cliente_seleccionado_id, f_inicio_str, f_fin_str))
                
                # --- CONSULTA DEL HISTORIAL DETALLADO CON FILTRO DE FECHAS ---
                sql_historial = """
                    SELECT 
                        v.id_viaje AS 'Código',
                        v.estatus_viaje AS 'Estado',
                        v.num_pedido AS 'Pedido',
                        v.num_factura AS 'Factura',
                        v.destino AS 'Destino',
                        u.nombre AS 'Conductor',
                        v.fecha_despacho AS 'Fecha Salida',
                        v.monto_flete_usd AS 'Flete USD',
                        v.importe_neto_usd AS 'Neto USD'
                    FROM viajes v
                    JOIN usuarios u ON v.cedula_conductor = u.cedula
                    WHERE v.id_cliente = ?
                      AND date(v.fecha_despacho) BETWEEN date(?) AND date(?)
                    ORDER BY v.id_viaje DESC
                """
                df_historial = pd.read_sql_query(sql_historial, conexion, params=(cliente_seleccionado_id, f_inicio_str, f_fin_str))
                conexion.close()
                
                # Extraemos valores para las tarjetas (manejando None si el cliente es nuevo o no hay datos)
                total_fletes = df_metrics['total_fletes'].values[0] if not df_metrics.empty else 0
                activos = df_metrics['activos'].values[0] if not df_metrics.empty else 0
                completados = df_metrics['completados'].values[0] if not df_metrics.empty else 0
                facturado = df_metrics['total_facturado'].values[0] if not df_metrics.empty and df_metrics['total_facturado'].values[0] is not None else 0.0
                
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


        # =========================================================================
        # PESTAÑA 3: CONSULTA INDIVIDUAL DE FLETES (MÉTODO EXPANDIDO)
        # =========================================================================

        # Auditoría de flete individual (Con fotos)
        with tab_individual:
            st.write("#### 🔍 Auditoría de Flete por ID")
            
            try:
                conexion = sqlite3.connect(personal_base_datos)
                df_ids = pd.read_sql_query("SELECT num_pedido FROM viajes ORDER BY num_pedido DESC", conexion)
                conexion.close()
            except:
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
                conexion = sqlite3.connect(personal_base_datos)
                cursor = conexion.cursor()
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
                    WHERE v.num_pedido = ?
                """
                cursor.execute(sql_individual, (id_seleccionado,))
                flete = cursor.fetchone()
                conexion.close()
                
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
                        st.write(f"**Monto Inicial del Flete (Total):** ${flete[11]:,.2f}") if flete[11] is not None else st.write("**Monto incial del Flete (Total):** $0.00")
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
                        st.warning("⚠️ No se ha cargado soporte fotográfico para este flete o el archivo no se encuentra en el servidor.")
                        
            except Exception as e:
                st.error(f"Error al cargar el detalle del flete: {e}")   