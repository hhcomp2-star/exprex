import streamlit as st
import os
import io
import zipfile
import pandas as pd
from datetime import datetime
from typing import Any

# Asumo que tienes un módulo de conexión a tu base de datos de PostgreSQL en Railway
# Por ejemplo: de tu modulo_conexion import obtener_conexion_db
# (Ajusta la importación según cómo estructuraste la conexión a PostgreSQL)
try:
    # Reemplaza esto con tu función real de conexión a PostgreSQL
    from modulos.utils import obtener_conexion_db  
except ImportError:
    # Definimos una función simulada por si acaso
    def obtener_conexion_db() -> Any:
        st.error("⚠️ No se pudo importar la función de conexión a PostgreSQL.")
        return None

try:
    from modulos.admin_bd import seccion_administrador_tablas
except ImportError:
    def seccion_administrador_tablas():
        st.warning("⚠️ El archivo `admin_bd.py` no se encuentra en el directorio del proyecto.")

def generar_respaldo_csv():
    """
    Obtiene todas las tablas de PostgreSQL y las empaqueta en un archivo ZIP 
    con formato CSV para que Hector pueda abrirlas en LibreOffice Calc.
    """
    conn = obtener_conexion_db()
    if not conn:
        return None
    
    # Creamos un archivo temporal en memoria RAM
    buffer_memoria = io.BytesIO()
    
    try:
        # 1. Obtener la lista de tablas de la base de datos (excluyendo las del sistema)
        query_tablas = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE';
        """
        tablas = pd.read_sql(query_tablas, conn)['table_name'].tolist()
        
        if not tablas:
            st.warning("⚠️ No se encontraron tablas activas en la base de datos.")
            conn.close()
            return None
        
        # 2. Creamos el archivo ZIP en memoria
        with zipfile.ZipFile(buffer_memoria, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for tabla in tablas:
                # Leemos cada tabla directamente a un DataFrame de Pandas
                df = pd.read_sql(f"SELECT * FROM {tabla};", conn)
                
                # Convertimos el DataFrame a CSV codificado en UTF-8
                csv_data = df.to_csv(index=False, encoding='utf-8')
                
                # Guardamos el CSV dentro del archivo ZIP
                zip_file.writestr(f"{tabla}.csv", csv_data)
                
        conn.close()
        buffer_memoria.seek(0)
        return buffer_memoria
        
    except Exception as e:
        st.error(f"❌ Error al extraer los datos: {e}")
        if conn:
            conn.close()
        return None


def mostrar_modulo_mantenimiento():
    st.subheader("🛠️ Mantenimiento y Seguridad del Sistema (Nube Railway)")
    
    tab_respaldos, tab_consola_bd = st.tabs(["💾 Respaldos de Seguridad", "🗄️ Consola de Base de Datos"])
    
    # -------------------------------------------------------------------------
    # PESTAÑA 1: RESPALDOS DE SEGURIDAD (Rediseñada para la nube)
    # -------------------------------------------------------------------------
    with tab_respaldos:
        st.write("### 💾 Respaldo de Base de Datos (PostgreSQL)")
        st.markdown("""
        Al estar en **Railway**, tu base de datos PostgreSQL está protegida en la nube. Sin embargo, 
        siempre es una excelente práctica tener copias de seguridad locales en tu computador.
        """)
        
        # --- SECCIÓN A: Descarga local en CSV para LibreOffice Calc ---
        st.markdown("#### 📥 Opción 1: Descargar tablas activas en formato CSV (Local)")
        st.info("Este botón extraerá toda la información actual de la base de datos en tiempo real y generará un archivo `.zip` con un archivo `.csv` para cada tabla, listo para que lo uses en **LibreOffice Calc**.")
        
        # Botón dinámico de descarga de Streamlit (el procesamiento ocurre en la RAM del servidor y se descarga al navegador)
        # Esto evita problemas de escritura de archivos en el disco de Railway.
        respaldo_zip = generar_respaldo_csv()
        
        if respaldo_zip:
            ahora_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 Descargar todas las tablas (.ZIP)",
                data=respaldo_zip,
                file_name=f"exprex_respaldo_csv_{ahora_str}.zip",
                mime="application/zip",
                use_container_width=True
            )
        else:
            st.warning("⚠️ No se pudo preparar la descarga. Verifica la conexión con PostgreSQL.")
            
        st.markdown("<hr>", unsafe_allow_html=True)
        
        # --- SECCIÓN B: Instrucciones para respaldos completos de base de datos ---
        st.markdown("#### ☁️ Opción 2: Respaldos automáticos y completos (En Railway)")
        st.markdown("""
        Para realizar una copia de seguridad estructural completa (un archivo `.sql` restaurable):
        
        1. **Entra a tu panel de Railway** y selecciona tu proyecto de **ExpreX**.
        2. Haz clic en el servicio de **PostgreSQL**.
        3. Dirígete a la pestaña de **Backups** (Copias de seguridad).
        4. Allí verás los respaldos automáticos diarios y podrás generar un respaldo manual con un solo clic para descargarlo a tu carpeta de copias de seguridad en Linux Mint.
        """)
        
    # -------------------------------------------------------------------------
    # PESTAÑA 2: CONSOLA DE BASE DE DATOS (Módulo de administrador)
    # -------------------------------------------------------------------------
    with tab_consola_bd:
        # Al ejecutar esto, asegúrate de que el código interno de 'seccion_administrador_tablas'
        # use 'obtener_conexion_db()' de PostgreSQL en lugar de 'sqlite3.connect()'
        seccion_administrador_tablas()

    # =========================================================================
    # BOTÓN DE RETORNO (Se mantiene al final de todo el módulo)
    # =========================================================================
    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    def ir_al_inicio_seguro():
        st.session_state["menu_navegacion"] = "Inicio"
    
    st.button(
        "↩️ Volver al Inicio", 
        type="secondary", 
        use_container_width=True,
        on_click=ir_al_inicio_seguro
    )