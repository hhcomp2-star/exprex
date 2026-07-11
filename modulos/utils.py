import streamlit as st
import sqlite3
import base64

def reproducir_alerta_victoria():
    """
    Inyecta un componente de audio HTML oculto para reproducir la fanfarria
    de victoria en el navegador del usuario (PC o Celular).
    """
    ruta_sonido = "/home/hector/exprex/tono_alerta_de_app.mp3"
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
    conexion = sqlite3.connect('exprex.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT COUNT(*) FROM viajes WHERE estatus_viaje = 'Solicitado'")
    cantidad = cursor.fetchone()[0]
    conexion.close()
    return cantidad

# -----------------------------------------------------------------------------------------------------------------

# Función para contar viajes pendientes de un chofer específico
def contar_viajes_pendientes_chofer(cedula_chofer):
    """Para el Teléfono: Cuenta fletes asignados a UN chofer específico que no han iniciado"""
    conexion = sqlite3.connect('exprex.db')
    cursor = conexion.cursor()
    # Buscamos los fletes asignados a él que están esperando por salir
    cursor.execute("""
        SELECT COUNT(*) 
        FROM viajes 
        WHERE cedula_conductor = ? AND estatus_viaje = 'Por Salir'
    """, (cedula_chofer,))
    cantidad = cursor.fetchone()[0]
    conexion.close()
    return cantidad
