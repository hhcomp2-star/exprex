import streamlit as st
import pandas as pd
from datetime import datetime
import time 

# Importamos tu función centralizada de conexión (ajusta el import si es necesario)
from modulos.utils import obtener_conexion_db  

# ====================================================
# VENTANA MODAL DE CONFIRMACIÓN (NIVEL RAÍZ)
# ====================================================
@st.dialog("⚠️ Confirmar Modificación")
def confirmar_actualizacion_modal():
    st.warning("¿Estás seguro de que deseas aplicar estos cambios en la base de datos?")
    datos = st.session_state.cambios_pendientes
    
    # Renderizado dinámico del modal según el cargo anterior/nuevo
    st.markdown(f"""
    * **Cédula:** {datos['cedula']} (Nombre: {datos['nombre']})
    * **Departamento:** {datos['departamento_actual']} ➡️ **{datos['departamento_nuevo']}**
    * **Cargo (Rol):** {datos['cargo_actual']} ➡️ **{datos['cargo_nuevo']}**
    * **Teléfono:** {datos['telefono_actual']} ➡️ **{datos['telefono_nuevo']}**
    * **Correo:** {datos['correo_actual']} ➡️ **{datos['correo_nuevo']}**
    * **Dirección:** {datos['direccion_actual']} ➡️ **{datos['direccion_nuevo']}**
    * **Banco:** {datos['banco_actual']} ➡️ **{datos['banco_nuevo']}**
    * **Cuenta:** {datos['num_cuenta_actual']} ➡️ **{datos['num_cuenta_nuevo']}**
    """)
    
    if datos['cargo_nuevo'] == 'Conductor':
        st.markdown(f"""
        * **Vehículo:** {datos['vehiculo_actual']} ➡️ **{datos['vehiculo_nuevo']}**
        * **Placa:** {datos['placa_actual']} ➡️ **{datos['placa_nuevo']}**
        * **Vehículo Propio:** {datos['propio_actual']} ➡️ **{datos['propio_nuevo']}**
        * **Vencimiento Certificado:** {datos['certificado_actual']} ➡️ **{datos['certificado_nuevo']}**
        * **Vencimiento ROTC:** {datos['rotc_actual']} ➡️ **{datos['rotc_nuevo']}**
        * **Capacidad de Carga:** {datos['capacidad_actual']} ➡️ **{datos['capacidad_nuevo']}**
        """)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancelar", use_container_width=True):
            st.session_state.cambios_pendientes = None
            st.rerun()
            
    with col2:
        if st.button("✅ Confirmar y Guardar", type="primary", use_container_width=True):
            try:
                # Usamos el manejador de contexto con tu pool/conexión de Postgres
                with obtener_conexion_db() as conexion:
                    with conexion.cursor() as cursor:
                        
                        # UPDATE 1: Tabla Usuarios (Campos maestros generales con marcador %s)
                        sql_usuarios = """
                            UPDATE usuarios 
                            SET departamento = %s, rol = %s, telefono = %s, email = %s, direccion = %s, banco = %s, numero_cuenta = %s 
                            WHERE cedula = %s
                        """
                        cursor.execute(sql_usuarios, (
                            datos['departamento_nuevo'], datos['cargo_nuevo'], 
                            datos['telefono_nuevo'], datos['correo_nuevo'], datos['direccion_nuevo'], 
                            datos['banco_nuevo'], datos['num_cuenta_nuevo'], datos['cedula']
                        ))
                        
                        # UPDATE 2: Tabla Conductores (Manejo condicional de conductor)
                        if datos['cargo_nuevo'] == 'Conductor':
                            cursor.execute("SELECT 1 FROM conductores WHERE cedula = %s", (datos['cedula'],))
                            existe = cursor.fetchone()
                            
                            if existe is not None:  # Verificación explícita para evitar quejas de Pylance
                                sql_conductores = """
                                    UPDATE conductores 
                                    SET vehiculo = %s, placa = %s, propio = %s, vence_certificado = %s, vence_rotc = %s, capacidad_carga = %s 
                                    WHERE cedula = %s
                                """
                                cursor.execute(sql_conductores, (
                                    datos['vehiculo_nuevo'], datos['placa_nuevo'], datos['propio_nuevo'],
                                    datos['certificado_nuevo'], datos['rotc_nuevo'], datos['capacidad_nuevo'], datos['cedula']
                                ))
                            else:
                                sql_insert_cond = """
                                    INSERT INTO conductores (cedula, vehiculo, placa, propio, disponible, vence_certificado, vence_rotc, capacidad_carga) 
                                    VALUES (%s, %s, %s, %s, 'Sí', %s, %s, %s)
                                """
                                cursor.execute(sql_insert_cond, (
                                    datos['cedula'], datos['vehiculo_nuevo'], datos['placa_nuevo'], datos['propio_nuevo'],
                                    datos['certificado_nuevo'], datos['rotc_nuevo'], datos['capacidad_nuevo']
                                ))
                        else:
                            # Si ya no es Conductor, lo removemos para liberar su placa en la flota operativa
                            cursor.execute("DELETE FROM conductores WHERE cedula = %s", (datos['cedula'],))
                        
                        # Al usar 'with' con psycopg2, el commit suele manejarse automáticamente al salir del bloque exitosamente,
                        # pero asegurar el commit previene problemas de aislamiento de transacciones en pools.
                        conexion.commit()
                
                if "sb_mod" in st.session_state:
                    del st.session_state["sb_mod"]
                
                st.session_state["opcion"] = "Inicio" 
                st.session_state["mensaje_exito_flotante"] = "📈 ¡Ficha de personal actualizada correctamente!"
                
            except Exception as e:
                st.error(f"❌ Error al guardar en la base de datos: {e}")
                
            st.session_state.cambios_pendientes = None
            st.rerun()

