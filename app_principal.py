import os
import time
import base64
import sqlite3
import requests
import urllib3
import pandas as pd
import streamlit as st
import modulos.vista_app_choferes as ch
import streamlit.components.v1 as components
#from pathlib import Path
from bs4 import BeautifulSoup
from streamlit_cookies_manager import EncryptedCookieManager
from streamlit_option_menu import option_menu
from modulos.nomina import mostrar_modulo_nomina
from modulos.combustible import mostrar_modulo_combustible
from modulos.vehiculos import mostrar_modulo_vehiculos
from modulos.gestion_gastos import mostrar_modulo_gastos
from modulos.gastos_viaje import mostrar_modulo_gastos_viaje
from modulos.finanzas_rapidas import mostrar_modulo_finanzas
from modulos.reportes_financieros import mostrar_modulo_reportes
from modulos.reporte_general import mostrar_modulo_reporte_general
from modulos.mantenimiento_sistema import mostrar_modulo_mantenimiento
from modulos.vista_app_clientes import mostrar_interfaz_cliente
from modulos.clientes import mostrar_modulo_clientes
from modulos.operaciones_viajes import mostrar_modulo_operaciones
from modulos.rec_cont import mostrar_modulo_recuperar_contrasena
from modulos.nvo_reg import mostrar_modulo_registro
from modulos.utils import contar_viajes_solicitados_global, reproducir_alerta_victoria

if "vista_login" not in st.session_state:
    st.session_state["vista_login"] = "login"

# =========================================================================
# ⚙️ CONFIGURACIÓN DE LA PÁGINA (¡SIEMPRE DE PRIMERO!)
# =========================================================================
st.set_page_config(page_title="ExpreX Sistema Logístico", page_icon="🚚", layout="centered")

# Inyección de código para que los teléfonos reconozcan el logo en la pantalla de inicio
st.markdown(
    f"""
    <link rel="manifest" href="/home/hector/exprex/manifest.json">
    <link rel="apple-touch-icon" href="/home/hector/exprex/logo_exprex.png">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black">
    """,
    unsafe_allow_html=True
)

# ------------------------------------------------------------------------------------------

# Desactivar advertencias de certificados (el BCV a veces tiene problemas de SSL)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================================
# 🕵️‍♂️ FUNCIÓN DE WEB SCRAPING PARA EL BANCO CENTRAL DE VENEZUELA
# =========================================================================
def obtener_tasa_bcv_en_vivo():
    """Intenta leer la tasa del dólar directo de la web oficial del BCV."""
    try:
        url = "https://www.bcv.org.ve/"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            contenedor_dolar = soup.find(id="dolar")
            if contenedor_dolar:
                tasa_texto = contenedor_dolar.find("strong").text.strip()
                tasa_float = float(tasa_texto.replace(",", "."))
                return tasa_float
    except Exception as e:
        print(f"⚠️ Alerta BCV: No se pudo raspar la web ({e}). Usando respaldo de Base de Datos.")
    return None

# =========================================================================
# 🔄 GESTIÓN DE TASA EN BASE DE DATOS
# =========================================================================
def sincronizar_tasa_bcv():
    """Busca la tasa en internet; si la halla, la guarda. Si no, lee la anterior."""
    conn = sqlite3.connect("exprex.db")
    cursor = conn.cursor()
    tasa_bcv_internet = obtener_tasa_bcv_en_vivo()
    
    # 1. Asegurar que la tabla exista
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    # 2. Asegurar que exista el registro de la tasa para poder actualizarlo
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_bcv', '0')")


    if tasa_bcv_internet:
        cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'tasa_bcv'", (str(tasa_bcv_internet),))
        conn.commit()
        st.toast(f"✅ Tasa BCV actualizada automáticamente: {tasa_bcv_internet} Bs.", icon="🚀")
        tasa_final = tasa_bcv_internet
    else:
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_bcv'")
        tasa_final = float(cursor.fetchone()[0])
        st.toast("📡 Modo Offline: Usando última tasa BCV registrada en sistema.", icon="📦")
        
    conn.close()
    return tasa_final

# ======================================================================================================
# Función para convertir la imagen local a Base64
# ======================================================================================================
#def get_base64_image(image_path):
#    with open(image_path, "rb") as img_file:
#        return base64.b64encode(img_file.read()).decode()

#image_base64 = get_base64_image("/modulos/textura-madera-en-negro.jpg")

#st.markdown(
#    f"""
#    <style>
#    .stApp {{
#        background-image: url("data:image/jpg;base64,{image_base64}");
#        background-size: cover;
#        background-position: center;
#        background-repeat: no-repeat;
#        background-attachment: fixed;
#    }}
#    </style>
#    """,
#    unsafe_allow_html=True
#)

