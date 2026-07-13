import streamlit as st
import sqlite3
import pandas as pd
import datetime
import datetime as dt
import time
import os
from modulos.utils import contar_viajes_pendientes_chofer, reproducir_alerta_victoria

# --- CARGAR TEXTO LEGAL DESDE LA CARPETA MODULOS ---
ruta_terminos = os.path.join("modulos", "terminos.txt")

try:
    with open(ruta_terminos, "r", encoding="utf-8") as f:
        texto_legal_choferes = f.read()
except Exception as e:
    texto_legal_choferes = f"⚠️ No se pudo cargar el archivo de términos en `{ruta_terminos}`: {e}"

import streamlit as st
import sqlite3

def verificar_vehiculo_propio(cedula_chofer):
    """
    Consulta en la tabla conductores si el vehículo es propio.
    Retorna True si es propio ('Sí'), o False si es de la empresa ('No').
    """
    try:
        conn = sqlite3.connect("exprex.db")
        cursor = conn.cursor()
        cursor.execute("SELECT propio FROM conductores WHERE cedula = ?", (cedula_chofer,))
        resultado = cursor.fetchone()
        conn.close()
        
        if resultado and resultado[0] == "Sí":
            return True
    except Exception as e:
        print(f"⚠️ Error al verificar propiedad en tabla conductores: {e}")
    
    return False

