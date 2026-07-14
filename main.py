import streamlit as st
import sqlite3
import os
import time

from modulos.rec_cont import mostrar_modulo_recuperar_contrasena
from modulos.nvo_reg import mostrar_modulo_registro

# Esta DEBE ser la primera instrucción de Streamlit en el archivo
#st.set_page_config(
#    page_title="ExpreX Logística",
#    page_icon="exprex_logo_2.png",  # Aquí llamamos a tu imagen para la pestaña
#    layout="wide"          # O la configuración que ya tengas armada
#)

# Configuración de la página (Debe ser la primera línea de Streamlit)
st.set_page_config(page_title="ExpreX Logística", page_icon="exprex_logo_2.png", layout="centered")

if "ultima_sincronizacion" not in st.session_state:
    st.session_state.ultima_sincronizacion = 0

# =======================================================
# 1. INICIALIZACIÓN DEL ESTADO DE LA SESIÓN
# =======================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_cedula" not in st.session_state:
    st.session_state.usuario_cedula = ""
if "usuario_nombre" not in st.session_state:
    st.session_state.usuario_nombre = ""
if "usuario_rol" not in st.session_state:
    st.session_state.usuario_rol = ""
if "cliente_id" not in st.session_state:
    st.session_state.cliente_id = None
if "vista_login" not in st.session_state:
    st.session_state.vista_login = "login"

# DB_PATH = "exprex.db"

# =========================================================================
# 🕵️‍♂️ VERIFICACIÓN DE CREDENCIALES EN BASE DE DATOS
# =========================================================================
def verificar_usuario(cedula, contrasena):
    conexion = sqlite3.connect('exprex.db')
    cursor = conexion.cursor()

    # Evaluamos que coincida la clave y que el trabajador esté ACTIVO ('Sí')
    # Esto aplica de forma general para Administrador y Conductor
    cursor.execute('''
        SELECT cedula, nombre, rol FROM usuarios 
        WHERE cedula = ? AND contrasena = ? AND activo = 'Sí'
    ''', (cedula, contrasena))
    resultado = cursor.fetchone()
    conexion.close()
    return resultado 

# =========================================================================
# 🔏 CAPA DE AUTENTICACIÓN (LOGIN)
# =========================================================================
if not st.session_state.autenticado:
    
    # -------------------------------------------------------------------------
    # OPCIÓN A: MÓDULO RECUPERAR CONTRASEÑA
    # -------------------------------------------------------------------------
    if st.session_state["vista_login"] == "recuperar_contrasena":
        st.markdown("## 🚛 ExpreX Logística")
        mostrar_modulo_recuperar_contrasena() 
        
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

    # -------------------------------------------------------------------------
    # OPCIÓN B: MÓDULO REGISTRO NUEVO
    # -------------------------------------------------------------------------
    elif st.session_state["vista_login"] == "registro_nuevo":
        st.markdown("## 🚛 ExpreX Logística")
        mostrar_modulo_registro()
        
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

    # -------------------------------------------------------------------------
    # OPCIÓN C: MÓDULO RECUPERAR ACCESO TOTAL (SOPORTE WHATSAPP)
    # -------------------------------------------------------------------------
    elif st.session_state["vista_login"] == "soporte_contacto":
        st.markdown("## 🚛 ExpreX Logística")
        st.write("#### 🎧 Soporte Técnico ExpreX")
        st.write("¿Tienes problemas para ingresar, olvidaste tu usuario o necesitas cambiar tus datos de contacto?")
        st.info("💡 Nuestro equipo de Operaciones te atenderá directamente para validar tu identidad y solucionar tu requerimiento de forma segura.")
        
        mensaje_soporte = "Hola, soy chofer de ExpreX y necesito soporte técnico con mi usuario en la aplicación de Exprex Logística."
        url_whatsapp = f"https://wa.me/584140335554?text={mensaje_soporte.replace(' ', '%20')}"

        st.markdown(f"[🚀 ¡Hacer clic aquí para contactar a Soporte Operaciones por WhatsApp!]({url_whatsapp})")
        
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

