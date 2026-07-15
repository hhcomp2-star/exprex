import streamlit as st
import pandas as pd
import time
from datetime import datetime

# Importamos la conexión centralizada desde tus utilidades
from modulos.utils import obtener_conexion_db

def mostrar_modulo_vehiculos():
    st.subheader("🚚 Control de Flota y Vehículos")
    st.markdown("---")
    
    tab_registro, tab_inventario = st.tabs([
        "📝 Registrar Vehículo", 
        "📋 Inventario de Flota"
    ])
    
    # Cargar conductores disponibles cruzando con usuarios para obtener el nombre
    df_choferes = pd.DataFrame(columns=['cedula', 'nombre', 'disponible'])
    try:
        with obtener_conexion_db() as conn:
            with conn.cursor() as cursor:
                query_choferes = """
                    SELECT c.cedula, u.nombre, c.disponible 
                    FROM conductores c
                    JOIN usuarios u ON c.cedula = u.cedula
                    ORDER BY u.nombre
                """
                cursor.execute(query_choferes)
                filas = cursor.fetchall()
                if cursor.description:
                    columnas = [desc[0] for desc in cursor.description]
                    df_choferes = pd.DataFrame(filas, columns=columnas)
    except Exception as e:
        st.error(f"Error al cargar conductores: {e}")

    # =========================================================================
    # PESTAÑA 1: REGISTRAR / MODIFICAR VEHÍCULO
    # =========================================================================
    with tab_registro:
        col_izq, col_der = st.columns(2)
        
        with col_izq:
            st.write("#### ➕ Registrar Nueva Unidad")
            with st.form("form_nuevo_vehiculo", clear_on_submit=True):
                placa = st.text_input("Placa / Matrícula (Única)").strip().upper()
                marca = st.text_input("Marca (Ej: Chevrolet, Renault)").strip()
                modelo = st.text_input("Modelo (Ej: Cheyenne, Mégane)").strip()
                anio = st.number_input("Año del Vehículo", min_value=1980, max_value=2027, value=2010, step=1)
                kilometraje = st.number_input("Kilometraje Inicial (Km)", min_value=0.0, step=500.0)
                
                st.markdown("**📦 Capacidades de Carga (Materiales Livianos):**")
                cap_peso = st.number_input("Capacidad de Peso (Kg)", min_value=0.0, step=100.0)
                cap_vol = st.number_input("Capacidad de Volumen (m³)", min_value=0.0, step=1.0)
                
                st.markdown("**🔍 Seriales de Ley:**")
                serial_motor = st.text_input("Serial del Motor").strip().upper()
                serial_carroceria = st.text_input("Serial de Carrocería").strip().upper()
                
                st.markdown("---")
                st.markdown("**🪪 Datos de Propiedad Inicial:**")
                prop_tipo_ini = st.selectbox("Origen de la Unidad", ["Propio", "Aliado / Tercero"])
                prop_nom_ini = st.text_input("Nombre del Propietario (Si es Aliado)").strip()
                prop_ced_ini = st.text_input("Cédula o RIF del Propietario (Si es Aliado)").strip()
                
                submit_v = st.form_submit_button("Guardar Vehículo en Flota", use_container_width=True)
                
            if submit_v and placa and marca and modelo:
                # Valores por defecto si es propio de ExpreX
                if prop_tipo_ini == "Propio":
                    prop_nom_ini = "ExpreX Freight"
                    prop_ced_ini = "G-200000000"
                
                try:
                    with obtener_conexion_db() as conexion:
                        with conexion.cursor() as cursor:
                            cursor.execute("""
                                INSERT INTO vehiculos (
                                    placa, marca, modelo, anio, kilometraje_actual, serial_motor, serial_carroceria, 
                                    capacidad_peso_kg, capacidad_volumen_m3, propietario_tipo, propietario_cedula, 
                                    propietario_nombre, estatus
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Operativo')
                            """, (placa, marca, modelo, int(anio), float(kilometraje), serial_motor, serial_carroceria, 
                                  float(cap_peso), float(cap_vol), prop_tipo_ini, prop_ced_ini, prop_nom_ini))
                            conexion.commit()
                            
                    st.success(f"🎉 Vehículo con placa [{placa}] registrado con éxito.")
                    time.sleep(1.2)
                    st.rerun()
                except Exception as e:
                    err_msg = str(e).lower()
                    if "unique" in err_msg or "duplicate key" in err_msg:
                        st.error("⚠️ Error: Ya existe un vehículo registrado con esa placa.")
                    else:
                        st.error(f"❌ Error al guardar en base de datos: {e}")

        with col_der:
            st.write("##### ✏️ Gestión de Guardia y Documentación")
            
            df_placas = pd.DataFrame(columns=['placa', 'info'])
            try:
                with obtener_conexion_db() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT placa, marca || ' ' || modelo AS info FROM vehiculos ORDER BY placa")
                        filas = cursor.fetchall()
                        if cursor.description:
                            columnas = [desc[0] for desc in cursor.description]
                            df_placas = pd.DataFrame(filas, columns=columnas)
            except Exception as e:
                st.error(f"Error al cargar las placas: {e}")
                
            if df_placas.empty:
                st.info("Registre un vehículo a la izquierda para poder gestionar su estatus y propietarios.")
            else:
                placa_seleccionada = st.selectbox(
                    "Seleccione la Placa a Gestionar:",
                    options=df_placas['placa'].tolist(),
                    format_func=lambda x: f"🚗 {x} - {df_placas[df_placas['placa'] == x]['info'].values[0]}"
                )
                
                datos_estatus = None
                try:
                    with obtener_conexion_db() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                SELECT propietario_nombre, propietario_cedula, estatus, chofer_asignado, 
                                       vencimiento_rcv, vencimiento_trimestres, kilometraje_actual, propietario_tipo
                                FROM vehiculos WHERE placa = %s
                            """, (placa_seleccionada,))
                            datos_estatus = cursor.fetchone()
                except Exception as e:
                    st.error(f"Error al consultar el estatus de la unidad: {e}")
                
                if datos_estatus:
                    with st.form("form_estatus_vehiculo"):
                        st.markdown(f"**Origen actual:** {datos_estatus[7]}")
                        
                        # Campos de texto seguros ante posibles nulos de la base de datos
                        prop_actual = str(datos_estatus[0]) if datos_estatus[0] is not None else ""
                        ced_prop_actual = str(datos_estatus[1]) if datos_estatus[1] is not None else ""
                        
                        prop = st.text_input("Nombre del Propietario / Empresa", value=prop_actual).strip()
                        ced_prop = st.text_input("Cédula o RIF del Propietario", value=ced_prop_actual).strip()
                        
                        km_inicial = float(datos_estatus[6]) if datos_estatus[6] is not None else 0.0
                        km_actualizar = st.number_input("Actualizar Kilometraje Actual (Km)", value=km_inicial, step=100.0)
                        
                        st.markdown("---")
                        st.markdown("**🗓️ Vencimiento de Documentación:**")
                        
                        # Conversión e interpretación robusta de fechas en Postgres
                        val_rcv = datos_estatus[4]
                        val_trim = datos_estatus[5]
                        
                        if isinstance(val_rcv, str):
                            f_rcv_inc = datetime.strptime(val_rcv, "%Y-%m-%d").date()
                        elif val_rcv is not None:
                            f_rcv_inc = val_rcv
                        else:
                            f_rcv_inc = datetime.today().date()

                        if isinstance(val_trim, str):
                            f_trim_inc = datetime.strptime(val_trim, "%Y-%m-%d").date()
                        elif val_trim is not None:
                            f_trim_inc = val_trim
                        else:
                            f_trim_inc = datetime.today().date()
                        
                        venc_rcv = st.date_input("Vencimiento Seguro RCV", value=f_rcv_inc)
                        venc_trim = st.date_input("Vencimiento Trimestres", value=f_trim_inc)
                        
                        st.markdown("---")
                        c_disp1, c_disp2 = st.columns(2)
                        with c_disp1:
                            estatus_actual = str(datos_estatus[2]) if datos_estatus[2] is not None else "Operativo"
                            opciones_estatus = ["Operativo", "En Taller", "Inactivo"]
                            idx_estatus = opciones_estatus.index(estatus_actual) if estatus_actual in opciones_estatus else 0
                            
                            v_estatus = st.selectbox("Estatus de la Unidad:", opciones_estatus, index=idx_estatus)
                        with c_disp2:
                            if df_choferes.empty:
                                st.selectbox("Asignar Conductor (Cédula):", ["No hay choferes"], disabled=True)
                                cedula_a_guardar = None
                            else:
                                opciones_chofer = [None] + df_choferes['cedula'].tolist()
                                
                                def formatear_chofer(ced):
                                    if ced is None: 
                                        return "Ninguno (Sin asignar)"
                                    filas_filtradas = df_choferes[df_choferes['cedula'] == ced]
                                    if not filas_filtradas.empty:
                                        nombre = str(filas_filtradas['nombre'].values[0])
                                        disp = str(filas_filtradas['disponible'].values[0])
                                        return f"{ced} - {nombre} ({disp})"
                                    return f"{ced} (Conductor)"
                                
                                chofer_actual = datos_estatus[3] if datos_estatus[3] is not None else None
                                idx_actual = opciones_chofer.index(chofer_actual) if chofer_actual in opciones_chofer else 0
                                cedula_a_guardar = st.selectbox("Asignar Conductor:", options=opciones_chofer, index=idx_actual, format_func=formatear_chofer)
                        
                        submit_estatus = st.form_submit_button("💾 Actualizar Ficha de la Unidad", use_container_width=True)
                        
                    if submit_estatus:
                        try:
                            with obtener_conexion_db() as conexion:
                                with conexion.cursor() as cursor:
                                    cursor.execute("""
                                        UPDATE vehiculos 
                                        SET propietario_nombre = %s, propietario_cedula = %s, estatus = %s, 
                                            chofer_asignado = %s, vencimiento_rcv = %s, vencimiento_trimestres = %s, 
                                            kilometraje_actual = %s
                                        WHERE placa = %s
                                    """, (prop, ced_prop, v_estatus, cedula_a_guardar, venc_rcv, venc_trim, float(km_actualizar), placa_seleccionada))
                                    conexion.commit()
                                    
                            st.success(f"🔄 Unidad {placa_seleccionada} actualizada de forma impecable.")
                            time.sleep(1.2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar la ficha: {e}")

    # =========================================================================
    # PESTAÑA 2: INVENTARIO DE FLOTA
    # =========================================================================
    with tab_inventario:
        st.write("#### 📋 Directorio Consolidado de Unidades")
        
        df_v = pd.DataFrame()
        try:
            sql_vehiculos = """
                SELECT 
                    v.placa AS "Placa",
                    v.marca AS "Marca",
                    v.modelo AS "Modelo",
                    v.anio AS "Año",
                    v.kilometraje_actual AS "Kilometraje (Km)",
                    v.estatus AS "Estatus",
                    COALESCE(u.nombre, 'Sin Asignar') AS "Chofer de Guardia",
                    COALESCE(v.chofer_asignado, 'N/P') AS "Cédula Chofer",
                    v.propietario_nombre AS "Propietario",
                    v.propietario_cedula AS "Cédula/RIF Prop.",
                    v.capacidad_peso_kg AS "Cap. Peso (Kg)",
                    v.capacidad_volumen_m3 AS "Cap. Vol (m³)",
                    v.vencimiento_rcv AS "Venc. RCV",
                    v.vencimiento_trimestres AS "Venc. Trimestres",
                    v.serial_motor AS "Serial Motor",
                    v.serial_carroceria AS "Serial Carrocería"
                FROM vehiculos v
                LEFT JOIN conductores c ON v.chofer_asignado = c.cedula
                LEFT JOIN usuarios u ON c.cedula = u.cedula
                ORDER BY v.estatus ASC, v.placa ASC
            """
            with obtener_conexion_db() as conexion:
                with conexion.cursor() as cursor:
                    cursor.execute(sql_vehiculos)
                    filas = cursor.fetchall()
                    if cursor.description:
                        columnas = [desc[0] for desc in cursor.description]
                        df_v = pd.DataFrame(filas, columns=columnas)
            
            if not df_v.empty:
                st.dataframe(df_v, use_container_width=True, hide_index=True)
            else:
                st.info("💡 No hay vehículos registrados en la flota todavía.")
        except Exception as e:
            st.error(f"Error al renderizar la tabla consolidada: {e}")