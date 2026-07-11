import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

def mostrar_modulo_gastos():
    st.subheader("💸 Control y Gestión de Gastos Operativos")
    st.markdown("---")
    
    # =========================================================================
    # 🗃️ CARGAR LISTAS DE CONTROL DESDE LA BD
    # =========================================================================
    lista_placas_registro = ["General (No aplica a vehículo)"]
    lista_placas_filtro = ["Todos los vehículos", "General"]
    
    try:
        conexion = sqlite3.connect('exprex.db')
        df_placas_bd = pd.read_sql_query("SELECT placa FROM vehiculos ORDER BY placa ASC", conexion)
        conexion.close()
        if not df_placas_bd.empty:
            placas_lista = df_placas_bd['placa'].tolist()
            lista_placas_registro.extend(placas_lista)
            lista_placas_filtro.extend(placas_lista)
    except:
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
                            conexion = sqlite3.connect('exprex.db')
                            cursor = conexion.cursor()
                            fecha_str = fecha_gasto.strftime("%Y-%m-%d")
                            placa_a_guardar = "General" if vehiculo_sel == "General (No aplica a vehículo)" else vehiculo_sel
                            
                            sql_insert = """
                                INSERT INTO gastos (fecha, categoria, monto_usd, observaciones, placa_vehiculo)
                                VALUES (?, ?, ?, ?, ?)
                            """
                            cursor.execute(sql_insert, (fecha_str, categoria_sel, monto_usd, observaciones.strip(), placa_a_guardar))
                            conexion.commit()
                            conexion.close()
                            
                            st.session_state["msg_exito"] = f"✅ Gasto asentado: {categoria_sel} (${monto_usd:,.2f})"
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

            if "msg_exito" in st.session_state:
                st.success(st.session_state["msg_exito"])
                del st.session_state["msg_exito"]

        with col_vista_rapida:
            st.subheader("📋 Últimos 15 Asientos")
            try:
                conexion = sqlite3.connect('exprex.db')
                df_ultimos = pd.read_sql_query("SELECT fecha AS 'Fecha', placa_vehiculo AS 'Placa', categoria AS 'Categoría', monto_usd AS 'Monto ($)' FROM gastos ORDER BY fecha DESC, id_gasto DESC LIMIT 15", conexion)
                conexion.close()
                if not df_ultimos.empty:
                    st.dataframe(df_ultimos, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay gastos recientes.")
            except:
                pass

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
        sql_placa = "%" if v_filtro == "Todos los vehículos" else v_filtro
        sql_categoria = "%" if c_filtro == "Todas las categorías" else c_filtro

        try:
            conexion = sqlite3.connect('exprex.db')
            sql_query = """
                SELECT 
                    id_gasto AS 'ID',
                    fecha AS 'Fecha',
                    placa_vehiculo AS 'Placa / Unidad',
                    categoria AS 'Categoría',
                    monto_usd AS 'Monto ($)',
                    observaciones AS 'Detalle / Observación'
                FROM gastos
                WHERE fecha BETWEEN ? AND ?
                  AND placa_vehiculo LIKE ?
                  AND categoria LIKE ?
                ORDER BY fecha DESC, id_gasto DESC
            """
            df_resultados = pd.read_sql_query(sql_query, conexion, params=(f_inicio_str, f_fin_str, sql_placa, sql_categoria))
            conexion.close()
            
            st.markdown("---")
            
            if not df_resultados.empty:
                total_filtrado = df_resultados['Monto ($)'].sum()
                registros_conteo = len(df_resultados)
                
                meta_c1, meta_c2 = st.columns(2)
                with meta_c1:
                    st.metric(label="💰 Total Gastado en este Criterio", value=f"$ {total_filtrado:,.2f}")
                with meta_c2:
                    st.metric(label="🧾 Cantidad de Comprobantes", value=f"{registros_conteo} gastos")
                
                st.write("#### 📋 Desglose del Reporte")
                # Mostramos la tabla. Nota que incluimos el 'ID' para que sepas qué número de registro vas a modificar
                st.dataframe(df_resultados, use_container_width=True, hide_index=True)
                
                # =========================================================================
                # 🛠️ PANEL DE CORRECCIÓN DE ERRORES (NUEVO)
                # =========================================================================
                st.markdown("---")
                st.write("### 🔧 Panel de Corrección de Erreglos / Modificaciones")
                
                # Creamos una lista de IDs válidos basados en lo que el usuario está viendo en su filtro
                lista_ids_visibles = df_resultados['ID'].tolist()
                
                col_mod1, col_mod2 = st.columns([1, 2])
                
                with col_mod1:
                    id_a_modificar = st.selectbox("🔍 Selecciona el ID del gasto a corregir o eliminar:", options=lista_ids_visibles)
                
                # Extraemos los datos actuales de ese ID para pre-llenar los campos de edición
                gasto_actual = df_resultados[df_resultados['ID'] == id_a_modificar].iloc[0]
                
                with col_mod2:
                    # Ponemos dos botones en paralelo bajo el selector de ID
                    st.write("<br>", unsafe_allow_html=True) # Espaciador visual
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        activar_edicion = st.button("✏️ Editar Gasto Seleccionado", use_container_width=True)
                    with btn_col2:
                        activar_borrado = st.button("🗑️ Eliminar Gasto por Completo", use_container_width=True, type="secondary")
                
                # --- CASO A: ELIMINAR ---
                if activar_borrado:
                    try:
                        conexion = sqlite3.connect('exprex.db')
                        cursor = conexion.cursor()
                        cursor.execute("DELETE FROM gastos WHERE id_gasto = ?", (int(id_a_modificar),))
                        conexion.commit()
                        conexion.close()
                        st.toast(f"🗑️ El gasto con ID {id_a_modificar} fue eliminado permanentemente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar: {e}")

                # --- CASO B: FORMULARIO FLOTANTE DE EDICIÓN ---
                # Si pulsa editar, abrimos un pequeño formulario dedicado abajo
                if activar_edicion or st.session_state.get("editando_gasto_id") == id_a_modificar:
                    st.session_state["editando_gasto_id"] = id_a_modificar
                    
                    st.markdown(f"#### 📝 Editando el Registro ID: `{id_a_modificar}`")
                    
                    # Convertimos la fecha de la BD a objeto date de Python
                    fecha_bd_obj = datetime.strptime(gasto_actual['Fecha'], "%Y-%m-%d").date()
                    
                    with st.form("form_edicion_gasto"):
                        col_e1, col_e2, col_e3 = st.columns(3)
                        with col_e1:
                            nueva_fecha = st.date_input("🗓️ Corregir Fecha:", fecha_bd_obj)
                        with col_e2:
                            # Pre-seleccionamos el valor viejo buscando su índice
                            placa_defecto = "General (No aplica a vehículo)" if gasto_actual['Placa / Unidad'] == "General" else gasto_actual['Placa / Unidad']
                            idx_placa = lista_placas_registro.index(placa_defecto) if placa_defecto in lista_placas_registro else 0
                            nueva_placa = st.selectbox("🚛 Corregir Vehículo:", options=lista_placas_registro, index=idx_placa)
                        with col_e3:
                            idx_cat = categorias_gastos.index(gasto_actual['Categoría']) if gasto_actual['Categoría'] in categorias_gastos else 0
                            nueva_cat = st.selectbox("🗂️ Corregir Categoría:", options=categorias_gastos, index=idx_cat)
                        
                        col_e4, col_e5 = st.columns([1, 2])
                        with col_e4:
                            nuevo_monto = st.number_input("💰 Corregir Monto ($ USD):", min_value=0.01, step=0.50, format="%.2f", value=float(gasto_actual['Monto ($)']))
                        with col_e5:
                            nuevas_obs = st.text_area("📝 Corregir Detalles:", value=gasto_actual['Detalle / Observación'])
                        
                        btn_actualizar = st.form_submit_button("💾 Guardar Cambios Quirúrgicos", type="primary", use_container_width=True)
                        
                        if btn_actualizar:
                            try:
                                conexion = sqlite3.connect('exprex.db')
                                cursor = conexion.cursor()
                                n_fecha_str = nueva_fecha.strftime("%Y-%m-%d")
                                n_placa_str = "General" if nueva_placa == "General (No aplica a vehículo)" else nueva_placa
                                
                                sql_update = """
                                    UPDATE gastos 
                                    SET fecha = ?, categoria = ?, monto_usd = ?, observaciones = ?, placa_vehiculo = ?
                                    WHERE id_gasto = ?
                                """
                                cursor.execute(sql_update, (n_fecha_str, nueva_cat, nuevo_monto, nuevas_obs.strip(), n_placa_str, int(id_a_modificar)))
                                conexion.commit()
                                conexion.close()
                                
                                if "editando_gasto_id" in st.session_state:
                                    del st.session_state["editando_gasto_id"]
                                    
                                st.toast("✅ ¡Registro corregido con éxito!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar: {e}")
            else:
                st.info("💡 No se encontraron gastos con esos criterios en las fechas seleccionadas.")
                
        except Exception as e:
            st.error(f"Error al procesar la consulta: {e}")