def play_alerta_sonora():
    # URL de un sonido de alerta corto (o puedes poner un archivo local en tu carpeta 'assets')
    # sonido_alerta = "https://actions.google.com/sounds/v1/alarms/beep_short.ogg"

    sonido_alerta = "fanfarria_de_victoria.mp3"
    
    js_code = f"""
    <audio autoplay>
        <source src="{sonido_alerta}" type="audio/ogg">
    </audio>
    """
    components.html(js_code, height=0)

@st.dialog("🚪 Cerrar Servidor del Sistema")
def confirmar_salida_sistema_modal():
    st.warning("¿Está seguro de que desea apagar el servidor de ExpreX?")
    st.write("Esta acción detendrá la aplicación por completo en la computadora.")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ Cancelar y Volver", width="stretch"):
            st.session_state["seleccion"] = "Inicio"
            st.rerun()
            
    with col2:
        if st.button("🛑 Sí, Apagar Sistema", type="primary", width="stretch"):
            st.error("Apagando servidor... Ya puede cerrar esta pestaña del navegador.")
            os._exit(0)

cookies = EncryptedCookieManager(prefix="exprex_", password="Exprex2027")
if not cookies.ready():
    st.stop()  # Espera un milisegundo a que las cookies carguen en el navegador

# =========================================================================
# 1. INICIALIZACIÓN DE VARIABLES DE SESIÓN REALES
# =========================================================================
if 'autenticado' not in st.session_state:
# Intentamos recuperar la sesión desde las cookies del navegador
    if "cedula_guardada" in cookies and "rol_guardado" in cookies:
        st.session_state.autenticado = True
        st.session_state.usuario_cedula = cookies["cedula_guardada"]
        st.session_state.usuario_nombre = cookies["nombre_guardado"]
        st.session_state.usuario_rol = cookies["rol_guardado"]

        # 🏢 Si el rol recuperado es Cliente, rescatamos su ID de inmediato
        if cookies["rol_guardado"] == "Cliente":
            st.session_state.cliente_id = int(cookies.get("cliente_id_guardado", 0))
    else:
        # Si no hay cookies, inicializamos los valores limpios por defecto
        st.session_state.autenticado = False
        st.session_state.usuario_cedula = ""
        st.session_state.usuario_nombre = ""
        st.session_state.usuario_rol = ""
        st.session_state.cliente_id = 0

# Nos aseguramos de que existan siempre las llaves base en el session_state
if 'usuario_cedula' not in st.session_state:
    st.session_state.usuario_cedula = ""
if 'usuario_nombre' not in st.session_state:
    st.session_state.usuario_nombre = ""
if 'usuario_rol' not in st.session_state:
    st.session_state.usuario_rol = ""

# Evita el KeyError al cargar las condicionales del login
if "vista_login" not in st.session_state:
    st.session_state["vista_login"] = "login"

if "tasa_bcv" not in st.session_state:
    st.session_state["tasa_bcv"] = sincronizar_tasa_bcv()

