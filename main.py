import streamlit as st
import os
import time
import sys
import psycopg2
import urllib.parse

# =========================================================================
# 🔍 CONTROL DE RUTAS CRÍTICO (Soluciona el error 'No module named utils')
# =========================================================================
# Obtenemos la ruta absoluta de la raíz y de la carpeta 'modulos'
ruta_raiz = os.path.dirname(os.path.abspath(__file__))
ruta_modulos = os.path.join(ruta_raiz, "modulos")

# Inyectamos ambas rutas en el sistema de búsqueda de Python para blindar las importaciones
for ruta in [ruta_raiz, ruta_modulos]:
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

# Ahora las importaciones se ejecutarán con total normalidad en tu PC y en la nube
from modulos.rec_cont import mostrar_modulo_recuperar_contrasena
from modulos.nvo_reg import mostrar_modulo_registro
#from modulos.componentes import mostrar_encabezado_exprex
from modulos.version_app import mostrar_version_de_la_app
from streamlit.components.v1 import html

# Configuración de la página
st.set_page_config(page_title="ExpreX Logística", page_icon="exprex_logo_8.png", layout="centered")

def obtener_conexion_db():
    """Busca la variable de entorno 'DATABASE_URL' en Railway de forma automática.

    Si estás en tu PC local, utiliza la URL pública que configuraste para la
    migración.
    """
    # 🛠️ CORRECCIÓN: Agregadas las comillas obligatorias a la URL para evitar el SyntaxError
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:GEwvrkHjgplcirKtSztYrISoKEqcBdXC@tokaido.proxy.rlwy.net:42381/railway",
    )

    # Conexión segura con SSL requerido para PostgreSQL en la nube
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    return conn


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

# =========================================================================
# 🗄️ PERSISTENCIA ULTRA-ESTABLE (MANTIENE LA SESIÓN AL REINICIAR EL SERVIDOR)
# =========================================================================
# Pequeño puente JS/HTML inyectado de forma segura en Streamlit para simular localstorage
from streamlit.components.v1 import html

# --- LÓGICA DE INICIAR SESIÓN ---
def espere(campo_cedula, campo_clave):
    if boton_entrar:  # Ajusta según tus variables
        if campo_cedula and campo_clave:
            
            # 1. Creamos un contenedor temporal para el mensaje y la barra
            con_progreso = st.container()
            
            with con_progreso:
                st.info("🔄 Espere. . .")
                # Inicializamos la barra de progreso en 0%
                barra_espera = st.progress(0)
                
                # Simulamos el avance sutil mientras la base de datos responde
                # (Divide los 2 o 3 segundos en pequeños pasos visuales)
                import time
                for porcentaje in range(0, 101, 10):
                    time.sleep(0.1) # Brevísimo retraso visual para que la barra se mueva
                    barra_espera.progress(porcentaje)
            
            # 2. Aquí ejecutas tu lógica real de conexión a la base de datos
            try:
                # Tu función existente para validar credenciales:
                # usuario_valido = verificar_credenciales(usuario, contrasena)
                pass
                
            except Exception as e:
                st.error(f"Error de conexión: {e}")
                
            finally:
                # 3. Al terminar todo el proceso, limpiamos la barra para que no se quede fija en pantalla
                con_progreso.empty()


def guardar_sesion_local(cedula, nombre, rol, cliente_id=None):
    """Guarda las credenciales de forma persistente en el dispositivo del chofer/usuario"""
    id_cli_str = str(cliente_id) if cliente_id else "null"
    html(f"""
        <script>
            localStorage.setItem("exprex_cedula", "{cedula}");
            localStorage.setItem("exprex_nombre", "{nombre}");
            localStorage.setItem("exprex_rol", "{rol}");
            localStorage.setItem("exprex_cliente_id", "{id_cli_str}");
            localStorage.setItem("exprex_autenticado", "true");
        </script>
    """, height=0)