def renderizar_panel_conductor(cedula_conductor, personal_base_datos='exprex.db'):

    #st.write(f"##### Panel de Operaciones - Conductor")

    # Colocar aquí para la barra lateral del Chofer (se despliega de lado en el tlf)
    tasa = st.session_state.get('tasa_bcv', '0.00')
    st.sidebar.success(f"Tasa BCV activa: {tasa} Bs.")

    # Si el chofer tiene dudas de si le asignaron algo, le da un toque aquí.
    if st.button("🔄 Actualizar y Buscar Nuevos Fletes", use_container_width=True):
        cedula = st.session_state.get("cedula_chofer") 

        fletes_nuevos = contar_viajes_pendientes_chofer(cedula)

        if fletes_nuevos > 0:
            reproducir_alerta_victoria() # ¡Suena la fanfarria en el celular!
            st.success(f"🚨 ¡Atención! Te asignaron {fletes_nuevos} flete(s) nuevo(s).")
        else:
            st.info("No hay fletes nuevos asignados por ahora.")
        st.rerun()

    # 1. Validación de propiedad (la función que creamos antes)
    es_vehiculo_propio = verificar_vehiculo_propio(cedula_conductor)

    # 2. Creamos las pestañas de forma condicional para reutilizar tus variables
    if es_vehiculo_propio:
        # Si es propio, solo creamos 2 pestañas, y asignamos un "cascarón vació" a la de combustible
        tab_fletes, tab_historial = st.tabs(["📋 Fletes", "📊 Historial"])
        tab_combustible = None  # Al ser None, el bloque 'with tab_combustible' no se ejecutará
    else:
        # Si es de la empresa, se crean las 3 pestañas originales exactamente igual
        tab_fletes, tab_combustible, tab_historial = st.tabs(["📋 Fletes Activos", "⛽ Reportar Combustible", "📜 Historial"])

    # =========================================================================
    # 📌 PESTAÑA 1: RUTAS ACTIVAS Y MAPA GPS
    # =========================================================================
    with tab_fletes:

        try:
            conexion = sqlite3.connect(personal_base_datos)
            df_mis_viajes = pd.read_sql_query('''
                SELECT v.id_viaje, v.cliente_solicitante, v.origen, v.destino, v.tipo_viaje,
                        v.distancia_km, 
                       v.peso_carga_kg, v.tipo_material, v.estatus_viaje, v.num_pedido,
                       s.latitud AS lat_origen, s.longitud AS lon_origen,
                       v.latitud_entrega AS lat_destino, v.longitud_entrega AS lon_destino,
                        v.persona_contacto_entrega, v.telefono_contacto_entrega,
                       c.razon_social AS empresa_cliente -- 🎯 TRUCO: Traemos la empresa jurídica real
                FROM viajes v
                LEFT JOIN sucursales s ON v.origen = s.nombre_agencia
                LEFT JOIN clientes c ON v.id_cliente = c.id_cliente -- 🎯 UNIÓN: Conectamos con clientes
                WHERE v.cedula_conductor = ? 
                  AND v.estatus_viaje IN ('Por Salir', 'En Ruta')
                ORDER BY v.id_viaje DESC
            ''', conexion, params=(cedula_conductor,))
            conexion.close()
        except Exception as e:
            st.error(f"❌ Error al cargar las rutas con coordenadas: {e}")
            df_mis_viajes = pd.DataFrame()

        if df_mis_viajes.empty:
            st.success("😎 ¡Al día! No tienes fletes pendientes asignados en este momento.")
        else:
            dicc_viajes = {row['id_viaje']: f"Flete N° {row['id_viaje']} - {row['tipo_material']}" for _, row in df_mis_viajes.iterrows()}
            viaje_id = st.selectbox("🔄 Selecciona el flete a ejecutar:", options=list(dicc_viajes.keys()), format_func=lambda x: str(dicc_viajes.get(x, f"Flete N° {x}")))

            viaje_sel = df_mis_viajes[df_mis_viajes['id_viaje'] == viaje_id].iloc[0]

            # 🏢 VISTA DE HOJA DE RUTA CORREGIDA
            st.markdown(f"""
            <div style="background-color:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid #22c55e;">
                <h5 style="margin-top:0; color:#22c55e;">📋 Hoja de Ruta - Flete N° {viaje_sel['id_viaje']}</h5>
                <p style="margin-bottom:5px; color:#ffffff;"><b>🏢 Empresa:</b> {viaje_sel['empresa_cliente'] if viaje_sel['empresa_cliente'] else 'No Registrada'}</p>
                <p style="margin-bottom:5px; color:#ffffff;"><b>📍 Salida (Sucursal):</b> {viaje_sel['origen']}</p>
                <p style="margin-bottom:5px; color:#ffffff;"><b>🏁 Dirección de Entrega:</b> {viaje_sel['destino']}</p>
                <p style="margin-bottom:5px; color:#ffffff;"><b>🛣️ Distancia:</b> {viaje_sel['distancia_km']}</p>
                <p style="margin-bottom:8px; color:#ffffff;"><b>📦 Carga:</b> {viaje_sel['peso_carga_kg']} Kg ({viaje_sel['tipo_material']})</p>
                <hr style="border-color:#333333; margin:10px 0;">
                <p style="margin-bottom:0; color:#b0b0b0; font-size:14px;"><b>👤 Solicitante:</b> {viaje_sel['cliente_solicitante']}</p>
                <p style="margin-bottom:0; color:#b0b0b0; font-size:14px;"><b>👤 Recibe:</b> {viaje_sel['persona_contacto_entrega']} Tel: {viaje_sel['telefono_contacto_entrega']}</p>
            </div>
            """, unsafe_allow_html=True)

            st.write("")

            # 🎯 La validación ideal definitiva:
            if pd.notna(viaje_sel['lat_origen']) and pd.notna(viaje_sel['lon_origen']) and viaje_sel['lat_origen'] != 0 and viaje_sel['lon_origen'] != 0:
                origen_param = f"{viaje_sel['lat_origen']},{viaje_sel['lon_origen']}"
            else:
                origen_param = viaje_sel['origen'].replace(" ", "+")

            if pd.notna(viaje_sel['lat_destino']) and pd.notna(viaje_sel['lon_destino']) and viaje_sel['lat_destino'] != 0 and viaje_sel['lon_destino'] != 0:
                destino_param = f"{viaje_sel['lat_destino']},{viaje_sel['lon_destino']}"
            else:
                destino_param = viaje_sel['destino'].replace(" ", "+")
            
            url_navegacion = f"https://www.google.com/maps/dir/?api=1&origin={origen_param}&destination={destino_param}&travelmode=driving"

            st.link_button("🚀 ¡Iniciar GPS con Coordenadas Reales!", url_navegacion, use_container_width=True, type="primary")
            st.caption("💡 *Esta ruta utiliza las coordenadas satelitales del galpón de salida guardadas en el sistema.*")

            # --- BOTONES DE CONTROL DE ESTADO Y CARGA DE COMPROBANTE ---
            st.write("#### 🛠️ Control de Progreso")
            
            # =========================================================================
            # 🔄 FUENTE DE VERDAD: CONSULTA DIRECTA (IGUAL QUE EN OPERACIONES)
            # =========================================================================
            try:
                conexion = sqlite3.connect(personal_base_datos)
                conexion.row_factory = sqlite3.Row  
                cursor = conexion.cursor()
                cursor.execute("SELECT estatus_viaje FROM viajes WHERE id_viaje = ?", (viaje_id,))
                registro = cursor.fetchone()
                conexion.close()
                
                estatus_actual = registro['estatus_viaje'] if registro else 'Por Salir'
            except Exception as e:
                st.error(f"❌ Error de lectura en BD: {e}")
                estatus_actual = 'Por Salir'

            # =========================================================================
            # 🏗️ FLUJO DE PANTALLAS SIMPLIFICADO (MÉTODO OPERACIONES.PY)
            # =========================================================================
            
            # Si la memoria no está en modo "Cierre", evaluamos las etapas normales de carretera
            if st.session_state.get(f"cerrando_viaje_{viaje_id}") != True:
                
                match estatus_actual:
                    
                    case 'Por Salir':
                        st.warning("📋 El flete está asignado y listo en andén. Debe iniciar el recorrido.")
                        if st.button("🚛 Iniciar Viaje ('En Ruta')", key=f"btn_iniciar_{viaje_id}", use_container_width=True):
                            try:
                                conexion = sqlite3.connect(personal_base_datos)
                                cursor = conexion.cursor()
                                cursor.execute("UPDATE viajes SET estatus_viaje = 'En Ruta' WHERE id_viaje = ?", (viaje_id,))
                                conexion.commit()
                                conexion.close()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error al iniciar: {e}")

                    case 'En Ruta':
                        st.info("🛣️ Estatus: En Ruta. El flete va en tránsito hacia el cliente.")
                        st.markdown("💡 *Al llegar al destino pulse el botón para proceder al cierre del flete...*")
                        
                        # Al pulsar este botón, NO tocamos la base de datos (evitamos que el viaje desaparezca)
                        if st.button("📍 Llegué a Destino (Proceder al Cierre)", key=f"btn_llegue_{viaje_id}", use_container_width=True, type="secondary"):
                            st.session_state[f"cerrando_viaje_{viaje_id}"] = True
                            st.rerun()

                    case _:
                        st.info(f"ℹ️ El viaje se encuentra en estatus: {estatus_actual}")

            # --- LA COMPUERTA DEL CIERRE (Idéntica a tu código administrativo exitoso) ---
            else:
                st.warning("📸 Estatus: En Destino. Para finalizar el flete, tome una foto del comprobante de entrega.")
                
                foto_comprobante = st.file_uploader(
                    "Cargar foto del soporte (Guía sellada/Carga):", 
                    type=["jpg", "jpeg", "png"], 
                    key=f"foto_{viaje_id}"
                )
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("❌ Cancelar Cierre", key=f"btn_cancelar_{viaje_id}", use_container_width=True):
                        st.session_state[f"cerrando_viaje_{viaje_id}"] = None
                        st.rerun()
                        
                with c2:
                    if foto_comprobante is not None:
                        # El botón de confirmación final solo aparece si la foto existe
                        if st.button("💾 Confirmar Entrega y Guardar", key=f"btn_cierre_{viaje_id}", use_container_width=True, type="primary"):
                            # Llama a tu función maestra que calcula finanzas, guarda foto y cambia a 'Entregado'
                            exito = actualizar_estatus_viaje(viaje_id, 'Entregado', personal_base_datos, foto_comprobante)
                            if exito:
                                st.session_state[f"cerrando_viaje_{viaje_id}"] = None
                                st.success("🎉 ¡Flete finalizado, montos procesados y soporte guardado con éxito!")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("❌ Hubo un problema al procesar el cierre financiero del flete.")
                    else:
                        st.button("🏁 Confirmar (Requiere Foto)", disabled=True, use_container_width=True)

    # =========================================================================
    # 📌 PESTAÑA 2: REPORTAR COMBUSTIBLE
    # =========================================================================
    if tab_combustible is not None:
        with tab_combustible:
            st.write("###### ⛽ Registro de Suministro Diésel/Gasolina")
            
            with st.form("form_combustible_chofer", clear_on_submit=True):
                fecha_gasto = st.date_input("📅 Fecha del Suministro:", value=datetime.date.today())
                litros = st.number_input("🧪 Litros Surtidos:", min_value=0.0, step=1.0)
                monto_pagado = st.number_input("💵 Monto Total Pagado ($):", min_value=0.0, step=1.0)
                estacion_servicio = st.text_input("🏪 Estación de Servicio o Ubicación:")
                observaciones_comb = st.text_area("🗒️ Notas adicionales:")
                
                btn_combustible = st.form_submit_button("💾 Guardar Reporte de Combustible", use_container_width=True)
                
            if btn_combustible:
                if litros <= 0 or monto_pagado <= 0:
                    st.error("❌ Error: Debe ingresar valores válidos de litros y costo monetario.")
                else:
                    try:
                        conexion = sqlite3.connect(personal_base_datos)
                        cursor = conexion.cursor()
                        cursor.execute('''
                            INSERT INTO control_combustible (cedula_conductor, fecha, litros, monto_usd, estacion, observaciones)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (cedula_conductor, str(fecha_gasto), litros, monto_pagado, estacion_servicio, observaciones_comb))
                        conexion.commit()
                        conexion.close()
                        st.success("🎉 ¡Reporte de combustible guardado con éxito!")
                    except Exception as e:
                        st.error(f"❌ Error al registrar en base de datos: {e}")

            # 🔄 BOTÓN DE RETORNO AL MENÚ PRINCIPAL
            st.write("---")
            if st.button("🏠 Volver al Menú Principal", key="btn_home_comb", use_container_width=True):
                st.session_state["chofer_pagina"] = "Menu Principal"
                st.rerun()

    # =========================================================================
    # 📌 PESTAÑA 3: HISTORIAL DE FLETES (FILTRADO POR MESES Y CABECERAS LIMPIAS)
    # =========================================================================
    with tab_historial:
        st.write("#### 📜 Mis Fletes Ejecutados")
        
        # --- FILTRO DE MESES PARA EL CELULAR ---
        # Mapeo de meses en español para que sea amigable
        meses_dicc = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        
        # Obtenemos el año y mes actual usando el alias 'dt'
        hoy = dt.date.today()
        ano_actual = hoy.year
        mes_actual = hoy.month
        
        # Creamos una lista de opciones para los últimos meses (Ej: el mes actual y los 5 anteriores)
        opciones_meses = []
        for i in range(6):
            # Restamos meses de forma matemática para calcular el histórico reciente
            m = mes_actual - i
            a = ano_actual
            if m <= 0:
                m += 12
                a -= 1
            opciones_meses.append((a, m))
            
        # Formateamos el selector para que el chofer vea "Julio 2026", "Junio 2026", etc.
        mes_seleccionado = st.selectbox(
            "📅 Seleccione el mes a consultar:",
            options=opciones_meses,
            format_func=lambda x: f"{meses_dicc[x[1]]} {x[0]}" if x is not None else ""
        )
        
        # 💡 CONTROL CRÍTICO: Si no hay opciones, evitamos que rompa la app
        if mes_seleccionado is None:
            #import datetime
            hoy = datetime.date.today()
            mes_seleccionado = (hoy.year, hoy.month)
        
        # Calculamos la fecha de inicio y fin del mes seleccionado para el SQL
        ano_sel, mes_sel = mes_seleccionado
        f_inicio_mes = f"{ano_sel}-{mes_sel:02d}-01"
        # Para el fin de mes, apuntamos de forma segura al inicio del mes siguiente
        if mes_sel == 12:
            f_fin_mes = f"{ano_sel + 1}-01-01"
        else:
            f_fin_mes = f"{ano_sel}-{mes_sel + 1:02d}-01"
            
        try:
            conexion = sqlite3.connect(personal_base_datos)
            # 🎯 CLAVE: Añadimos la condición de fechas en el WHERE usando date()
            df_historial = pd.read_sql_query('''
                SELECT id_viaje, fecha_despacho, cliente_solicitante, origen, destino, estatus_viaje, tipo_material, num_pedido, pago_chofer_usd
                FROM viajes 
                WHERE cedula_conductor = ? 
                  AND estatus_viaje NOT IN ('Solicitado', 'Por Salir', 'En Ruta')
                  AND date(fecha_despacho) >= date(?)
                  AND date(fecha_despacho) < date(?)
                ORDER BY id_viaje DESC
            ''', conexion, params=(cedula_conductor, f_inicio_mes, f_fin_mes))
            conexion.close()
        except Exception as e:
            st.error(f"❌ Error al cargar historial: {e}")
            df_historial = pd.DataFrame()

        if df_historial.empty:
            st.info(f"ℹ️ No registras viajes finalizados en {meses_dicc[mes_sel]} {ano_sel}.")
        else:
            # 🔄 MAPEO DE CABECERAS: Renombramos los campos técnicos a nombres amigables
            df_visual = df_historial.rename(columns={
                'id_viaje': 'Flete N°',
                'fecha_despacho': 'Fecha',
                'cliente_solicitante': 'Cliente',
                'origen': 'Origen',
                'destino': 'Destino',
                'estatus_viaje': 'Estatus',
                'tipo_material': 'Material',
                'num_pedido': 'Pedido',
                'pago_chofer_usd': 'Pago ($)'
            })

            # Mostramos la tabla limpia en el celular con las columnas elegantes
            st.dataframe(df_visual, use_container_width=True, hide_index=True)
            
            st.write("---")
            st.write("🔍 **Consulta Individual Detallada**")
            
            # Formateamos el selector con los datos del flete, cliente y pedido
            dicc_historial = {}
            for _, row in df_historial.iterrows():
                id_v = row['id_viaje']
                cliente = row['cliente_solicitante']
                pedido = row['num_pedido'] if pd.notna(row['num_pedido']) and str(row['num_pedido']).strip() != "" else "S/N"
                dicc_historial[id_v] = f"Flete N° {id_v} - {cliente} (Ped: {pedido})"
            
            id_historial_sel = st.selectbox(
                "Seleccione un flete pasado para ver detalles:", 
                options=list(dicc_historial.keys()),
                format_func=lambda x: str(dicc_historial.get(x, f"Flete N° {x}"))
            )
            
            if id_historial_sel:
                try:
                    conexion = sqlite3.connect(personal_base_datos)
                    cursor = conexion.cursor()
                    cursor.execute('''
                        SELECT cliente_solicitante, origen, destino, tipo_material, peso_carga_kg, estatus_viaje, num_pedido, tipo_viaje, pago_chofer_usd
                        FROM viajes 
                        WHERE id_viaje = ?
                    ''', (id_historial_sel,))
                    v_det = cursor.fetchone()
                    conexion.close()
                    
                    if v_det:
                        pago_flotante = float(v_det[8]) if v_det[8] is not None else 0.0
                        st.info(f"""
                        **Detalle del Flete N° {id_historial_sel}**
                        * **Cliente:** {v_det[0]}
                        * **N° Pedido:** {v_det[6] if v_det[6] else "S/N"}
                        * **Ruta:** {v_det[1]} ➡️ {v_det[2]}
                        * **Material:** {v_det[3]} ({v_det[4]} Kg)
                        * **Tipo de viaje:** {v_det[7]}
                        * **Estatus Final:** {v_det[5]}
                        * **Pago al Chofer (USD):** ${pago_flotante:.2f}
                        """)
                except Exception as e:
                    st.error(f"Error al abrir detalle individual: {e}")

        # 🔄 BOTÓN DE RETORNO AL MENÚ PRINCIPAL
        st.write("---")

        st.success("Para salir de aquí haz clic o tap en la pestaña de Fletes Activos")

        #if st.button("🏠 Volver al Menú Principal", key="btn_home_hist", use_container_width=True):
        #    st.session_state["chofer_pagina"] = "Menu Principal"
        #    st.rerun()

    # =========================================================================
    # 📌 SECCIÓN DE AYUDA Y SOPORTE EN LA BARRA LATERAL
    # =========================================================================
    with st.sidebar:
        st.write("---")
        st.caption("⚙️ SOPORTE EXPREX")
        
        # Un expander dentro del sidebar para que no ocupe espacio visual directo
        with st.expander("❓ Manual de Ayuda", expanded=False):
            st.markdown("""
            **Guía Rápida de Uso:**
            
            * 📱 **Pantalla:** Diseñado para uso vertical en teléfonos móviles.
            * 🔍 **Historial:** Si no ves un viaje pasado, verifica tener seleccionado el mes correcto en el filtro.
            * 🔄 **Actualizar:** Si realizas un cambio y no se refleja, usa el botón de retornar al menú o recarga la página.
            * 📇 **Datos:** Los montos de pago y datos de clientes se actualizan en tiempo real desde la base de datos central.
            
            ---
            💬 **¿Problemas con la App?**  
            Comunícate de inmediato con el administrador del sistema para reportar fallas o solicitar soporte técnico.
            """)
            
            
        # --- TÉRMINOS Y CONDICIONES DESDE TERMINOS.TXT ---
        with st.expander("📄 Términos y Condiciones", expanded=False):
            # Mostramos el contenido exacto del archivo txt en pantalla
            st.markdown(texto_legal_choferes)
        st.markdown("---")    
        if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario_cedula = ""
            st.session_state.usuario_nombre = ""
            st.session_state.usuario_rol = ""
            st.session_state.cliente_id = None
            st.session_state.vista_login = "login"
            st.rerun()
        st.markdown("---")
        st.caption("ExpreX Choferes v1.6.1 • 🔒 Local Safe")

# ==========================================================================================================

def actualizar_estatus_viaje(id_viaje, nuevo_estatus, db_path, archivo_foto_streamlit=None):
    """
    Función Única Centralizada para controlar el ciclo de vida de un flete con el alias 'st'.
    """
    try:
        conexion = sqlite3.connect(db_path)
        cursor = conexion.cursor()
        
        if nuevo_estatus == 'Entregado':
            # 📁 1️⃣ GUARDADO FÍSICO DE LA FOTO
            ruta_foto_final = None
            if archivo_foto_streamlit is not None:
                carpeta_destino = "fotos_entregas"
                if not os.path.exists(carpeta_destino):
                    os.makedirs(carpeta_destino)
                
                extension = archivo_foto_streamlit.name.split(".")[-1]
                nombre_archivo = f"viaje_{id_viaje}_evidencia.{extension}"
                ruta_foto_final = os.path.join(carpeta_destino, nombre_archivo)
                
                with open(ruta_foto_final, "wb") as f:
                    f.write(archivo_foto_streamlit.getbuffer())

            # 2️⃣ LEER DATOS REALES DEL VIAJE
            cursor.execute("""
                SELECT monto_flete_usd, cedula_conductor, distancia_km, tipo_viaje, id_cliente 
                FROM viajes 
                WHERE id_viaje = ?
            """, (id_viaje,))
            res_v = cursor.fetchone()
            
            if res_v:
                # 🎯 CORRECCIÓN: Si el flete inicial es None, le ponemos 0.0 para que no explote
                monto_flete_total = float(res_v[0]) if res_v[0] is not None else 0.0
                cedula_chofer = res_v[1]
                distancia_real = float(res_v[2]) if res_v[2] is not None else 0.0
                tipo_viaje = res_v[3]
                id_cliente = res_v[4]
                
                # 📊 Recálculo Matemático
                # 🎯 CORRECCIÓN: Si la distancia es mayor a 0 usa el max, si es 0 usa mínimo 8.0 por defecto
                distancia_calculo = max(distancia_real, 8.0) if distancia_real > 0 else 8.0
                tarifa_por_km = 4.0 if tipo_viaje == 'Express' else 2.5
                monto_flete_total = round(distancia_calculo * tarifa_por_km, 2)
                
                # --- 🏦 SECCIÓN: ACTUALIZACIÓN DE SALDO EN TABLA CLIENTES ---
                if id_cliente is not None:
                    cursor.execute("SELECT limite_credito_usd, saldo_pendiente_usd, credito_disponible_usd FROM clientes WHERE id_cliente = ?", (id_cliente,))
                    res_cli = cursor.fetchone()
                    
                    if res_cli:
                        limite_credito_actual = float(res_cli[0]) if res_cli[0] is not None else 0.0
                        saldo_actual = float(res_cli[1]) if res_cli[1] is not None else 0.0
                        credito_disponible_actual = float(res_cli[2]) if res_cli[2] is not None else 0.0
                        
                        credito_disponible_actual = round(credito_disponible_actual - monto_flete_total, 2)
                        saldo_actual = round(saldo_actual + monto_flete_total, 2)
                        
                        cursor.execute("""
                            UPDATE clientes 
                            SET limite_credito_usd = ?, saldo_pendiente_usd = ?, credito_disponible_usd = ? 
                            WHERE id_cliente = ?
                        """, (limite_credito_actual, saldo_actual, credito_disponible_actual, id_cliente))

                # ------------------------------------------------------------------

                # Fórmulas Financieras Oficiales
                cursor.execute("SELECT propio FROM conductores WHERE cedula = ?", (cedula_chofer,))
                res_c = cursor.fetchone()
                es_propio = res_c[0] if res_c and res_c[0] else "No"
                
                descuento = round(monto_flete_total * 0.15, 2)
                importe_neto = round(monto_flete_total - descuento, 2)
                porcentaje_chofer = 0.75 if es_propio == "Sí" else 0.37
                pago_chofer = round(importe_neto * porcentaje_chofer, 2)
                beneficio_exprex = round(importe_neto - pago_chofer, 2)
                
                # 💾 Inyección total en la tabla 'viajes'
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
                    ruta_foto_final, monto_flete_total, descuento, 
                    importe_neto, pago_chofer, beneficio_exprex, id_viaje
                ))
                conexion.commit()
                st.info("Espere mientras se procesan los cálculos financieros del flete...")
                time.sleep(1)
            else:
                st.error("❌ No se encontraron datos para procesar el flete financiero.")
                conexion.close()
                return False
                
        else:
            cursor.execute("UPDATE viajes SET estatus_viaje = ? WHERE id_viaje = ?", (nuevo_estatus, id_viaje))
            conexion.commit()
            
        conexion.close()
        return True
        
    except Exception as e:
        import traceback
        print("\n=== 🛑 DETALLE COMPLETO DEL ERROR EN BASE DE DATOS ===")
        traceback.print_exc()  # Esto imprimirá en tu terminal la línea exacta que falla
        print("=======================================================\n")
        
        st.error(f"❌ Error en el módulo maestro financiero: {e}")
        return False

