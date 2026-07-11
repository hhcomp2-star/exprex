import streamlit as st
import sqlite3
import os
import shutil
from datetime import datetime

# Importamos la función de la consola de administración desde tu otro archivo
# Recuerda crear el archivo 'admin_bd.py' con el código de la consola en la misma carpeta
try:
    from modulos.admin_bd import seccion_administrador_tablas
except ImportError:
    # Si aún no has creado el archivo admin_bd.py, definimos una función temporal para que no rompa la app
    def seccion_administrador_tablas():
        st.warning("⚠️ El archivo `admin_bd.py` no se encuentra en el directorio del proyecto.")

def mostrar_modulo_mantenimiento():
    st.subheader("🛠️ Mantenimiento y Seguridad del Sistema")
    
    # =========================================================================
    # 📑 CREACIÓN DE LAS PESTAÑAS (TABS)
    # =========================================================================
    tab_respaldos, tab_consola_bd = st.tabs(["💾 Respaldos de Seguridad", "🗄️ Consola de Base de Datos"])
    
    # -------------------------------------------------------------------------
    # PESTAÑA 1: RESPALDOS DE SEGURIDAD (Tu código original)
    # -------------------------------------------------------------------------
    with tab_respaldos:
        st.write("### 💾 Respaldo de Base de Datos (Backup)")
        st.markdown("""
        Este módulo te permite generar una copia exacta y segura de toda la información de **ExpreX** (viajes, gastos, vehículos y configuraciones) en la carpeta local que tú elijas de tu entorno Linux Mint.
        """)
        
        db_produccion = "exprex.db"
        
        if not os.path.exists(db_produccion):
            st.error(f"❌ No se encontró la base de datos activa `{db_produccion}` en la raíz del proyecto.")
        else:
            tamaño_kb = os.path.getsize(db_produccion) / 1024
            ultima_mod = datetime.fromtimestamp(os.path.getmtime(db_produccion)).strftime('%d/%m/%Y %I:%M %p')
            
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.info(f"📁 **Base de datos activa:** `{os.path.abspath(db_produccion)}`")
            with col_info2:
                st.info(f"📊 **Tamaño actual:** `{tamaño_kb:.2f} KB` | **Último cambio:** `{ultima_mod}`")
                
            st.subheader("⚙️ Configurar Destino del Respaldo")
            
            ruta_sugerida = f"/home/hector/Mi_Nube_MEGA/respaldos_exprex"
            
            ruta_destino = st.text_input(
                "📂 Especifica la ruta absoluta de la carpeta contenedora:", 
                value=ruta_sugerida,
                placeholder="Ejemplo: /home/hector/Documentos/BackupsExprex",
                key="input_ruta_backup" # Agregamos un key único por seguridad de renderizado
            )
            
            st.caption("💡 *Nota: Si la carpeta que escribes no existe en tu disco, el sistema intentará crearla automáticamente por ti.*")
            st.markdown("<br>", unsafe_allow_html=True)
            
            btn_respaldar = st.button("💾 Generar Copia de Seguridad Ahora", type="primary", use_container_width=True)
            
            if btn_respaldar:
                if not ruta_destino.strip():
                    st.error("❌ Por favor, especifica una ruta de carpeta válida.")
                else:
                    try:
                        carpeta_limpia = ruta_destino.strip()
                        if not os.path.exists(carpeta_limpia):
                            os.makedirs(carpeta_limpia, exist_ok=True)
                        
                        ahora_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        nombre_respaldo = f"exprex_backup_{ahora_str}.db"
                        ruta_completa_respaldo = os.path.join(carpeta_limpia, nombre_respaldo)
                        
                        con_origen = sqlite3.connect(db_produccion)
                        con_destino = sqlite3.connect(ruta_completa_respaldo)
                        
                        with con_destino:
                            con_origen.backup(con_destino)
                            
                        con_destino.close()
                        con_origen.close()
                        
                        st.success(f"✅ **¡Respaldo creado con éxito total!**")
                        st.markdown(f"""
                        * **Archivo generado:** `{nombre_respaldo}`
                        * **Ubicación exacta:** `{os.path.abspath(ruta_completa_respaldo)}`
                        
                        Ya puedes verificar la carpeta desde tu gestor de archivos de Linux Mint. ¡Datos protegidos!
                        """)                
                    except Exception as e:
                        st.error(f"❌ Ocurrió un error al intentar escribir en la ruta especificada: {e}")
                        st.info("Verifica que tengas permisos de escritura en la carpeta seleccionada.")

    # -------------------------------------------------------------------------
    # PESTAÑA 2: CONSOLA DE BASE DE DATOS (Módulo de administrador)
    # -------------------------------------------------------------------------
    with tab_consola_bd:
        # Llamamos a la función importada que maneja la seguridad y la edición de tablas
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