# Verificamos si no está autenticado en memoria RAM, si hay credenciales guardadas en el navegador
if not st.session_state.autenticado:
    query_params = st.query_params
    
    if "local_cedula" in query_params:
        # Recuperamos y limpiamos inmediatamente
        st.session_state.autenticado = True
        st.session_state.usuario_cedula = query_params["local_cedula"]
        st.session_state.usuario_nombre = query_params["local_nombre"]
        st.session_state.usuario_rol = query_params["local_rol"]
        st.session_state.cliente_id = None if query_params["local_cliente_id"] == "null" else int(query_params["local_cliente_id"])
        
        # Limpiamos los query params para dejar la URL limpia
        st.query_params.clear()
        st.rerun() 
    else:
        # Solo inyectamos el script si la URL no está ya procesando un login
        html("""
            <script>
                const auth = localStorage.getItem("exprex_autenticado");
                if (auth === "true") {
                    const cedula = localStorage.getItem("exprex_cedula");
                    const nombre = localStorage.getItem("exprex_nombre");
                    const rol = localStorage.getItem("exprex_rol");
                    const cliente_id = localStorage.getItem("exprex_cliente_id");
                    
                    const url = new URL(window.location.href);
                    // Verificamos que no estemos ya en un bucle de redirección
                    if (!url.searchParams.has("local_cedula")) {
                        url.searchParams.set("local_cedula", cedula);
                        url.searchParams.set("local_nombre", nombre);
                        url.searchParams.set("local_rol", rol);
                        url.searchParams.set("local_cliente_id", cliente_id);
                        window.location.href = url.toString();
                    }
                }
            </script>
        """, height=0)

# =========================================================================
# 🕵️‍♂️ VERIFICACIÓN DE CREDENCIALES (MIGRADO A POSTGRESQL)
# =========================================================================
def verificar_usuario(cedula, contrasena):
    with obtener_conexion_db() as conexion:
        with conexion.cursor() as cursor:
            # Usamos %s adaptado para PostgreSQL
            cursor.execute('''
                SELECT cedula, nombre, rol FROM usuarios 
                WHERE cedula = %s AND contrasena = %s AND activo = 'Sí'
            ''', (cedula, contrasena))
            resultado = cursor.fetchone()
    return resultado 

# =========================================================================
# 🔏 CAPA DE AUTENTICACIÓN (LOGIN)
# =========================================================================
if not st.session_state.autenticado:
    
    if st.session_state["vista_login"] == "recuperar_contrasena":
        #mostrar_encabezado_exprex()
        st.markdown("## 🚛 ExpreX Logística")
        mostrar_modulo_recuperar_contrasena() 
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

    elif st.session_state["vista_login"] == "registro_nuevo":
        #mostrar_encabezado_exprex()
        st.markdown("## 🚛 ExpreX Logística")
        mostrar_modulo_registro()
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

    elif st.session_state["vista_login"] == "soporte_contacto":
        #mostrar_encabezado_exprex()
        st.markdown("## 🚛 ExpreX Logística")
        st.write("#### 🎧 Soporte Técnico ExpreX")

        st.write("¿Tienes problemas para iniciar sesión? Solicita soporte técnico:")

        # 1. El chofer ingresa su número de teléfono
        telefono_usuario = st.text_input(
            "📞 Ingresa tu número de teléfono registrado:", 
            placeholder="Ej: +584141234567",
            key="tel_soporte"
        )

        # 2. Si el usuario escribió su número, le mostramos el botón de enviar
        if telefono_usuario.strip():
            # Tu número de soporte de ExpreX que recibirá el caso
            numero_soporte_empresa = "584140335554"
            
            # Armamos y codificamos el mensaje para que no falle con las tildes
            mensaje_soporte = f"Hola, soy chofer de ExpreX. Necesito soporte técnico con mi usuario. Mi número de teléfono registrado es: {telefono_usuario}."
            mensaje_codificado = urllib.parse.quote(mensaje_soporte)
            url_whatsapp = f"https://wa.me/{numero_soporte_empresa}?text={mensaje_codificado}"
            
            # Mostramos un botón real y llamativo de "Enviar" que abre la URL
            st.link_button(
                label="🚀 Enviar reporte por WhatsApp", 
                url=url_whatsapp, 
                type="primary",          # Esto lo pinta de azul/color principal de tu tema
                use_container_width=True # Hace que ocupe todo el ancho en la pantalla del celular
            )
        else:
            # Mensaje amigable mientras el campo está vacío
            st.info("💡 Por favor, escribe tu número de teléfono arriba y luego taca aquí para habilitar el botón de envío.")
        
        st.markdown("---")
        if st.button("⬅️ Volver al Inicio de Sesión", use_container_width=True):
            st.session_state["vista_login"] = "login"
            st.rerun()

    else:
        #mostrar_encabezado_exprex()
        st.markdown("### 🚛 ExpreX Logística")
        st.write("#### Iniciar Sesión")

        with st.form("formulario_login"):
            campo_cedula = st.text_input("Cédula de Identidad o RIF Empresa:").strip()
            campo_clave = st.text_input("Contraseña", type="password")
            recordar_sesion = st.checkbox("Mantener mi sesión iniciada en este dispositivo", value=True)
            boton_entrar = st.form_submit_button("Ingresar al Sistema")

            if boton_entrar:
                if not campo_cedula or not campo_clave:
                    st.warning("Por favor, rellene todos los campos.")
                else:
                    usuario = verificar_usuario(campo_cedula, campo_clave)
                    
                    #

                    if usuario:
                        st.session_state.autenticado = True
                        st.session_state.usuario_cedula = usuario[0] 
                        st.session_state.usuario_nombre = usuario[1]
                        st.session_state.usuario_rol = usuario[2]

                        if recordar_sesion:
                            guardar_sesion_local(usuario[0], usuario[1], usuario[2])

                        st.success(f"¡Bienvenido, {usuario[1]}!")
                        espere(campo_cedula, campo_clave)
                        time.sleep(1)
                        st.rerun()
                        
                    else:
                        try:
                            from modulos.vista_app_clientes import verificar_cliente_b2b
                            cliente = verificar_cliente_b2b(campo_cedula, campo_clave)
                        except ModuleNotFoundError:
                            cliente = None 
                        
                        if cliente:
                            id_clie, rif_clie, razon_social_clie = cliente
                            
                            st.session_state.autenticado = True
                            st.session_state.cliente_id = id_clie
                            st.session_state.usuario_cedula = rif_clie          
                            st.session_state.usuario_nombre = razon_social_clie 
                            st.session_state.usuario_rol = "Cliente"

                            if recordar_sesion:
                                guardar_sesion_local(rif_clie, razon_social_clie, "Cliente", id_clie)

                            st.success(f"¡Bienvenido al Panel Corporativo, {razon_social_clie}!")
                            espere(campo_cedula, campo_clave)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Cédula/RIF o contraseña incorrecta, o cuenta inactiva. Intente de nuevo.")

        st.markdown("---")
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

