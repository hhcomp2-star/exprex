import streamlit as st
import sqlite3
import pandas as pd

def mostrar_modulo_clientes():
    st.markdown("### 🏢 Gestión Comercial de Clientes")
    st.write("Administración de datos maestros de empresas, sucursales de carga y tarifas asociadas.")
    
    personal_base_datos = "exprex.db"
    
    # 📝 CORRECCIÓN 1: Traemos las consultas al inicio del módulo para alimentar los selectores de forma segura
    try:
        conexion = sqlite3.connect(personal_base_datos)
        df_cb_clientes = pd.read_sql_query("SELECT id_cliente, razon_social FROM clientes ORDER BY razon_social", conexion)
        conexion.close()
    except Exception as e:
        st.error(f"❌ Error de conexión base de datos: {e}")
        return

    # 📝 CORRECCIÓN 2: Pestañas comerciales únicas, limpias y ordenadas
    tab_registrar_cliente, tab_sucursales, tab_directorio = st.tabs([
        "➕ Registrar Cliente", 
        "🏢 Sucursales y Sedes", 
        "📂 Directorio Comercial (CRUD)"
    ])
    
    # =========================================================================
    # PESTAÑA 1: REGISTRAR CLIENTE
    # =========================================================================
    with tab_registrar_cliente:
        st.write("### 🏢 Registrar Nueva Empresa Cliente")
        with st.form("form_nuevo_cliente", clear_on_submit=True):
            rif = st.text_input("RIF de la Empresa (Ej: J-12345678-9)").strip().upper()
            razon_social = st.text_input("Razón Social / Nombre de la Empresa").strip()
            telefono = st.text_input("Teléfono Corporativo de Contacto").strip()
            
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                email = st.text_input("Correo Electrónico de Facturación").strip()
            with col_c2:
                contrasena = st.text_input("Contraseña de Acceso", type="password")
            direccion = st.text_area("Dirección Fiscal Legal").strip()
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                limite_credito_usd = st.number_input("🛡️ Límite de Crédito (USD):", min_value=0.0, value=1000.0, step=100.0)
            with col_c2:
                dias_credito = st.number_input("📅 Días de Crédito:", min_value=0, value=15, step=1)
            submit_c = st.form_submit_button("Guardar Empresa")
            saldo_pendiente_usd = 0.0  # Inicializamos el saldo pendiente en cero al registrar un nuevo cliente
        #
        if submit_c:
            if not rif or not razon_social:
                st.error("⚠️ El RIF y la Razón Social son obligatorios.")
            else:
                try:
                    conexion = sqlite3.connect(personal_base_datos)
                    cursor = conexion.cursor()
                   
                    cursor.execute("""
                        INSERT INTO clientes (rif, razon_social, telefono_contacto, email_contacto, contrasena, direccion_fiscal, dias_credito, limite_credito_usd, saldo_pendiente_usd) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0)
                    """, (rif, razon_social, telefono, email, contrasena, direccion, dias_credito, limite_credito_usd))
                    
                    conexion.commit()
                    st.success(f"🎉 Empresa '{razon_social}' registrada exitosamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar la empresa: {e}")
                finally:
                    conexion.close()

    # =========================================================================
    # PESTAÑA 2: SUCURSALES Y SEDES
    # =========================================================================
    with tab_sucursales:
        st.write("### 📍 Registrar Sucursal / Agencia de Carga o Descarga")
        if df_cb_clientes.empty:
            st.info("💡 No hay empresas comerciales registradas todavía. Agregue una en la pestaña anterior.")
        else:
            with st.form("form_nueva_sucursal", clear_on_submit=True):
                empresa_id = st.selectbox(
                    "Seleccione la Empresa Asociada:", 
                    options=df_cb_clientes['id_cliente'].tolist(), 
                    format_func=lambda x: df_cb_clientes[df_cb_clientes['id_cliente'] == x]['razon_social'].values[0]
                )
                nombre_agencia = st.text_input("Nombre de la Agencia / Galpón (Ej: Almacén Central)").strip()
                ciudad_agencia = st.text_input("Ciudad de ubicación (Ej: Valencia)").strip()
                telefono_agencia = st.text_input("📞 Teléfono directo de la Agencia (Opcional)").strip()
                dir_agencia = st.text_area("Dirección Exacta para el Chofer").strip()
                col_1, col_2 = st.columns(2)
                with col_1:
                    longitud_agencia = st.number_input("🌐 Longitud de la Agencia", format="%.6f", value=0.0)
                with col_2:
                    latitud_agencia = st.number_input("🌐 Latitud de la Agencia", format="%.6f", value=0.0)

                submit_s = st.form_submit_button("Asignar Sucursal a Empresa")
                
            if submit_s:
                if not nombre_agencia or not ciudad_agencia:
                    st.error("⚠️ El nombre de la agencia y la ciudad son obligatorios.")
                else:
                    try:
                        conexion = sqlite3.connect(personal_base_datos)
                        cursor = conexion.cursor()
                        cursor.execute("""
                            INSERT INTO sucursales (id_cliente, nombre_agencia, ciudad, direccion, telefono_sucursal, longitud, latitud) 
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (empresa_id, nombre_agencia, ciudad_agencia, dir_agencia, telefono_agencia, longitud_agencia, latitud_agencia))
                        conexion.commit()
                        st.success(f"📍 Sucursal '{nombre_agencia}' vinculada con éxito.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar la sucursal: {e}")
                    finally:
                        conexion.close()

    # =========================================================================
    # PESTAÑA 3: DIRECTORIO Y MODIFICACIONES (CRUD)
    # =========================================================================
    with tab_directorio:
        st.write("### 📋 Directorio Consolidado (Empresas y sus Agencias)")
        try:
            conexion = sqlite3.connect(personal_base_datos)
            sql_dir = """
                SELECT 
                    c.razon_social AS 'Empresa', 
                    c.rif AS 'RIF', 
                    s.nombre_agencia AS 'Agencia/Sucursal', 
                    s.ciudad AS 'Ciudad', 
                    s.telefono_sucursal AS '📞 Teléfono Agencia',
                    s.direccion AS 'Dirección Almacén'
                FROM sucursales s
                JOIN clientes c ON s.id_cliente = c.id_cliente
                ORDER BY c.razon_social, s.nombre_agencia
            """
            df_dir = pd.read_sql_query(sql_dir, conexion)
            conexion.close()
            
            if not df_dir.empty:
                st.dataframe(df_dir, use_container_width=True, hide_index=True)
            else:
                st.info("💡 No hay agencias o sucursales vinculadas aún.")
        except Exception as e:
            st.error(f"❌ Error al listar el directorio comercial: {e}")
            
        st.markdown("---")
        st.write("### ✏️ Modificar o Corregir una Sucursal Existente")
        
        try:
            conn_mod = sqlite3.connect(personal_base_datos)
            df_suc_mod = pd.read_sql_query("""
                SELECT s.id_sucursal, c.razon_social || ' - ' || s.nombre_agencia AS info_completa 
                FROM sucursales s 
                JOIN clientes c ON s.id_cliente = c.id_cliente 
                ORDER BY c.razon_social, s.nombre_agencia
            """, conn_mod)
            conn_mod.close()
        except Exception as e:
            df_suc_mod = pd.DataFrame()

        if df_suc_mod.empty:
            st.info("Aún no hay sucursales registradas para permitir ediciones.")
        else:
            sucursal_a_editar = st.selectbox(
                "Seleccione la Sucursal que desea editar:",
                options=df_suc_mod['id_sucursal'].tolist(),
                format_func=lambda x: df_suc_mod[df_suc_mod['id_sucursal'] == x]['info_completa'].values[0],
                key="sb_editar_sucursal_comercial"
            )
            
            try:
                conn_mod = sqlite3.connect(personal_base_datos)
                cursor_mod = conn_mod.cursor()
                cursor_mod.execute("""
                    SELECT nombre_agencia, ciudad, direccion, telefono_sucursal 
                    FROM sucursales 
                    WHERE id_sucursal = ?
                """, (sucursal_a_editar,))
                datos_actuales = cursor_mod.fetchone()
                conn_mod.close()
            except Exception as e:
                datos_actuales = None
                st.error(f"Error al buscar detalles: {e}")
            
            if datos_actuales:
                with st.form("form_editar_sucursal_limpio", clear_on_submit=False):
                    col_ed1, col_ed2 = st.columns(2)
                    with col_ed1:
                        nuevo_nombre = st.text_input("Nombre de la Agencia", value=datos_actuales[0]).strip()
                        nueva_ciudad = st.text_input("Ciudad", value=datos_actuales[1]).strip()
                    with col_ed2:
                        nuevo_telefono = st.text_input("📞 Teléfono de la Agencia", value=datos_actuales[3] if datos_actuales[3] else "").strip()
                        nueva_direccion = st.text_area("Dirección Exacta", value=datos_actuales[2] if datos_actuales[2] else "").strip()
                    
                    _, col_btn_ed, _ = st.columns([1, 2, 1])
                    with col_btn_ed:
                        boton_actualizar = st.form_submit_button("💾 Guardar Cambios en la Sucursal", use_container_width=True)
                
                if boton_actualizar:
                    if not nuevo_nombre or not nueva_ciudad:
                        st.error("⚠️ El nombre y la ciudad no pueden quedar vacíos.")
                    else:
                        try:
                            conexion = sqlite3.connect(personal_base_datos)
                            cursor = conexion.cursor()
                            cursor.execute("""
                                UPDATE sucursales 
                                SET nombre_agencia = ?, ciudad = ?, direccion = ?, telefono_sucursal = ? 
                                WHERE id_sucursal = ?
                            """, (nuevo_nombre, nueva_ciudad, nueva_direccion, nuevo_telefono, sucursal_a_editar))
                            conexion.commit()
                            st.success(f"🔄 ¡Sucursal actualizada con éxito en la base de datos!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error al actualizar: {e}")
                        finally:
                            conexion.close()