# =========================================================================
# 🕵️‍♂️ VERIFICACIÓN DE CREDENCIALES EN BASE DE DATOS
# =========================================================================
def verificar_usuario(cedula, contrasena):
    conexion = sqlite3.connect('exprex.db')
    cursor = conexion.cursor()
    # Evaluamos que coincida la clave y que el trabajador esté ACTIVO ('Sí')
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
        # Aquí invocas la función del módulo independiente que ya desarrollaste
        mostrar_modulo_recuperar_contrasena() 
        
        # Nota: Ponemos un botón de respaldo por si el usuario quiere desistir
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

    # -------------------------------------------------------------------------
    # OPCIÓN B: MÓDULO REGISTRO NUEVO
    # -------------------------------------------------------------------------
    elif st.session_state["vista_login"] == "registro_nuevo":
        # Aquí invocas tu módulo de registro
        mostrar_modulo_registro()
        
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

    # -------------------------------------------------------------------------
    # OPCIÓN C: MÓDULO RECUPERAR ACCESO TOTAL (SOPORTE WHATSAPP)
    # -------------------------------------------------------------------------
    elif st.session_state["vista_login"] == "soporte_contacto":
        st.write("## 🎧 Soporte Técnico ExpreX")
        st.write("¿Tienes problemas para ingresar, olvidaste tu usuario o necesitas cambiar tus datos de contacto?")
        st.info("💡 Nuestro equipo de Operaciones te atenderá directamente para validar tu identidad y solucionar tu requerimiento de forma segura.")
        
        mensaje_soporte = "Hola, soy chofer de ExpreX y necesito soporte técnico con mi usuario en la aplicación de Exprex Logística."
        url_whatsapp = f"https://wa.me/584140335554?text={mensaje_soporte.replace(' ', '%20')}"

        st.markdown(f"[🚀 ¡Hacer clic aquí para contactar a Soporte Operaciones por WhatsApp!]({url_whatsapp})")
        
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

    # -------------------------------------------------------------------------
    # OPCIÓN POR DEFECTO: FORMULARIO DE LOGIN TRADICIONAL (CON CLIENTE CORPORATIVO)
    # -------------------------------------------------------------------------
    else:
        st.write("### 🚚 ExpreX Logística")
        st.write("#### Iniciar Sesión")

        with st.form("formulario_login"):
            # Nota: El cliente usará este mismo campo para meter su RIF (Ej: J-12345678-0)
            campo_cedula = st.text_input("Cédula de Identidad o RIF Empresa:").strip()
            campo_clave = st.text_input("Contraseña", type="password")

            recordar_sesion = st.checkbox("Mantener mi sesión iniciada en este dispositivo", value=True)

            boton_entrar = st.form_submit_button("Ingresar al Sistema")

            if boton_entrar:
                # 1. Primero verifica si es Administrador o Conductor
                usuario = verificar_usuario(campo_cedula, campo_clave)
                
                if usuario:
                    st.session_state.autenticado = True
                    st.session_state.usuario_cedula = usuario[0] 
                    st.session_state.usuario_nombre = usuario[1]
                    st.session_state.usuario_rol = usuario[2]

                    # 💾 SI MARCÓ LA CASILLA, GUARDAMOS LOS DATOS EN EL NAVEGADOR
                    if recordar_sesion:
                        cookies["cedula_guardada"] = usuario[0]
                        cookies["nombre_guardado"] = usuario[1]
                        cookies["rol_guardado"] = usuario[2]
                        cookies.save()

                    st.success(f"¡Bienvenido, {usuario[1]}!")
                    time.sleep(1)
                    st.rerun()
                    
                else:
                    # 2. Si no es interno, ¡buscamos si es un Cliente Corporativo! 🏢
                    from modulos.vista_app_clientes import verificar_cliente_b2b
                    cliente = verificar_cliente_b2b(campo_cedula, campo_clave)
                    
                    if cliente:
                        id_clie, rif_clie, razon_social_clie = cliente
                        
                        st.session_state.autenticado = True
                        st.session_state.cliente_id = id_clie
                        st.session_state.usuario_cedula = rif_clie          # Guardamos el RIF aquí
                        st.session_state.usuario_nombre = razon_social_clie # Razón Social de la Empresa
                        st.session_state.usuario_rol = "Cliente"

                        # 💾 GUARDAMOS LA SESIÓN DEL CLIENTE EN LAS COOKIES DEL NAVEGADOR
                        if recordar_sesion:
                            cookies["cedula_guardada"] = rif_clie
                            cookies["nombre_guardado"] = razon_social_clie
                            cookies["rol_guardado"] = "Cliente"
                            # Guardamos también el id_cliente como cookie para que no se pierda al refrescar
                            cookies["cliente_id_guardado"] = str(id_clie)
                            cookies.save()

                        st.success(f"¡Bienvenido al Panel Corporativo, {razon_social_clie}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Cédula/RIF o contraseña incorrecta, o cuenta inactiva. Intente de nuevo.")

        st.markdown("---") # Una línea divisoria fina para separar el formulario

        # Creamos las 3 columnas de navegación limpia
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
        
    # =========================================================================
    # LÓGICA DINÁMICA: Dependiendo de qué botón presionen, se muestra la ventana correspondiente
    # =========================================================================
    if st.session_state.get("vista_login") == "recuperar_contrasena":
        st.info("🔄 Formulario para restablecer contraseña por correo o SMS...")
        # Aquí puedes programar el formulario para pedir la cédula y resetear la clave
        if st.button("⬅️ Volver al Login"):
            st.session_state["vista_login"] = "login"
            st.rerun()

    elif st.session_state.get("vista_login") == "registro_nuevo":
        st.success("📋 Formulario de Registro para nuevos Choferes...")
        # Aquí pones los inputs para que un chofer nuevo meta sus datos (Nombre, Cédula, Teléfono)
        if st.button("⬅️ Volver al Login"):
            st.session_state["vista_login"] = "login"
            st.rerun()

