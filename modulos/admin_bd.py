import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# 🛠️ IMPORTAMOS TU FUNCIÓN CENTRALIZADA DE CONEXIÓN
# Si 'obtener_conexion_db' está en utils.py, cámbialo a: from utils import obtener_conexion_db
from utils import obtener_conexion_db 

def seccion_administrador_tablas():
    st.write("### 🛠️ Consola de Administración de Base de Datos (PostgreSQL)")
    st.caption("Acceso exclusivo para edición, auditoría y corrección en caliente de tablas en Railway.")

    # 🔑 VALIDACIÓN DIRECTA POR PALABRA CLAVE NATIVA
    clave_acceso = st.text_input(
        "🔑 Introduce la clave de Administrador para desbloquear:", 
        type="password", 
        placeholder="Escribe la contraseña maestra..."
    )

    if clave_acceso != "Exprex2026":
        if clave_acceso: 
            st.error("🛑 Clave incorrecta. Acceso denegado.")
        else:
            st.info("🔒 La consola se encuentra bloqueada. Introduce la credencial para ver las tablas.")
        return

    # SÍ PASÓ LA CLAVE -> MODO DIOS ACTIVADO
    st.success("🔓 ¡Acceso concedido, Héctor! Conectado a la base de datos de producción.")
    st.markdown("---")

    # 📂 OBTENER LISTA DE TABLAS REALES DE POSTGRESQL
    lista_tablas = []
    try:
        with obtener_conexion_db() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                      AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                lista_tablas = [fila[0] for fila in cursor.fetchall()]
    except Exception as e:
        st.error(f"❌ Error al consultar el esquema de PostgreSQL: {e}")
        return

    if not lista_tablas:
        st.warning("⚠️ No se encontraron tablas públicas en la base de datos actual.")
        return

    tabla_seleccionada = st.selectbox("👉 Selecciona la tabla que deseas auditar/editar:", lista_tablas)

    if tabla_seleccionada:
        st.write(f"### 📋 Vista de la tabla: `{tabla_seleccionada}`")
        
        df_completo = pd.DataFrame()
        pk_columna = None

        # 🔍 LEER DATOS Y DETECTAR LA CLAVE PRIMARIA DE LA TABLA
        try:
            with obtener_conexion_db() as conn:
                # 1. Traemos los datos
                df_completo = pd.read_sql_query(f"SELECT * FROM {tabla_seleccionada}", conn)
                
                # 2. Investigamos cuál es la columna Primary Key de esta tabla específica
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT kcu.column_name 
                        FROM information_schema.table_constraints tco
                        JOIN information_schema.key_column_usage kcu 
                          ON kcu.constraint_name = tco.constraint_name
                         AND kcu.table_schema = tco.table_schema
                        WHERE tco.constraint_type = 'PRIMARY KEY'
                          AND tco.table_name = %s;
                    """, (tabla_seleccionada,))
                    res_pk = cursor.fetchone()
                    if res_pk:
                        pk_columna = res_pk[0]
        except Exception as e:
            st.error(f"❌ Error al cargar datos de la tabla: {e}")
            return

        if df_completo.empty:
            st.info(f"La tabla `{tabla_seleccionada}` está vacía.")
            return

        st.warning(f"⚠️ Las modificaciones se guardarán fila por fila usando la clave primaria: `{pk_columna or 'No detectada'}`.")
        
        # 📝 RENDERIZADO DEL EDITOR INTERACTIVO
        datos_editados = st.data_editor(
            df_completo, 
            use_container_width=True, 
            key=f"editor_{tabla_seleccionada}",
            disabled=[pk_columna] if pk_columna else [] # Impedimos editar la PK para no romper relaciones
        )
        
        # 💾 DETECCIÓN DE CAMBIOS Y GUARDADO SEGURO MEDIANTE UPDATES
        if not df_completo.equals(datos_editados):
            if st.button("💾 Guardar Cambios en Railway", type="primary"):
                if not pk_columna:
                    st.error("🛑 No se puede actualizar automáticamente esta tabla porque no tiene una clave primaria definida.")
                    return
                
                try:
                    # Encontramos cuáles índices de filas cambiaron en el DataFrame
                    filas_cambiadas = datos_editados.loc[(df_completo != datos_editados).any(axis=1)]
                    
                    with obtener_conexion_db() as conn:
                        with conn.cursor() as cursor:
                            for idx, fila in filas_cambiadas.iterrows():
                                valor_pk = fila[pk_columna]
                                
                                # Construimos el UPDATE dinámico con las columnas editadas
                                columnas_update = [col for col in datos_editados.columns if col != pk_columna]
                                seteos = ", ".join([f"{col} = %s" for col in columnas_update])
                                valores = [None if pd.isna(fila[col]) else fila[col] for col in columnas_update]
                                
                                query = f"UPDATE {tabla_seleccionada} SET {seteos} WHERE {pk_columna} = %s"
                                valores.append(valor_pk)
                                
                                cursor.execute(query, valores)
                        conn.commit()
                        
                    st.success(f"🎉 ¡Se actualizaron {len(filas_cambiadas)} registros con éxito en la nube!")
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al ejecutar la actualización en caliente: {e}")