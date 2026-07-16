import streamlit as st
import pandas as pd
import datetime as dt
#import psycopg2
import time
import os
import sys
#import base64

# 🔍 CONTROL DE RUTAS CRÍTICO
ruta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ruta_raiz not in sys.path:
    sys.path.insert(0, ruta_raiz)

# E importas desde el paquete modulos
from modulos.utils import obtener_conexion_db, contar_viajes_por_salir, reproducir_alerta_victoria
from modulos.version_app import mostrar_version_de_la_app
from modulos.soporte import llamar_soporte

ruta_terminos = os.path.join("modulos", "terminos.txt")

try:
    with open(ruta_terminos, "r", encoding="utf-8") as f:
        texto_legal_choferes = f.read()
except Exception as e:
    texto_legal_choferes = f"⚠️ No se pudo cargar el archivo de términos en `{ruta_terminos}`: {e}"


def verificar_vehiculo_propio(cedula_chofer):
    """
    Consulta en PostgreSQL (Railway) si el vehículo del conductor es propio.
    Retorna True si es propio ('Sí'), o False si es de la empresa ('No').
    """
    try:
        # MIGRADO A POSTGRESQL
        with obtener_conexion_db() as conn:
            with conn.cursor() as cursor:
                # En Postgres usamos %s en lugar de ? para los parámetros
                cursor.execute("SELECT propio FROM conductores WHERE cedula = %s", (cedula_chofer,))
                resultado = cursor.fetchone()
                
        if resultado and resultado[0] == "Sí":
            return True
    except Exception as e:
        print(f"⚠️ Error al verificar propiedad en tabla conductores: {e}")
    
    return False

