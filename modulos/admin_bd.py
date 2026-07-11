# Contenido de admin_bd.py corregido e infalible
import streamlit as st
import sqlite3
import pandas as pd

def seccion_administrador_tablas():
    st.write("### 🛠️ Consola de Administración de Base de Datos")
    st.caption("Acceso exclusivo para edición y auditoría total de tablas.")

    personal_base_datos = "exprex.db"

    # 🔑 VALIDACIÓN DIRECTA POR PALABRA CLAVE NATIVA
    # Esto ignora por completo si el login falló o si session_state se borró
    clave_acceso = st.text_input(
        "🔑 Introduce la clave de Administrador para desbloquear:", 
        type="password", 
        placeholder="Escribe la contraseña maestra..."
    )

    # Define aquí la clave provisoria que tú quieras (ejemplo: "exprex2026")
    if clave_acceso != "Exprex2026":
        if clave_acceso: # Si escribió algo pero está mal
            st.error("🛑 Clave incorrecta. Acceso denegado.")
        else:
            st.info("🔒 La consola se encuentra bloqueada. Introduce la credencial para ver las tablas.")
        return

    #  SÍ PASÓ LA CLAVE -> SE DESBLOQUEA TODO EL CONTENIDO INFERIOR
    st.success("🔓 ¡Acceso concedido, Héctor! Modo Dios activado.")
    st.markdown("---")

    try:
        conn = sqlite3.connect(personal_base_datos)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        lista_tablas = [fila[0] for fila in cursor.fetchall()]
        conn.close()
    except Exception as e:
        st.error(f"Error al conectar a la base de datos: {e}")
        return

    if not lista_tablas:
        st.warning("No se encontraron tablas en la base de datos.")
        return

    tabla_seleccionada = st.selectbox("👉 Selecciona la tabla que deseas auditar/editar:", lista_tablas)

    if tabla_seleccionada:
        st.write(f"### 📋 Vista Completa de la tabla: `{tabla_seleccionada}`")
        
        conn = sqlite3.connect(personal_base_datos)
        df_completo = pd.read_sql_query(f"SELECT * FROM {tabla_seleccionada}", conn)
        conn.close()

        if df_completo.empty:
            st.info(f"La tabla `{tabla_seleccionada}` está vacía.")
        else:
            st.warning("⚠️ Los cambios realizados en la tabla se aplicarán directamente en la base de datos.")
            
            datos_editados = st.data_editor(
                df_completo, 
                use_container_width=True, 
                key=f"editor_{tabla_seleccionada}"
            )
            
            if not df_completo.equals(datos_editados):
                if st.button("💾 Guardar Cambios en la Base de Datos", type="primary"):
                    try:
                        conn = sqlite3.connect(personal_base_datos)
                        datos_editados.to_sql(tabla_seleccionada, conn, if_exists='replace', index=False)
                        conn.close()
                        st.success("🎉 ¡Base de datos actualizada con éxito!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error al guardar los cambios: {e}")