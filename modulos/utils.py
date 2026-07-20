import base64
import os
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st


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


def reproducir_alerta_victoria():
    """Inyecta un componente de audio HTML oculto para reproducir la fanfarria

    de victoria en el navegador del usuario (PC o Celular).
    """
    ruta_sonido = "/modulos/tono_alerta_de_app.mp3"
    try:
        with open(ruta_sonido, "rb") as f:
            datos_audio = f.read()

        # Convertimos el archivo a un formato que el navegador acepta de forma nativa
        audio_base64 = base64.b64encode(datos_audio).decode()
        html_audio = f"""
            <audio autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
        """
        # Inyectamos el audio oculto en la interfaz
        st.markdown(html_audio, unsafe_allow_html=True)
    except Exception as e:
        # Usamos caption silencioso para que si falla el archivo de audio, la app siga operativa
        st.caption(f"🔊 Alerta sonora no disponible.")

# -----------------------------------------------------------------------------------------------------------------

# Función para contar viajes solicitados globalmente
def contar_viajes_solicitados_global():
    """Para la PC: Cuenta todas las solicitudes nuevas de clientes sin asignar"""
    cantidad = 0  # 🔑 SOLUCIÓN PYLANCE: Aseguramos que la variable exista siempre antes del try
    try:
        # 🔌 Cambiado a PostgreSQL con manejo seguro de conexiones 'with'
        with obtener_conexion_db() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM viajes WHERE estatus_viaje = 'Solicitado'"
                )
                # Saneado para evitar el error 'NoneType' en Pylance
                resultado = cursor.fetchone()
                cantidad = int(resultado[0]) if resultado is not None else 0
    except Exception as e:
        st.error(f"❌ Error al contar viajes globales: {e}")

    return cantidad

# -----------------------------------------------------------------------------------------------------------------

# Función para contar viajes pendientes de un chofer específico
def contar_viajes_por_salir(cedula_conductor: str) -> int:
    """Cuenta los viajes pendientes 'Por Salir' específicos de un conductor."""
    try:
        with obtener_conexion_db() as conexion:
            with conexion.cursor() as cursor:
                # Filtramos por estatus Y por la cédula del conductor que consulta
                sql = """
                    SELECT COUNT(*) 
                    FROM viajes 
                    WHERE estatus_viaje = 'Por Salir' 
                      AND cedula_conductor = %s
                """
                cursor.execute(sql, (str(cedula_conductor),))
                
                # Saneado para evitar el error 'NoneType' en Pylance
                resultado = cursor.fetchone()
                cantidad = int(resultado[0]) if resultado is not None else 0
                return cantidad
    except Exception:
        return 0

# ------------------------------------------------------------------------------------------------------------------

def contar_viajes_en_ruta(cedula_conductor: str) -> int:
    """Cuenta los viajes activos 'En Ruta' específicos de un conductor."""
    try:
        with obtener_conexion_db() as conexion:
            with conexion.cursor() as cursor:
                # Filtramos por estatus Y por la cédula del conductor que consulta
                sql = """
                    SELECT COUNT(*) 
                    FROM viajes 
                    WHERE estatus_viaje = 'En Ruta' 
                      AND cedula_conductor = %s
                """
                cursor.execute(sql, (str(cedula_conductor),))
                
                # Saneado para evitar el error 'NoneType' en Pylance
                resultado = cursor.fetchone()
                cantidad = int(resultado[0]) if resultado is not None else 0
                return cantidad
    except Exception:
        return 0
    
# =============================================================================================================================

def mostrar_evidencia_entrega(ruta_desde_db):
    """
    Renderiza la foto de entrega si está en la PC local (Héctor), 
    o muestra un mensaje informativo si se accede desde otro dispositivo.
    """
    if not ruta_desde_db:
        st.warning("⚠️ Este viaje no tiene ninguna evidencia de foto registrada.")
        return

    # Ruta raíz en tu Linux Mint
    ruta_raiz_hector = "/home/hector/exprex/fotos_entregas"
    
    # Corregido: Validamos si es absoluta o relativa usando os.path directamente
    if not os.path.isabs(ruta_desde_db):
        ruta_absoluta_local = os.path.join(ruta_raiz_hector, ruta_desde_db)
    else:
        ruta_absoluta_local = ruta_desde_db

    # Verificamos si el archivo existe físicamente en el disco
    if os.path.exists(ruta_absoluta_local):
        st.success("📸 Evidencia localizada en el almacenamiento local:")
        st.image(
            ruta_absoluta_local, 
            caption=f"Evidencia: {os.path.basename(ruta_desde_db)}", 
            use_container_width=True
        )
    else:
        st.info("📦 **Almacenamiento Local Protegido**")
        st.markdown(
            f"""
            La imagen de evidencia para este flete (`{os.path.basename(ruta_desde_db)}`) 
            se encuentra resguardada de forma segura en el servidor central de **ExpreX**.
            
            💡 *Si necesitas visualizar o descargar este archivo, por favor solicítalo directamente a la administración.*
            """
        )

# ===========================================================================================================================

#def info_espere():
    # --- LÓGICA DE INICIAR SESIÓN ---
#if boton_login or enter_pulsado:  # Ajusta según tus variables
#    if usuario and contrasena:
#        
#        # 1. Creamos un contenedor temporal para el mensaje y la barra
#        con_progreso = st.container()
#        
#        with con_progreso:
#            st.info("🔄 Espere. . .")
#            # Inicializamos la barra de progreso en 0%
#            barra_espera = st.progress(0)
#            
#            # Simulamos el avance sutil mientras la base de datos responde
#            # (Divide los 2 o 3 segundos en pequeños pasos visuales)
#            import time
#            for porcentaje in range(0, 101, 10):
#                time.sleep(0.1) # Brevísimo retraso visual para que la barra se mueva
#                barra_espera.progress(porcentaje)
#        
#        # 2. Aquí ejecutas tu lógica real de conexión a la base de datos
#        try:
#            # Tu función existente para validar credenciales:
#            # usuario_valido = verificar_credenciales(usuario, contrasena)
#            pass
            
#        except Exception as e:
#            st.error(f"Error de conexión: {e}")
#            
#        finally:
#            # 3. Al terminar todo el proceso, limpiamos la barra para que no se quede fija en pantalla
#            con_progreso.empty()