def renderizar_panel_conductor(cedula_conductor):
    
    st.write(f"##### Panel de Operaciones - Conductor")
    
    # Colocar aquí para la barra lateral del Chofer (se despliega de lado en el tlf)
    tasa = st.session_state.get('tasa_bcv', '0.00')
    st.sidebar.success(f"Tasa BCV activa: {tasa} Bs.")

    # Si el chofer tiene dudas de si le asignaron algo, le da un toque aquí.
    if st.button("🔄 Actualizar y Buscar Nuevos Fletes", use_container_width=True):
        cedula = st.session_state.get("cedula_chofer") 

        cedula_segura = str(cedula) if cedula is not None else ""
        fletes_nuevos = contar_viajes_por_salir(cedula_segura)
        
        if fletes_nuevos > 0:
            reproducir_alerta_victoria() # ¡Suena la fanfarria en el celular!
            st.success(f"🚨 ¡Atención! Te asignaron {fletes_nuevos} flete(s) nuevo(s).")
        else:
            st.info("No hay fletes nuevos asignados por ahora.")
        st.rerun()

    # 1. Validación de propiedad (PostgreSQL)
    es_vehiculo_propio = verificar_vehiculo_propio(cedula_conductor)

    # 2. Creamos las pestañas de forma condicional para reutilizar tus variables
    if es_vehiculo_propio:
        # Si es propio, solo creamos 2 pestañas, y asignamos un "cascarón vacío" a la de combustible
        tab_fletes, tab_historial = st.tabs(["📋 Fletes", "📊 Historial"])
        tab_combustible = None  # Al ser None, el bloque 'with tab_combustible' no se ejecutará
    else:
        # Si es de la empresa, se crean las 3 pestañas originales exactamente igual
        tab_fletes, tab_combustible, tab_historial = st.tabs(["📋 Fletes Activos", "⛽ Reportar Combustible", "📜 Historial"])

    # =========================================================================
    # 📌 PESTAÑA 1: RUTAS ACTIVAS Y MAPA GPS
    # =========================================================================
    with tab_fletes:

        df_mis_viajes = pd.DataFrame()
        try:
            # 🛠️ MIGRADO A POSTGRESQL (RAILWAY)
            with obtener_conexion_db() as conexion:
                # Cambiamos el marcador '?' por '%s' para PostgreSQL
                sql_viajes = '''
                    SELECT v.id_viaje, v.cliente_solicitante, v.origen, v.destino, v.tipo_viaje,
                           v.distancia_km, v.peso_carga_kg, v.tipo_material, v.estatus_viaje, v.num_pedido,
                           s.latitud AS lat_origen, s.longitud AS lon_origen,
                           v.latitud_entrega AS lat_destino, v.longitud_entrega AS lon_destino,
                           v.persona_contacto_entrega, v.telefono_contacto_entrega,
                           c.razon_social AS empresa_cliente 
                    FROM viajes v
                    LEFT JOIN sucursales s ON v.origen = s.nombre_agencia
                    LEFT JOIN clientes c ON v.id_cliente = c.id_cliente 
                    WHERE v.cedula_conductor = %s 
                      AND v.estatus_viaje IN ('Por Salir', 'En Ruta')
                    ORDER BY v.id_viaje DESC
                '''
                df_mis_viajes = pd.read_sql_query(sql_viajes, conexion, params=(cedula_conductor,))
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

            # 🎯 Conversión segura a numérico para evitar conflictos de tipo de datos en las coordenadas
            lat_orig = pd.to_numeric(viaje_sel['lat_origen'], errors='coerce')
            lon_orig = pd.to_numeric(viaje_sel['lon_origen'], errors='coerce')
            lat_dest = pd.to_numeric(viaje_sel['lat_destino'], errors='coerce')
            lon_dest = pd.to_numeric(viaje_sel['lon_destino'], errors='coerce')

            # Validación ideal definitiva adaptada:
            if pd.notna(lat_orig) and pd.notna(lon_orig) and lat_orig != 0 and lon_orig != 0:
                origen_param = f"{lat_orig},{lon_orig}"
            else:
                origen_param = str(viaje_sel['origen']).replace(" ", "+")

            if pd.notna(lat_dest) and pd.notna(lon_dest) and lat_dest != 0 and lon_dest != 0:
                destino_param = f"{lat_dest},{lon_dest}"
            else:
                destino_param = str(viaje_sel['destino']).replace(" ", "+")
            
            url_navegacion = f"https://www.google.com/maps/dir/?api=1&origin={origen_param}&destination={destino_param}&travelmode=driving"

            st.link_button("🚀 ¡Iniciar GPS con Coordenadas Reales!", url_navegacion, use_container_width=True, type="primary")
            st.caption("💡 *Esta ruta utiliza las coordenadas satelitales del galpón de salida guardadas en el sistema.*")

            # --- BOTONES DE CONTROL DE ESTADO Y CARGA DE COMPROBANTE ---
            st.write("#### 🛠️ Control de Progreso")
            
            # =========================================================================
            # 🔄 FUENTE DE VERDAD: CONSULTA DIRECTA (IGUAL QUE EN OPERACIONES)
            # =========================================================================
            try:
                # 🛠️ MIGRADO A POSTGRESQL (RAILWAY)
                with obtener_conexion_db() as conexion:
                    with conexion.cursor() as cursor:
                        # Usamos %s en lugar de ? para la consulta
                        cursor.execute("SELECT estatus_viaje FROM viajes WHERE id_viaje = %s", (viaje_id,))
                        registro = cursor.fetchone()
                
                # En Postgres con cursor estándar, el resultado viene como tupla indexada
                estatus_actual = registro[0] if registro else 'Por Salir'
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
                                # 🛠️ MIGRADO A POSTGRESQL (RAILWAY)
                                with obtener_conexion_db() as conexion:
                                    with conexion.cursor() as cursor:
                                        cursor.execute(
                                            "UPDATE viajes SET estatus_viaje = 'En Ruta' WHERE id_viaje = %s", 
                                            (viaje_id,)
                                        )
                                    conexion.commit()
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
                            
                            # 🛠️ PASAMOS EL FLUJO DE POSTGRESQL A TU FUNCIÓN MAESTRA FINANCIERA
                            # Nota: internamente 'actualizar_estatus_viaje' debe usar obtener_conexion_db()
                            exito = actualizar_estatus_viaje(viaje_id, 'Entregado', foto_comprobante)
                            
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
                # Usamos dt.date.today() que es el alias limpio que dejamos arriba
                fecha_gasto = st.date_input("📅 Fecha del Suministro:", value=dt.date.today())
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
                        # 🛠️ MIGRADO A POSTGRESQL (RAILWAY)
                        with obtener_conexion_db() as conexion:
                            with conexion.cursor() as cursor:
                                # Reemplazamos los '?' por '%s' para la sintaxis de Postgres
                                cursor.execute('''
                                    INSERT INTO control_combustible (cedula_conductor, fecha, litros, monto_usd, estacion, observaciones)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                ''', (cedula_conductor, str(fecha_gasto), litros, monto_pagado, estacion_servicio, observaciones_comb))
                            conexion.commit()
                        st.success("🎉 ¡Reporte de combustible guardado con éxito!")
                    except Exception as e:
                        st.error(f"❌ Error al registrar en base de datos: {e}")

            # 🔄 BOTÓN DE RETORNO AL MENÚ PRINCIPAL
            st.write("---")
            st.caption("💬 Para volver al inicio pulse o haga tap en la pestaña Fletes Activos")

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
        
        # 💡 CONTROL CRÍTICO CORREGIDO: Usamos el alias 'dt' para evitar el NameError
        if mes_seleccionado is None:
            hoy = dt.date.today()
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
            # 🛠️ MIGRADO A POSTGRESQL (RAILWAY)
            with obtener_conexion_db() as conexion:
                # Adaptamos la sintaxis de fecha y usamos marcadores %s para Postgres
                query_historial = '''
                    SELECT id_viaje, fecha_despacho, cliente_solicitante, origen, destino, estatus_viaje, tipo_material, num_pedido, pago_chofer_usd
                    FROM viajes 
                    WHERE cedula_conductor = %s 
                      AND estatus_viaje NOT IN ('Solicitado', 'Por Salir', 'En Ruta')
                      AND fecha_despacho::date >= %s::date
                      AND fecha_despacho::date < %s::date
                    ORDER BY id_viaje DESC
                '''
                df_historial = pd.read_sql_query(query_historial, conexion, params=(cedula_conductor, f_inicio_mes, f_fin_mes))
        except Exception as e:
            st.error(f"❌ Error al cargar historial: {e}")
            df_historial = pd.DataFrame()

        if df_historial.empty:
            st.info(f"ℹ️ No registras viajes finalizados en {meses_dicc[mes_sel]} {ano_sel}.")
        else:
            # =========================================================================
            # 📊 NUEVA SECCIÓN: MÉTRICAS DEL MES (ENTRE EL SELECTOR Y EL LISTADO)
            # =========================================================================
            total_viajes = len(df_historial)
            
            # Sumamos los pagos asegurándonos de tratar los nulos como 0.0
            monto_acumulado = pd.to_numeric(df_historial['pago_chofer_usd'], errors='coerce').fillna(0.0).sum()
            
            # Usamos columnas adaptadas para que queden alineadas y compactas en el celular
            col_met1, col_met2 = st.columns(2, gap="small")
            
            with col_met1:
                st.metric(
                    label="Viajes Realizados", 
                    value=f"{total_viajes}"
                )
                
            with col_met2:
                st.metric(
                    label="Monto Acumulado", 
                    value=f"${monto_acumulado:,.2f}"
                )
            
            st.write("---")  # Línea sutil divisoria

            # ======================================================================================================

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
                    # 🛠️ MIGRADO A POSTGRESQL (RAILWAY)
                    with obtener_conexion_db() as conexion:
                        with conexion.cursor() as cursor:
                            cursor.execute('''
                                SELECT cliente_solicitante, origen, destino, tipo_material, peso_carga_kg, estatus_viaje, num_pedido, tipo_viaje, pago_chofer_usd
                                FROM viajes 
                                WHERE id_viaje = %s
                            ''', (id_historial_sel,))
                            v_det = cursor.fetchone()
                    
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
            * 🛠️ **Tus viajes pendientes se actualizan al entrar a la aplicación. Para verificar si tienes viajes pendientes, pulsa el botón "🔄 Actualizar y Buscar Nuevos Fletes"
            * 💡 **Si el vehículo que manejas es de la empresa y te toca echarle combustible, podrás reportarlo a través de la pestaña: Reportar Combustible.
            * 🔍 **Historial:** Si no ves un viaje pasado, verifica tener seleccionado el mes correcto en el filtro.
            * 🔄 **Actualizar:** Si realizas un cambio y no se refleja, usa el botón de retornar al menú o recarga la página.
            * 📇 **Datos:** Los montos de pago y datos de clientes se actualizan en tiempo real desde la base de datos central.
            
            ---
            💬 **¿Problemas con la App?**  
            Comunícate de inmediato con el administrador del sistema para reportar fallas o solicitar soporte técnico.
            """)
            
        # --- TÉRMINOS Y CONDICIONES DESDE TERMINOS.TXT ---
        with st.expander("📄 Términos y Condiciones", expanded=False):
            st.markdown(texto_legal_choferes)
            
        st.markdown("---")    

        # =========================================================================
        # ⚙️ CAMBIO DEL BOTÓN DE SOPORTE POR EL LINK_BUTTON DINÁMICO
        # =========================================================================
        import urllib.parse

        # 1. Obtenemos el teléfono del chofer logueado (si está en session_state, si no usamos el tuyo por defecto)
        telefono_chofer = st.session_state.get('usuario_telefono', '584140335554')
        
        # 2. Armamos y codificamos el mensaje
        mensaje_soporte = "Hola, soy chofer de ExpreX y necesito soporte técnico con mi usuario en la aplicación de Exprex Logística."
        mensaje_codificado = urllib.parse.quote(mensaje_soporte)
        
        # 3. Generamos la URL
        url_whatsapp = f"https://wa.me/{telefono_chofer}?text={mensaje_codificado}"

        # 4. Colocamos el link_button directo en el sidebar
        st.link_button("❓ Soporte", url=url_whatsapp, use_container_width=True)
        # =========================================================================

        # Usamos st.button directo especificando el contenedor del sidebar de forma limpia
        if st.button("🚪 Cerrar Sesión", use_container_width=True, key="btn_logout_sidebar"):
            st.session_state.autenticado = False
            st.session_state.usuario_cedula = ""
            st.session_state.usuario_nombre = ""
            st.session_state.usuario_rol = ""
            st.session_state.cliente_id = None
            st.session_state.vista_login = "login"
            st.rerun()
            
        st.markdown("---")
        mostrar_version_de_la_app()
        

# ==========================================================================================================

def actualizar_estatus_viaje(id_viaje, nuevo_estatus, archivo_foto_streamlit=None):
    """
    Función Única Centralizada para controlar el ciclo de vida de un flete en PostgreSQL.
    Guarda la foto físicamente en el disco del servidor y registra la ruta de texto en la base de datos.
    """
    try:
        import psycopg2
        import os  # 👈 Necesario para manejar las carpetas y rutas físicas
        
        # 🛠️ MIGRADO A POSTGRESQL (RAILWAY)
        with obtener_conexion_db() as conexion:
            with conexion.cursor() as cursor:
                
                if nuevo_estatus == 'Entregado':
                    # 📁 1️⃣ GUARDADO FÍSICO DE LA FOTO Y OBTENCIÓN DE RUTA DE TEXTO
                    ruta_base_datos = None  # Esto es lo que guardaremos en Postgres
                    
                    if archivo_foto_streamlit is not None:
                        # Definimos y aseguramos la existencia de la carpeta local
                        directorio_fotos = "exprex/fotos_entregas"
                        os.makedirs(directorio_fotos, exist_ok=True)
                        
                        # Generamos el nombre del archivo basado en el id_viaje
                        nombre_archivo = f"viaje_{id_viaje}_evidencia.jpg"
                        ruta_fisica_local = os.path.join(directorio_fotos, nombre_archivo)
                        
                        # Extraemos los bytes del buffer de Streamlit
                        bytes_foto = archivo_foto_streamlit.getvalue()
                        
                        # Guardamos el archivo físicamente en el servidor
                        with open(ruta_fisica_local, "wb") as archivo_disco:
                            archivo_disco.write(bytes_foto)
                        
                        # Definimos la ruta relativa que guardará la base de datos (Ej: 'fotos_entregas/viaje_126_evidencia.jpg')
                        ruta_base_datos = f"fotos_entregas/{nombre_archivo}"

                    # 2️⃣ LEER DATOS REALES DEL VIAJE
                    cursor.execute("""
                        SELECT monto_flete_usd, cedula_conductor, distancia_km, tipo_viaje, id_cliente 
                        FROM viajes 
                        WHERE id_viaje = %s
                    """, (id_viaje,))
                    res_v = cursor.fetchone()
                    
                    if res_v:
                        # 🎯 CONTROL DE TIPOS: Forzamos float() por si Postgres devuelve tipos Decimal (Numeric)
                        monto_flete_total = float(res_v[0]) if res_v[0] is not None else 0.0
                        cedula_chofer = res_v[1]
                        distancia_real = float(res_v[2]) if res_v[2] is not None else 0.0
                        tipo_viaje = res_v[3]
                        id_cliente = res_v[4]
                        
                        # 📊 Recálculo Matemático
                        distancia_calculo = max(distancia_real, 8.0) if distancia_real > 0 else 8.0
                        tarifa_por_km = 4.0 if tipo_viaje == 'Express' else 2.5
                        monto_flete_total = round(distancia_calculo * tarifa_por_km, 2)
                        
                        # --- 🏦 SECCIÓN: ACTUALIZACIÓN DE SALDO EN TABLA CLIENTES ---
                        if id_cliente is not None:
                            cursor.execute("""
                                SELECT limite_credito_usd, saldo_pendiente_usd, credito_disponible_usd 
                                FROM clientes 
                                WHERE id_cliente = %s
                            """, (id_cliente,))
                            res_cli = cursor.fetchone()
                            
                            if res_cli:
                                limite_credito_actual = float(res_cli[0]) if res_cli[0] is not None else 0.0
                                saldo_actual = float(res_cli[1]) if res_cli[1] is not None else 0.0
                                credito_disponible_actual = float(res_cli[2]) if res_cli[2] is not None else 0.0
                                
                                credito_disponible_actual = round(credito_disponible_actual - monto_flete_total, 2)
                                saldo_actual = round(saldo_actual + monto_flete_total, 2)
                                
                                cursor.execute("""
                                    UPDATE clientes 
                                    SET limite_credito_usd = %s, saldo_pendiente_usd = %s, credito_disponible_usd = %s 
                                    WHERE id_cliente = %s
                                """, (limite_credito_actual, saldo_actual, credito_disponible_actual, id_cliente))

                        # ------------------------------------------------------------------
                        # Fórmulas Financieras Oficiales
                        cursor.execute("SELECT propio FROM conductores WHERE cedula = %s", (cedula_chofer,))
                        res_c = cursor.fetchone()
                        es_propio = res_c[0] if res_c and res_c[0] else "No"
                        
                        descuento = round(monto_flete_total * 0.15, 2)
                        importe_neto = round(monto_flete_total - descuento, 2)
                        porcentaje_chofer = 0.75 if es_propio == "Sí" else 0.37
                        pago_chofer = round(importe_neto * porcentaje_chofer, 2)
                        beneficio_exprex = round(importe_neto - pago_chofer, 2)
                        
                        # 💾 Inyección total en la tabla 'viajes' (Guarda la ruta de texto en Postgres)
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
                            ruta_base_datos,  # 👈 Guardamos la ruta de texto de la imagen
                            monto_flete_total, descuento, importe_neto, 
                            pago_chofer, beneficio_exprex, id_viaje
                        ))
                        conexion.commit()
                        st.info("Espere mientras se procesan los cálculos financieros del flete...")
                        time.sleep(1)
                    else:
                        st.error("❌ No se encontraron datos para procesar el flete financiero.")
                        return False
                        
                else:
                    cursor.execute("UPDATE viajes SET estatus_viaje = %s WHERE id_viaje = %s", (nuevo_estatus, id_viaje))
                    conexion.commit()
                    
        return True
        
    except Exception as e:
        import traceback
        print("\n=== 🛑 DETALLE COMPLETO DEL ERROR EN BASE DE DATOS VALIDADOR ===")
        traceback.print_exc()
        print("=================================================================\n")
        
        st.error(f"❌ Error en el módulo maestro financiero: {e}")
        return False
