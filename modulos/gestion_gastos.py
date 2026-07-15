import streamlit as st
import pandas as pd
from datetime import datetime

# Importamos la conexión centralizada desde tus utilidades
from modulos.utils import obtener_conexion_db

def mostrar_modulo_gastos():
    st.subheader("💸 Control y Gestión de Gastos Operativos")
    st.markdown("---")
    
    # =========================================================================
    # 🗃️ CARGAR LISTAS DE CONTROL DESDE LA BD
    # =========================================================================
    lista_placas_registro = ["General (No aplica a vehículo)"]
    lista_placas_filtro = ["Todos los vehículos", "General"]
    
    try:
        with obtener_conexion_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT placa FROM vehiculos ORDER BY placa ASC")
                filas = cursor.fetchall()
                if filas:
                    placas_lista = [str(fila[0]) for fila in filas]
                    lista_placas_registro.extend(placas_lista)
                    lista_placas_filtro.extend(placas_lista)
    except Exception:
        pass

    categorias_gastos = [
        "Estacionamiento", 
        "Mantenimiento", 
        "Seguros", 
        "Impuestos", 
        "Grúas", 
        "Multas", 
        "Gastos Varios"
    ]

    # Separamos el módulo en dos pestañas
    tab_registro, tab_consulta = st.tabs(["📝 Registrar Nuevo Gasto", "🔍 Consultar y Reportes de Gastos"])

    # =========================================================================
    # PESTAÑA 1: REGISTRO
    # =========================================================================
    with tab_registro:
        col_form, col_vista_rapida = st.columns([1, 1.2])
        
        with col_form:
            st.subheader("Formulario de Egreso")
            with st.form("form_registro_gasto", clear_on_submit=True):
                fecha_gasto = st.date_input("🗓️ Fecha del Gasto:", datetime.now().date(), key="g_fecha")
                vehiculo_sel = st.selectbox("🚛 Vehículo Asociado (Placa):", options=lista_placas_registro, key="g_placa")
                categoria_sel = st.selectbox("🗂️ Categoría del Gasto:", categorias_gastos, key="g_cat")
                monto_usd = st.number_input("💰 Monto ($ USD):", min_value=0.00, step=0.50, format="%.2f", key="g_monto")
                observaciones = st.text_area("📝 Observaciones / Descripción:", placeholder="Detalles del gasto...", key="g_obs")
                
                boton_guardar = st.form_submit_button("💾 Asentar Gasto", use_container_width=True, type="primary")
                
                if boton_guardar:
                    if monto_usd <= 0:
                        st.error("❌ El monto del gasto debe ser mayor a $ 0.00")
                    else:
                        try:
                            fecha_str = fecha_gasto.strftime("%Y-%m-%d")
                            placa_a_guardar = "General" if vehiculo_sel == "General (No aplica a vehículo)" else str(vehiculo_sel)
                            
                            with obtener_conexion_db() as conexion:
                                with conexion.cursor() as cursor:
                                    sql_insert = """
                                        INSERT INTO gastos (fecha, categoria, monto_usd, observaciones, placa_vehiculo)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """
                                    cursor.execute(sql_insert, (fecha_str, categoria_sel, float(monto_usd), observaciones.strip(), placa_a_guardar))
                                    conexion.commit()
                            
                            st.session_state["msg_exito"] = f"✅ Gasto asentado: {categoria_sel} (${monto_usd:,.2f})"
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al guardar en PostgreSQL: {e}")

            if "msg_exito" in st.session_state:
                st.success(st.session_state["msg_exito"])
                del st.session_state["msg_exito"]

        with col_vista_rapida:
            st.subheader("📋 Últimos 15 Asientos")
            df_ultimos = pd.DataFrame()
            try:
                with obtener_conexion_db() as conexion:
                    with conexion.cursor() as cursor:
                        query_ultimos = """
                            SELECT fecha AS "Fecha", placa_vehiculo AS "Placa", categoria AS "Categoría", monto_usd AS "Monto ($)" 
                            FROM gastos 
                            ORDER BY fecha DESC, id_gasto DESC 
                            LIMIT 15
                        """
                        cursor.execute(query_ultimos)
                        filas = cursor.fetchall()
                        if cursor.description:
                            columnas = [desc[0] for desc in cursor.description]
                            df_ultimos = pd.DataFrame(filas, columns=columnas)
                
                if not df_ultimos.empty:
                    st.dataframe(df_ultimos, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay gastos recientes.")
            except Exception as e:
                st.error(f"Error al cargar últimos asientos: {e}")

    # =========================================================================
    # PESTAÑA 2: EL MOTOR DE CONSULTAS + EDICIÓN
    # =========================================================================
    with tab_consulta:
        st.write("#### 📊 Buscador Avanzado de Gastos")
        
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        hoy = datetime.now().date()
        primer_dia_mes = hoy.replace(day=1)
        
        with col_c1:
            f_inicio = st.date_input("🗓️ Desde:", primer_dia_mes, key="f_busqueda_inicio")
        with col_c2:
            f_fin = st.date_input("🗓️ Hasta:", hoy, key="f_busqueda_fin")
        with col_c3:
            v_filtro = st.selectbox("🚛 Filtrar por Vehículo:", lista_placas_filtro, key="f_busqueda_placa")
        with col_c4:
            lista_cat_filtro = ["Todas las categorías"] + categorias_gastos
            c_filtro = st.selectbox("🗂️ Tipo de Gasto:", lista_cat_filtro, key="f_busqueda_cat")

        f_inicio_str = f_inicio.strftime("%Y-%m-%d")
        f_fin_str = f_fin.strftime("%Y-%m-%d")
        
        # En Postgres usamos el comodín ILIKE para evitar sensibilidad a mayúsculas
        sql_placa = "%" if v_filtro == "Todos los vehículos" else v_filtro
        sql_categoria = "%" if c_filtro == "Todas las categorías" else c_filtro

        df_resultados = pd.DataFrame()
        try:
            with obtener_conexion_db() as conexion:
                with conexion.cursor() as cursor:
                    sql_query = """
                        SELECT 
                            id_gasto AS "ID",
                            fecha AS "Fecha",
                            placa_vehiculo AS "Placa / Unidad",
                            categoria AS "Categoría",
                            monto_usd AS "Monto ($)",
                            observaciones AS "Detalle / Observación"
                        FROM gastos
                        WHERE fecha BETWEEN %s AND %s
                          AND placa_vehiculo LIKE %s
                          AND categoria LIKE %s
                        ORDER BY fecha DESC, id_gasto DESC
                    """
                    cursor.execute(sql_query, (f_inicio_str, f_fin_str, sql_placa, sql_categoria))
                    filas = cursor.fetchall()
                    if cursor.description:
                        columnas = [desc[0] for desc in cursor.description]
                        df_resultados = pd.DataFrame(filas, columns=columnas)
            
            st.markdown("---")
            
            if not df_resultados.empty:
                # Aseguramos que los montos sean numéricos
                df_resultados['Monto ($)'] = pd.to_numeric(df_resultados['Monto ($)'], errors='coerce').fillna(0.0)
                total_filtrado = float(df_resultados['Monto ($)'].sum())
                registros_conteo = len(df_resultados)
                
                meta_c1, meta_c2 = st.columns(2)
                with meta_c1:
                    st.metric(label="💰 Total Gastado en este Criterio", value=f"$ {total_filtrado:,.2f}")
                with meta_c2:
                    st.metric(label="🧾 Cantidad de Comprobantes", value=f"{registros_conteo} gastos")
                
                st.write("#### 📋 Desglose del Reporte")
                st.dataframe(df_resultados, use_container_width=True, hide_index=True)
                
                # =========================================================================
                # 🛠️ PANEL DE CORRECCIÓN DE ERRORES
                # =========================================================================
                st.markdown("---")
                st.write("### 🔧 Panel de Corrección de Errores / Modificaciones")
                
                # Convertimos los IDs a enteros limpios para evitar quejas de Pylance
                lista_ids_visibles = [int(x) for x in df_resultados['ID'].dropna().tolist()]
                
                col_mod1, col_mod2 = st.columns([1, 2])
                
                with col_mod1:
                    id_a_modificar = st.selectbox("🔍 Selecciona el ID del gasto a corregir o eliminar:", options=lista_ids_visibles)
                
                # Convertimos de forma segura a entero
                id_seguro = int(id_a_modificar) if id_a_modificar is not None else 0
                
                # Extraemos los datos actuales para pre-llenar de forma segura
                gasto_actual = df_resultados[df_resultados['ID'] == id_seguro].iloc[0]
                
                with col_mod2:
                    st.write("<br>", unsafe_allow_html=True)  # Espaciador visual
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        activar_edicion = st.button("✏️ Editar Gasto Seleccionado", use_container_width=True)
                    with btn_col2:
                        activar_borrado = st.button("🗑️ Eliminar Gasto por Completo", use_container_width=True, type="secondary")
                
                # --- CASO A: ELIMINAR ---
                if activar_borrado:
                    try:
                        with obtener_conexion_db() as conexion:
                            with conexion.cursor() as cursor:
                                cursor.execute("DELETE FROM gastos WHERE id_gasto = %s", (id_seguro,))
                                conexion.commit()
                        st.toast(f"🗑️ El gasto con ID {id_seguro} fue eliminado permanentemente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar: {e}")

                # --- CASO B: FORMULARIO FLOTANTE DE EDICIÓN ---
                if activar_edicion or st.session_state.get("editando_gasto_id") == id_seguro:
                    st.session_state["editando_gasto_id"] = id_seguro
                    
                    st.markdown(f"#### 📝 Editando el Registro ID: `{id_seguro}`")
                    
                    # Convertimos la fecha de la BD (que en Postgres puede venir como objeto date directamente)
                    fecha_val = gasto_actual['Fecha']
                    if isinstance(fecha_val, str):
                        fecha_bd_obj = datetime.strptime(fecha_val, "%Y-%m-%d").date()
                    else:
                        fecha_bd_obj = fecha_val  # Ya es un objeto date/datetime de Python
                    
                    with st.form("form_edicion_gasto"):
                        col_e1, col_e2, col_e3 = st.columns(3)
                        with col_e1:
                            nueva_fecha = st.date_input("🗓️ Corregir Fecha:", fecha_bd_obj)
                        with col_e2:
                            placa_defecto = "General (No aplica a vehículo)" if gasto_actual['Placa / Unidad'] == "General" else gasto_actual['Placa / Unidad']
                            idx_placa = lista_placas_registro.index(str(placa_defecto)) if str(placa_defecto) in lista_placas_registro else 0
                            nueva_placa = st.selectbox("🚛 Corregir Vehículo:", options=lista_placas_registro, index=idx_placa)
                        with col_e3:
                            idx_cat = categorias_gastos.index(str(gasto_actual['Categoría'])) if str(gasto_actual['Categoría']) in categorias_gastos else 0
                            nueva_cat = st.selectbox("🗂️ Corregir Categoría:", options=categorias_gastos, index=idx_cat)
                        
                        col_e4, col_e5 = st.columns([1, 2])
                        with col_e4:
                            monto_inicial_edit = float(gasto_actual['Monto ($)']) if pd.notnull(gasto_actual['Monto ($)']) else 0.01
                            nuevo_monto = st.number_input("💰 Corregir Monto ($ USD):", min_value=0.01, step=0.50, format="%.2f", value=monto_inicial_edit)
                        with col_e5:
                            detalle_inicial = str(gasto_actual['Detalle / Observación']) if pd.notnull(gasto_actual['Detalle / Observación']) else ""
                            nuevas_obs = st.text_area("📝 Corregir Detalles:", value=detalle_inicial)
                        
                        btn_actualizar = st.form_submit_button("💾 Guardar Cambios Quirúrgicos", type="primary", use_container_width=True)
                        
                        if btn_actualizar:
                            try:
                                n_fecha_str = nueva_fecha.strftime("%Y-%m-%d")
                                n_placa_str = "General" if nueva_placa == "General (No aplica a vehículo)" else str(nueva_placa)
                                
                                with obtener_conexion_db() as conexion:
                                    with conexion.cursor() as cursor:
                                        sql_update = """
                                            UPDATE gastos 
                                            SET fecha = %s, categoria = %s, monto_usd = %s, observaciones = %s, placa_vehiculo = %s
                                            WHERE id_gasto = %s
                                        """
                                        cursor.execute(sql_update, (n_fecha_str, nueva_cat, float(nuevo_monto), nuevas_obs.strip(), n_placa_str, id_seguro))
                                        conexion.commit()
                                
                                if "editando_gasto_id" in st.session_state:
                                    del st.session_state["editando_gasto_id"]
                                    
                                st.toast("✅ ¡Registro corregido con éxito!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar en PostgreSQL: {e}")
            else:
                st.info("💡 No se encontraron gastos con esos criterios en las fechas seleccionadas.")
                
        except Exception as e:
            st.error(f"Error al procesar la consulta: {e}")