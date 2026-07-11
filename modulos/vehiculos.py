import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

def mostrar_modulo_vehiculos():
    st.subheader("🚚 Control de Flota y Vehículos")
    st.markdown("---")
    
    tab_registro, tab_inventario = st.tabs([
        "📝 Registrar Vehículo", 
        "📋 Inventario de Flota"
    ])
    
    # Cargar conductores disponibles desde su propio módulo para los selectbox
    # Cargar conductores disponibles cruzando con usuarios para obtener el nombre
    try:
        conn = sqlite3.connect('exprex.db')
        query_choferes = """
            SELECT c.cedula, u.nombre, c.disponible 
            FROM conductores c
            JOIN usuarios u ON c.cedula = u.cedula
            ORDER BY u.nombre
        """
        df_choferes = pd.read_sql_query(query_choferes, conn)
        conn.close()
    except:
        df_choferes = pd.DataFrame(columns=['cedula', 'nombre', 'disponible'])


#    try:
#        conn = sqlite3.connect('exprex.db')
#        df_choferes = pd.read_sql_query("SELECT cedula, nombre, disponible FROM conductores ORDER BY nombre", conn)
#        conn.close()
#    except:
#        df_choferes = pd.DataFrame(columns=['cedula', 'nombre', 'disponible'])
    
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
                    conexion = sqlite3.connect('exprex.db')
                    cursor = conexion.cursor()
                    cursor.execute("""
                        INSERT INTO vehiculos (
                            placa, marca, modelo, anio, kilometraje_actual, serial_motor, serial_carroceria, 
                            capacidad_peso_kg, capacidad_volumen_m3, propietario_tipo, propietario_cedula, 
                            propietario_nombre, estatus
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Operativo')
                    """, (placa, marca, modelo, anio, kilometraje, serial_motor, serial_carroceria, 
                          cap_peso, cap_vol, prop_tipo_ini, prop_ced_ini, prop_nom_ini))
                    conexion.commit()
                    conexion.close()
                    st.success(f"🎉 Vehículo con placa [{placa}] registrado con éxito.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("⚠️ Error: Ya existe un vehículo registrado con esa placa.")
                except Exception as e:
                    st.error(f"❌ Error al guardar en base de datos: {e}")

        with col_der:
            st.write("##### ✏️ Gestión de Guardia y Documentación")
            
            try:
                conn = sqlite3.connect('exprex.db')
                df_placas = pd.read_sql_query("SELECT placa, marca || ' ' || modelo AS info FROM vehiculos ORDER BY placa", conn)
                conn.close()
            except:
                df_placas = pd.DataFrame()
                
            if df_placas.empty:
                st.info("Registre un vehículo a la izquierda para poder gestionar su estatus y propietarios.")
            else:
                placa_seleccionada = st.selectbox(
                    "Seleccione la Placa a Gestionar:",
                    options=df_placas['placa'].tolist(),
                    format_func=lambda x: f"🚗 {x} - {df_placas[df_placas['placa'] == x]['info'].values[0]}"
                )
                
                conn = sqlite3.connect('exprex.db')
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT propietario_nombre, propietario_cedula, estatus, chofer_asignado, 
                           vencimiento_rcv, vencimiento_trimestres, kilometraje_actual, propietario_tipo
                    FROM vehiculos WHERE placa = ?
                """, (placa_seleccionada,))
                datos_estatus = cursor.fetchone()
                conn.close()
                
                if datos_estatus:
                    with st.form("form_estatus_vehiculo"):
                        st.markdown(f"**Origen actual:** {datos_estatus[7]}")
                        prop = st.text_input("Nombre del Propietario / Empresa", value=datos_estatus[0] if datos_estatus[0] else "").strip()
                        ced_prop = st.text_input("Cédula o RIF del Propietario", value=datos_estatus[1] if datos_estatus[1] else "").strip()
                        km_actualizar = st.number_input("Actualizar Kilometraje Actual (Km)", value=float(datos_estatus[6]), step=100.0)
                        
                        st.markdown("---")
                        st.markdown("**🗓️ Vencimiento de Documentación:**")
                        
                        # Conversión segura de fechas guardadas como texto
                        f_rcv_inc = datetime.strptime(datos_estatus[4], "%Y-%m-%d").date() if datos_estatus[4] else datetime.today().date()
                        f_trim_inc = datetime.strptime(datos_estatus[5], "%Y-%m-%d").date() if datos_estatus[5] else datetime.today().date()
                        
                        venc_rcv = st.date_input("Vencimiento Seguro rcv", value=f_rcv_inc)
                        venc_trim = st.date_input("Vencimiento Trimestres", value=f_trim_inc)
                        
                        st.markdown("---")
                        c_disp1, c_disp2 = st.columns(2)
                        with c_disp1:
                            v_estatus = st.selectbox("Estatus de la Unidad:", ["Operativo", "En Taller", "Inactivo"], 
                                                     index=["Operativo", "En Taller", "Inactivo"].index(datos_estatus[2]) if datos_estatus[2] in ["Operativo", "En Taller", "Inactivo"] else 0)
                        with c_disp2:
                            if df_choferes.empty:
                                chofer_seleccionado = st.selectbox("Asignar Conductor (Cédula):", ["No hay choferes"], disabled=True)
                                cedula_a_guardar = None
                            else:
                                opciones_chofer = [None] + df_choferes['cedula'].tolist()
                                def formatear_chofer(ced):
                                    if ced is None: return "Ninguno (Sin asignar)"
                                    nombre = df_choferes[df_choferes['cedula'] == ced]['nombre'].values[0]
                                    disp = df_choferes[df_choferes['cedula'] == ced]['disponible'].values[0]
                                    return f"{ced} - {nombre} ({disp})"
                                
                                idx_actual = opciones_chofer.index(datos_estatus[3]) if datos_estatus[3] in opciones_chofer else 0
                                cedula_a_guardar = st.selectbox("Asignar Conductor:", options=opciones_chofer, index=idx_actual, format_func=formatear_chofer)
                        
                        submit_estatus = st.form_submit_button("💾 Actualizar Ficha de la Unidad", use_container_width=True)
                        
                    if submit_estatus:
                        try:
                            conexion = sqlite3.connect('exprex.db')
                            cursor = conexion.cursor()
                            cursor.execute("""
                                UPDATE vehiculos 
                                SET propietario_nombre = ?, propietario_cedula = ?, estatus = ?, 
                                    chofer_asignado = ?, vencimiento_rcv = ?, vencimiento_trimestres = ?, 
                                    kilometraje_actual = ?
                                WHERE placa = ?
                            """, (prop, ced_prop, v_estatus, cedula_a_guardar, str(venc_rcv), str(venc_trim), km_actualizar, placa_seleccionada))
                            conexion.commit()
                            conexion.close()
                            st.success(f"🔄 Unidad {placa_seleccionada} actualizada de forma impecable.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar la ficha: {e}")

    # =========================================================================
    # PESTAÑA 2: INVENTARIO DE FLOTA (CON TRIPLE CONDICIÓN EN TIEMPO REAL)
    # =========================================================================
    with tab_inventario:
        st.write("#### 📋 Directorio Consolidado de Unidades")
        try:
            conexion = sqlite3.connect('exprex.db')
            sql_vehiculos = """
                SELECT 
                    v.placa AS 'Placa',
                    v.marca AS 'Marca',
                    v.modelo AS 'Modelo',
                    v.anio AS 'Año',
                    v.kilometraje_actual AS 'Kilometraje (Km)',
                    v.estatus AS 'Estatus',
                    COALESCE(u.nombre, 'Sin Asignar') AS 'Chofer de Guardia', -- ✨ ¡Ahora viene desde la tabla usuarios!
                    COALESCE(v.chofer_asignado, 'N/P') AS 'Cédula Chofer',
                    v.propietario_nombre AS 'Propietario',
                    v.propietario_cedula AS 'Cédula/RIF Prop.',
                    v.capacidad_peso_kg AS 'Cap. Peso (Kg)',
                    v.capacidad_volumen_m3 AS 'Cap. Vol (m³)',
                    v.vencimiento_rcv AS 'Venc. RCV',
                    v.vencimiento_trimestres AS 'Venc. Trimestres',
                    v.serial_motor AS 'Serial Motor',
                    v.serial_carroceria AS 'Serial Carrocería'
                FROM vehiculos v
                LEFT JOIN conductores c ON v.chofer_asignado = c.cedula
                LEFT JOIN usuarios u ON c.cedula = u.cedula -- ✨ El puente mágico para hallar el nombre
                ORDER BY v.estatus ASC, v.placa ASC
            """
            df_v = pd.read_sql_query(sql_vehiculos, conexion)
            conexion.close()
            
            if not df_v.empty:
                st.dataframe(df_v, use_container_width=True, hide_index=True)
            else:
                st.info("💡 No hay vehículos registrados en la flota todavía.")
        except Exception as e:
            st.error(f"Error al renderizar la tabla consolidada: {e}")