# =========================================================================
# 🚀 PANTALLA PRINCIPAL (YA AUTENTICADO)
# =========================================================================
else:
    # Barra superior informativa con los datos reales extraídos del login
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info(f"👤 **Usuario:** {st.session_state.usuario_nombre} | **Rol:** {st.session_state.usuario_rol}")
    with col2:
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario_cedula = ""
            st.session_state.usuario_nombre = ""
            st.session_state.usuario_rol = ""
            if "chofer_pagina" in st.session_state:
                del st.session_state["chofer_pagina"]
            st.rerun()

    # Gestión de avisos flotantes de otras pestañas
    if st.session_state.get("mensaje_exito_flotante"):
        st.toast(st.session_state["mensaje_exito_flotante"], icon="✅")
        del st.session_state["mensaje_exito_flotante"]
        
    #st.write("---")
    
    # =========================================================================
    # 📱 CASO A: EL USUARIO LOGUEADO ES UN CHOFER (INTERFAZ MÓVIL)
    # =========================================================================
    if st.session_state.usuario_rol == "Conductor":
        if "chofer_pagina" not in st.session_state:
            st.session_state["chofer_pagina"] = "Menu Principal"

        # 2. Inyectamos quirúrgicamente el panel del mapa pasándole la cédula de la sesión 🚀
        ch.renderizar_panel_conductor(st.session_state.usuario_cedula)

    # =========================================================================
    # 💻 CASO B: EL USUARIO LOGUEADO ES ADMINISTRADOR (VISTA COMPLETA)
    # =========================================================================
    elif st.session_state.usuario_rol == "Administrador":
        st.header("💼 ExpreX - Control de Operaciones")
        st.sidebar.success(f"Tasa BCV activa: {st.session_state['tasa_bcv']} Bs.")

        # En tu barra lateral, dentro de la lógica del Admin:
        pendientes = contar_viajes_solicitados_global()
        if pendientes > 0:
            st.sidebar.markdown(f"---")
            st.sidebar.error(f"🚨 **¡ATENCIÓN!** Hay {pendientes} fletes pendientes de aprobación.")
            reproducir_alerta_victoria()
        
        opciones_menu = ["Inicio", "Control Operativo", "Gestión de Clientes", "Nómina",  "Control de Flota", "Combustible", "Registrar Gastos", "Gastos de Viaje", "Cuentas", "Reportes", "Reporte General", "Mantenimiento", "Salir del Sistema"]
        iconos_menu = ["house", "book", "briefcase", "person-badge", "truck", "fuel-pump", "receipt", "map", "book", "file-earmark-bar-graph", "building-up", "database-gear", "door-open"]
        
        with st.sidebar:
            st.success(f"Perfil: {st.session_state.usuario_rol}")
            if "menu_navegacion" not in st.session_state:
                st.session_state["menu_navegacion"] = "Inicio"

            seleccion = option_menu(
                menu_title="Navegación",
                options=opciones_menu,
                icons=iconos_menu,
                menu_icon="cast",
                key="menu_navegacion"
            )

        # --- ENRUTADOR DE MÓDULOS DE ADMINISTRACIÓN ---
        if seleccion == "Inicio":
            st.subheader(f"Hola, {st.session_state.usuario_nombre}")
            st.write("Bienvenido al sistema de gestión de transporte de materiales livianos.")
            st.image("/home/hector/exprex/modulos/Flete_Flash_Logo_2.png")
            st.info("Selecciona una opción en el menú izquierdo para empezar a trabajar.")
        elif seleccion == "Gestión de Clientes":
            mostrar_modulo_clientes()
        elif seleccion == "Control Operativo":
            mostrar_modulo_operaciones()
        elif seleccion == "Control de Flota":
            mostrar_modulo_vehiculos()
        elif seleccion == "Nómina":
            mostrar_modulo_nomina()  
        elif seleccion == "Combustible":
            mostrar_modulo_combustible()
        elif seleccion == "Registrar Gastos":
            mostrar_modulo_gastos()
        elif seleccion == "Gastos de Viaje":
            mostrar_modulo_gastos_viaje()
        elif seleccion == "Cuentas":
            mostrar_modulo_finanzas()
        elif seleccion == "Reportes":
            mostrar_modulo_reportes()
        elif seleccion == "Reporte General":
            mostrar_modulo_reporte_general()
        elif seleccion == "Mantenimiento":
            mostrar_modulo_mantenimiento()
        elif seleccion == "Salir del Sistema":
            confirmar_salida_sistema_modal()

    # =========================================================================
    # 🏢 CASO C: EL USUARIO LOGUEADO ES UN CLIENTE CORPORATIVO (NUEVO 🚀)
    # =========================================================================
    elif st.session_state.usuario_rol == "Cliente":

        # Ejecutamos la vista del cliente pasándole sus credenciales activas
        mostrar_interfaz_cliente()

    # =========================================================================
    # 🏢 CASO C: OTROS ROLES (SECRETARIA, VENDEDOR, JEFE DE DEPARTAMENTO)
    # =========================================================================
    else:
        st.subheader(f"🏢 Panel Interno - {st.session_state.usuario_rol}")
        st.write(f"Hola, {st.session_state.usuario_nombre}. Bienvenido a tu panel operativo.")
        st.info("Próximamente se habilitarán las opciones restringidas para tu cargo. Por los momentos, el acceso total está reservado a la Administración.")

st.markdown("---") # Una línea divisoria sutil
st.caption("© ExpreX Logística. 2026 - Versión 1.4.0")