# ====================================================
# FUNCIÓN PRINCIPAL DEL MÓDULO
# ====================================================
def mostrar_modulo_nomina():

    # Listas maestros del negocio (Se unifica 'Conductor' como el término estándar)
    departamentos_lista = ["Operaciones", "Administración", "Finanzas", "Ventas y Comercial"]
    cargos_lista = ["Jefe de Departamento", "Administrador", "Conductor", "Secretaria", "Vendedor"]

    if "cambios_pendientes" not in st.session_state:
        st.session_state.cambios_pendientes = None
    if "actualizacion_exitosa" not in st.session_state:
        st.session_state.actualizacion_exitosa = False
    if "version_tabs" not in st.session_state:
        st.session_state["version_tabs"] = 0

    lista_pestanas = [
        "👥 Nómina Activa", 
        "📝 Registrar Personal", 
        "✏️ Modificar Datos",
        "🔴 Dar de Baja",
        "🗄️ Historial"
    ]
    
    tabs = st.tabs(lista_pestanas)
    
    tab_activos = tabs[0]
    tab_crear = tabs[1]
    tab_modificar = tabs[2]
    tab_eliminar = tabs[3]
    tab_historico = tabs[4]

    # ====================================================
    # PESTAÑA 1: VISUALIZAR NÓMINA ACTIVA GENERAL
    # ====================================================
    with tab_activos:
        with obtener_conexion_db() as conexion:
            # Traemos toda la nómina activa base usando sintaxis Postgres
            query = """
                SELECT u.cedula AS "Cédula", u.nombre AS "Nombre", u.departamento AS "Departamento", u.rol AS "Cargo", u.activo AS "Activo",
                       u.telefono AS "Teléfono", u.email AS "Correo", u.direccion AS "Dirección",
                       u.banco AS "Banco", u.numero_cuenta AS "Cuenta",
                       c.vehiculo AS "Vehículo", c.placa AS "Placa", c.propio AS "Vehículo Propio", c.disponible AS "Disponible",
                       c.vence_certificado AS "Venc. Certificado", c.vence_rotc AS "Venc. ROTC", c.capacidad_carga AS "Capacidad"
                FROM usuarios u
                LEFT JOIN conductores c ON u.cedula = c.cedula
                WHERE u.activo = 'Sí'
            """
            df_activos = pd.read_sql_query(query, conexion)

        if df_activos.empty:
            st.info("No hay personal activo registrado en la empresa.")
        else:
            st.write("### 👥 Nómina General Activa")
            
            # FILTROS CRUZADOS EN PARALELO
            col_f1, col_f2 = st.columns(2)
            
            with col_f1:
                opciones_filtro_dep = ["Todos los Departamentos"] + departamentos_lista
                dep_seleccionado = st.selectbox("1️⃣ Filtrar por Departamento:", opciones_filtro_dep, key="sb_filtro_departamento")
            
            with col_f2:
                opciones_filtro_cargo = ["Todos los Cargos"] + cargos_lista
                cargo_seleccionado = st.selectbox("2️⃣ Filtrar por Cargo:", opciones_filtro_cargo, key="sb_filtro_cargo")
            
            # LÓGICA DE FILTRADO EN CASCADA
            df_vista = df_activos.copy()
            
            if dep_seleccionado != "Todos los Departamentos":
                df_vista = df_vista[df_vista["Departamento"] == dep_seleccionado]
                
            if cargo_seleccionado != "Todos los Cargos":
                df_vista = df_vista[df_vista["Cargo"] == cargo_seleccionado]

            columnas_vista = ["Cédula", "Nombre", "Departamento", "Cargo", "Teléfono", "Activo"]
            
            if df_vista.empty:
                st.warning(f"⚠️ No hay coincidencias para el personal de '{dep_seleccionado}' con cargo de '{cargo_seleccionado}'.")
            else:
                st.dataframe(df_vista[columnas_vista], use_container_width=True, hide_index=True)

            # ----------------------------------------------------
            # SUB-SECCIÓN: CONSULTA INDIVIDUAL DE EXPEDIENTE
            # ----------------------------------------------------
            st.markdown("---")
            st.write("### 🔍 Consulta Individual de Expediente")
    
            opciones_busqueda = ["-- Seleccione para ver Ficha Detallada --"] + [
                f"{fila['Nombre']} ({fila['Cargo']} - C.I. {fila['Cédula']})" for _, fila in df_vista.iterrows()
            ]
            
            seleccion = st.selectbox("Buscar empleado activo:", opciones_busqueda, key="sb_consulta_expediente")
            
            if seleccion != "-- Seleccione para ver Ficha Detallada --":
                cedula_consulta = seleccion.split("- C.I. ")[1].replace(")", "")
                persona = df_activos[df_activos["Cédula"] == cedula_consulta].iloc[0]
                
                st.write("---")
                st.markdown(f"## 🪪 {persona['Nombre']}")
                st.markdown(f"**Cargo:** {persona['Cargo']} | **Área:** {persona['Departamento']} | **Estatus:** 🟢 Activo")
                st.write("---")
                
                col_personal, col_logistica = st.columns(2)
                with col_personal:
                    st.markdown("#### 📞 Datos de Contacto")
                    st.markdown(f"* **Teléfono:** {persona['Teléfono']}")
                    st.markdown(f"* **Correo:** {persona['Correo']}")
                    st.markdown("* **Dirección de Habitación:**")
                    st.info(persona['Dirección'] if persona['Dirección'] else "No registrada.")
                    st.markdown("#### Datos Financieros")
                    st.markdown(f"* **Banco:** {persona['Banco'] if persona['Banco'] else 'Por recibir información'}")
                    st.markdown(f"* **Cuenta:** {persona['Cuenta'] if persona['Cuenta'] else 'Por recibir información'}")
                    
                with col_logistica:
                    if persona['Cargo'] == 'Conductor':
                        st.markdown("#### 🚛 Datos de la Unidad Asignada")
                        st.markdown(f"* **Vehículo:** {persona['Vehículo']}")
                        st.markdown(f"* **Placa:** `{persona['Placa']}`")
                        st.markdown(f"* **Unidad Propia:** {persona['Vehículo Propio']}")
                        st.markdown(f"* **Capacidad de Carga:** {persona['Capacidad']}")
                        st.markdown(f"* **Disponibilidad:** {'🟢 Disponible' if persona['Disponible'] == 'Sí' else '🔴 En Ruta / Taller'}")
                    else:
                        st.markdown("#### 🏢 Información Interna")
                        st.info("Este empleado pertenece al personal fijo/administrativo de oficina. No tiene unidades vehiculares asignadas.")
                
                if persona['Cargo'] == 'Conductor':
                    st.write("---")
                    st.markdown("#### 🗓️ Vencimientos de Documentación Legal")
                    col_doc1, col_doc2 = st.columns(2)
                    with col_doc1: st.metric(label="Certificado Médico", value=str(persona['Venc. Certificado']))
                    with col_doc2: st.metric(label="ROTC / SSET", value=str(persona['Venc. ROTC']))
                    
                st.write("---")
                st.info("💡 **Nota:** Para cerrar esta ficha seleccione otra pestaña o vaya al menú de **Inicio**.")

    # ====================================================
    # PESTAÑA 2: REGISTRAR NUEVO PERSONAL (DINÁMICO)
    # ====================================================
    with tab_crear:
        st.write("### 📝 Registrar Nuevo Integrante de la Empresa")
        with st.form("form_registro_conductor", clear_on_submit=True):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                c_departamento = st.selectbox("Departamento / Área:", departamentos_lista)
            with col_u2:
                # Corregimos "Chofer" por "Conductor" para unificar el flujo en todo el sistema
                c_cargo = st.selectbox("Cargo (Rol en Sistema):", cargos_lista)
                
            c_cedula = st.text_input("Cédula de Identidad")
            c_nombre = st.text_input("Nombre Completo")
            c_telefono = st.text_input("Teléfono")
            c_email = st.text_input("Correo Electrónico")
            c_direccion = st.text_area("Dirección")
            c_banco = st.text_input("Nombre del Banco")
            # Se unifica 'c_num_cuenta' con 'num_cuenta' en BD para Postgres
            c_num_cuenta = st.text_input("Número de Cuenta")
            c_clave = st.text_input("Contraseña de Acceso", type="password")
            
            st.markdown("---")
            st.markdown("##### 🚛 Datos de Vehículo (Exclusivo para Conductores)")
            st.caption("Nota: Si el cargo seleccionado arriba no es 'Conductor', el sistema ignorará estos campos automáticamente.")
            
            c_vehiculo = st.text_input("Vehículo (Ej: Chevrolet Cheyenne)")
            c_placa = st.text_input("Placa de la Unidad")
            c_propio = st.selectbox("¿Vehículo propio?", ["Sí", "No"])
            c_vence_cert = st.date_input("Vencimiento Certificado Médico")
            c_vence_rotc = st.date_input("Vencimiento ROTC")
            c_capacidad = st.text_input("Capacidad de Carga")
            
            if st.form_submit_button("Guardar Registro"):
                if not c_cedula or not c_nombre or not c_clave:
                    st.error("❌ Cédula, Nombre y Contraseña son obligatorios.")
                else:
                    try:
                        with obtener_conexion_db() as conexion:
                            with conexion.cursor() as cursor:
                                # INSERT 1: Tabla Usuarios (Postgres %s)
                                cursor.execute("""
                                    INSERT INTO usuarios (cedula, nombre, departamento, rol, telefono, email, direccion, banco, numero_cuenta, contrasena, activo) 
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Sí')
                                """, (c_cedula, c_nombre, c_departamento, c_cargo, c_telefono, c_email, c_direccion, c_banco, c_num_cuenta, c_clave))
                                
                                # INSERT 2: Condicionado a si es Conductor
                                if c_cargo == "Conductor":
                                    cursor.execute("""
                                        INSERT INTO conductores (cedula, vehiculo, placa, propio, disponible, vence_certificado, vence_rotc, capacidad_carga) 
                                        VALUES (%s, %s, %s, %s, 'Sí', %s, %s, %s)
                                    """, (c_cedula, c_vehiculo, c_placa, c_propio, str(c_vence_cert), str(c_vence_rotc), c_capacidad))
                                
                                conexion.commit()
                                
                        st.success(f"¡{c_cargo} registrado exitosamente!")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error de base de datos: {e}")

    # ====================================================
    # PESTAÑA 3: MODIFICAR DATOS
    # ====================================================
    with tab_modificar:
        st.write("### ✏️ Actualizar Datos de Expediente")
        
        if df_activos.empty:
            st.info("No hay personal activo para modificar.")
        else:
            cedula_mod = st.selectbox("Seleccione la Cédula a modificar:", ["-- Seleccione --"] + df_activos["Cédula"].tolist(), key="sb_mod")
            
            if cedula_mod != "-- Seleccione --":
                st.write("---")
                
                with obtener_conexion_db() as conexion:
                    with conexion.cursor() as cursor:
                        cursor.execute("""
                            SELECT u.nombre, u.departamento, u.rol, u.telefono, u.email, u.direccion, u.banco, u.numero_cuenta,
                                   c.vehiculo, c.placa, c.propio, c.vence_certificado, c.vence_rotc, c.capacidad_carga, c.disponible
                            FROM usuarios u
                            LEFT JOIN conductores c ON u.cedula = c.cedula
                            WHERE u.cedula = %s
                        """, (cedula_mod,))
                        expediente = cursor.fetchone()
                
                if expediente is not None:
                    nom, dep, cargo_act, tel, corr, dire, banco, num_cuenta, veh, plac, prop, cert, rotc, cap, disp = expediente

                    st.markdown(f"#### ⚙️ Editando Ficha de: **{nom}**")
                    
                    # Manejo de disponibilidad operativa (unificado a 'Conductor')
                    if cargo_act == "Conductor":
                        st.write(f"Disponibilidad operativa actual: **{disp}**")
                        nuevo_estado = st.radio("Cambiar estado operativo:", ["Sí", "No"], index=0 if disp == "Sí" else 1, key="radio_disp")
                        if st.button("Actualizar Solo Disponibilidad", use_container_width=True):
                            with obtener_conexion_db() as conexion:
                                with conexion.cursor() as cursor:
                                    cursor.execute("UPDATE conductores SET disponible = %s WHERE cedula = %s", (nuevo_estado, cedula_mod))
                                    conexion.commit()
                            st.success("¡Disponibilidad modificada!")
                            st.rerun()
                        st.write("---")

                    st.markdown("##### 📝 Campos del Expediente")
                    with st.form(key="form_modificar", clear_on_submit=False):
                        
                        col_m1, col_m2 = st.columns(2)
                        with col_m1:
                            idx_dep = departamentos_lista.index(dep) if dep in departamentos_lista else 0
                            nuevo_dep = st.selectbox("Departamento:", departamentos_lista, index=idx_dep)
                        with col_m2:
                            idx_car = cargos_lista.index(cargo_act) if cargo_act in cargos_lista else 0
                            nuevo_cargo = st.selectbox("Cargo (Rol):", cargos_lista, index=idx_car)

                        nuevo_telefono = st.text_input("Teléfono:", value=tel if tel else "")
                        nuevo_correo = st.text_input("Correo Electrónico:", value=corr if corr else "")
                        nuevo_direccion = st.text_area("Dirección:", value=dire if dire else "")
                        nuevo_banco = st.text_input("Nombre del Banco:", value=banco if banco else "")
                        nuevo_num_cuenta = st.text_input("Número de Cuenta:", value=num_cuenta if num_cuenta else "")

                        st.markdown("✨ *Campos de Transporte (Solo aplican si el cargo final es 'Conductor')*")
                        nuevo_vehiculo = st.text_input("Vehículo Asignado:", value=veh if veh else "")
                        nuevo_placa = st.text_input("Placa de la Unidad:", value=plac if plac else "")
                        nuevo_propio = st.selectbox("¿Vehículo Propio?", ["Sí", "No"], index=0 if prop == "Sí" else 1)
                        nuevo_certificado = st.text_input("Vencimiento Certificado Médico (AAAA-MM-DD):", value=str(cert) if cert else "2026-01-01")
                        nuevo_rotc = st.text_input("Vencimiento ROTC (AAAA-MM-DD):", value=str(rotc) if rotc else "2026-01-01")
                        nuevo_capacidad = st.text_input("Capacidad de Carga:", value=cap if cap else "")

                        boton_actualizar = st.form_submit_button("Guardar Cambios del Expediente")

                    if boton_actualizar:
                        st.session_state.cambios_pendientes = {
                            "cedula": cedula_mod, "nombre": nom,
                            "departamento_actual": dep, "departamento_nuevo": nuevo_dep,
                            "cargo_actual": cargo_act, "cargo_nuevo": nuevo_cargo,
                            "telefono_actual": tel, "telefono_nuevo": nuevo_telefono.strip(),
                            "correo_actual": corr, "correo_nuevo": nuevo_correo.strip(),
                            "direccion_actual": dire, "direccion_nuevo": nuevo_direccion.strip(),
                            "banco_actual": banco, "banco_nuevo": nuevo_banco.strip(),
                            "num_cuenta_actual": num_cuenta, "num_cuenta_nuevo": nuevo_num_cuenta.strip(),
                            "vehiculo_actual": veh, "vehiculo_nuevo": nuevo_vehiculo.strip(),
                            "placa_actual": plac, "placa_nuevo": nuevo_placa.strip(),
                            "propio_actual": prop, "propio_nuevo": nuevo_propio,
                            "certificado_actual": cert, "certificado_nuevo": nuevo_certificado.strip(),
                            "rotc_actual": rotc, "rotc_nuevo": nuevo_rotc.strip(),
                            "capacidad_actual": cap, "capacidad_nuevo": nuevo_capacidad.strip()
                        }
                        confirmar_actualizacion_modal()
               
    # ====================================================
    # PESTAÑA 4: DAR DE BAJA
    # ====================================================
    with tab_eliminar:
        st.write("### 🔴 Tramitar Retiro de Personal")
        if df_activos.empty:
            st.info("No hay personal activo para tramitar egreso.")
        else:
            cedula_baja = st.selectbox("Seleccione la Cédula del empleado a retirar:", ["-- Seleccione una Cédula --"] + df_activos["Cédula"].tolist(), key="sb_baja")
            
            if cedula_baja != "-- Seleccione una Cédula --":
                st.write("---")
                st.warning(f"⚠️ **CONFIRMACIÓN REQUERIDA:** Está a punto de pasar al estado de 'Inactivo' al empleado con Cédula **{cedula_baja}**.")
                
                check_legal = st.checkbox("Confirmo legalmente que deseo registrar el egreso de este trabajador.", key="chk_legal")
                
                if st.button("🔥 Aplicar Baja Definitiva", type="primary", disabled=not check_legal):
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
                    with obtener_conexion_db() as conexion:
                        with conexion.cursor() as cursor:
                            cursor.execute("UPDATE usuarios SET activo = 'No', fecha_baja = %s WHERE cedula = %s", (fecha_hoy, cedula_baja))
                            conexion.commit()
                    st.success(f"💼 Personal desincorporado con éxito el {fecha_hoy}.")
                    time.sleep(1.5)
                    st.rerun()

    # ====================================================
    # PESTAÑA 5: HISTORIAL DE EX-EMPLEADOS
    # ====================================================
    with tab_historico:
        st.write("### 🗄️ Personal Egresado (Histórico)")
        with obtener_conexion_db() as conexion:
            query_hist = """
                SELECT u.cedula AS "Cédula", u.nombre AS "Nombre", u.departamento AS "Departamento", u.rol AS "Cargo ocupado", u.fecha_baja AS "Fecha de Baja", u.activo AS "Activo"
                FROM usuarios u
                WHERE u.activo = 'No'
            """
            df_hist = pd.read_sql_query(query_hist, conexion)

        if df_hist.empty:
            st.info("No hay registros de bajas en el historial.")
        else:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)