else:
    # ---------------------------------------------------
    # VISTA PRINCIPAL (PANTALLA LIMPIA POST-LOGIN)
    # ---------------------------------------------------
    #mostrar_encabezado_exprex()
    st.write(f"### 🚛 ExpreX Logística")
    st.markdown("---")
    st.info(f"**Usuario:** {st.session_state.usuario_nombre} -  **Rol:** {st.session_state.usuario_rol}")

    # Sincronización de tasa BCV (Cada 30 min)
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

    # Captura de cierre de sesión para purgar LocalStorage
    if not st.session_state.get("autenticado", True):
        html("""
            <script>
                localStorage.clear();
            </script>
        """, height=0)

    # 1. EVALUACIÓN DE ADMINISTRADOR
    if st.session_state.usuario_rol == "Administrador":
        try:
            from modulos.vista_app_admin import mostrar_panel_administrador
            mostrar_panel_administrador()
        except Exception as e:
            st.error(f"Error al cargar el panel de Administrador: {e}")
        
    # 2. EVALUACIÓN DE CONDUCTOR
    elif st.session_state.usuario_rol == "Conductor":
        #if "chofer_pagina" not in st.session_state:
        #    st.session_state["chofer_pagina"] = "Menu Principal"
        #try:
        #    import modulos.vista_app_choferes as ch
        #    ch.renderizar_panel_conductor(st.session_state.usuario_cedula)
        try:
            from modulos.vista_app_choferes import renderizar_panel_conductor
            renderizar_panel_conductor(st.session_state.usuario_cedula)
        except Exception as e:
            st.error(f"Error al cargar el panel de Conductor: {e}")
            
    # 3. EVALUACIÓN DE CLIENTE
    elif st.session_state.usuario_rol == "Cliente":
        try:
            from modulos.vista_app_clientes import mostrar_interfaz_cliente
            mostrar_interfaz_cliente()
        except Exception as e:
            st.error(f"Error al cargar el panel de Cliente: {e}")
mostrar_version_de_la_app()
#st.caption("© ExpreX Logística. 2026 - Versión 1.7.8 • 🔑 Persistencia Activada")