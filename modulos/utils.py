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