# ====================================================================================================================================================

    # -------------------------------------------------------------------------
    # OPCIÓN POR DEFECTO: FORMULARIO DE LOGIN TRADICIONAL
    # -------------------------------------------------------------------------
    else:
        st.markdown("## 🚛 ExpreX Logística")
        st.write("### Iniciar Sesión")

        with st.form("formulario_login"):
            campo_cedula = st.text_input("Cédula de Identidad o RIF Empresa:").strip()
            campo_clave = st.text_input("Contraseña", type="password")

            recordar_sesion = st.checkbox("Mantener mi sesión iniciada en este dispositivo", value=True)

            boton_entrar = st.form_submit_button("Ingresar al Sistema")

            if boton_entrar:
                if not campo_cedula or not campo_clave:
                    st.warning("Por favor, rellene todos los campos.")
                else:
                    # 1. Primero verifica si es Administrador o Conductor Activo
                    usuario = verificar_usuario(campo_cedula, campo_clave)
                    
                    if usuario:
                        st.session_state.autenticado = True
                        st.session_state.usuario_cedula = usuario[0] 
                        st.session_state.usuario_nombre = usuario[1]
                        st.session_state.usuario_rol = usuario[2]

                        st.success(f"¡Bienvenido, {usuario[1]}!")
                        time.sleep(1)
                        st.rerun()
                        
                    else:
                        # 2. Si no es interno, ¡buscamos si es un Cliente Corporativo! 🏢
                        try:
                            from modulos.vista_app_clientes import verificar_cliente_b2b
                            cliente = verificar_cliente_b2b(campo_cedula, campo_clave)
                        except ModuleNotFoundError:
                            # Simulador por si aún no tienes la carpeta/módulo creada en esta prueba limpia
                            cliente = None 
                        
                        if cliente:
                            id_clie, rif_clie, razon_social_clie = cliente
                            
                            st.session_state.autenticado = True
                            st.session_state.cliente_id = id_clie
                            st.session_state.usuario_cedula = rif_clie          
                            st.session_state.usuario_nombre = razon_social_clie 
                            st.session_state.usuario_rol = "Cliente"

                            st.success(f"¡Bienvenido al Panel Corporativo, {razon_social_clie}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Cédula/RIF o contraseña incorrecta, o cuenta inactiva. Intente de nuevo.")

        st.markdown("---") # Línea divisoria fina

        # Las 3 columnas de navegación limpia
        col_olvido, col_reg, col_soporte = st.columns(3)
        
        with col_olvido:
            if st.button("🔑 Olvidé mi contraseña", use_container_width=True, type="secondary"):
                st.session_state["vista_login"] = "recuperar_contrasena"
                st.rerun()

        with col_reg:
            if st.button("📝 Registrarme", use_container_width=True, type="secondary"):
                st.session_state["vista_login"] = "registro_nuevo"
                st.rerun()

        with col_soporte:
            if st.button("🎧 Soporte / Contáctanos", use_container_width=True, type="secondary"):
                st.session_state["vista_login"] = "soporte_contacto"
                st.rerun()
                
        st.markdown("---")
        #st.caption("© ExpreX Logística. 2026 - Versión 1.4.0")

else:
    # ---------------------------------------------------
    # VISTA PRINCIPAL (PANTALLA LIMPIA POST-LOGIN)
    # ---------------------------------------------------
    
    st.write(f"## 🚛 ExpreX Logística")
    st.markdown("---")
    
    st.info(f"**Usuario:** {st.session_state.usuario_nombre} -  **Rol:** {st.session_state.usuario_rol}")

    # -------------------------------------------------------------------------
    # VISTA PRINCIPAL (DIRECCIONAMIENTO SEGURO POR ROL)
    # -------------------------------------------------------------------------
    
    # Sincroniza si es la primera vez O si ya pasaron 30 minutos (1800 segundos)
    tiempo_actual = time.time()
    if 'tasa_bcv' not in st.session_state or (tiempo_actual - st.session_state.ultima_sincronizacion) > 1800:
        try:
            from modulos.obtener_tasa_bcv import sincronizar_tasa_bcv
            sincronizar_tasa_bcv()
            st.session_state.ultima_sincronizacion = tiempo_actual
        except Exception as e:
            st.error(f"Error al sincronizar tasa BCV: {e}")
            if 'tasa_bcv' not in st.session_state:
                st.session_state['tasa_bcv'] = "0.00"

    # Si la tasa no se ha cargado en esta sesión, la sincronizamos usando el nuevo módulo
    if 'tasa_bcv' not in st.session_state:
        try:
            from modulos.obtener_tasa_bcv import sincronizar_tasa_bcv
            sincronizar_tasa_bcv()
        except Exception as e:
            st.error(f"Error al importar el módulo de tasa BCV: {e}")
            st.session_state['tasa_bcv'] = "0.00"

# =============================================================================================================

    # 1. EVALUACIÓN DE ADMINISTRADOR
    if st.session_state.usuario_rol == "Administrador":
        try:
            from modulos.vista_app_admin import mostrar_panel_administrador
            mostrar_panel_administrador()
        except Exception as e:
            st.error(f"Error al cargar el panel de Administrador: {e}")
            #st.rerun()
        
    # 2. EVALUACIÓN DE CONDUCTOR
    elif st.session_state.usuario_rol == "Conductor":
        if "chofer_pagina" not in st.session_state:
            st.session_state["chofer_pagina"] = "Menu Principal"

        try:
            # Importamos tu módulo real e invocamos su función quirúrgica pasándole la cédula
            import modulos.vista_app_choferes as ch
            ch.renderizar_panel_conductor(st.session_state.usuario_cedula)
        except Exception as e:
            st.error(f"Error al cargar el panel de Conductor: {e}")
            #st.rerun()
            
    # 3. EVALUACIÓN DE CLIENTE
    elif st.session_state.usuario_rol == "Cliente":
        try:
            from modulos.vista_app_clientes import mostrar_interfaz_cliente
            mostrar_interfaz_cliente()
        except Exception as e:
            st.error(f"Error al cargar el panel de Cliente: {e}")

st.caption("© ExpreX Logística. 2026 - Versión 1.6.3")