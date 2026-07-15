import streamlit as st
import pandas as pd
import time
from datetime import datetime

# Importamos la conexión centralizada desde tus utilidades
from modulos.utils import obtener_conexion_db

def mostrar_modulo_gastos_viaje():
    st.write("### 🛣️ Control de Gastos Operativos de Viaje (Ruta)")
    
    # 1. Recuperamos la tasa BCV automática de tu sistema
    tasa_bcv_sistema = st.session_state.get("tasa_bcv", 45.00)

    # 2. Buscamos las placas activas para amarrar el gasto al camión correcto
    df_placas = pd.DataFrame(columns=["placa", "nombre"])
    
    try:
        with obtener_conexion_db() as conexion:
            with conexion.cursor() as cursor:
                query_placas = """
                    SELECT c.placa, u.nombre 
                    FROM conductores c
                    JOIN usuarios u ON c.cedula = u.cedula
                    WHERE u.activo = 'Sí'
                """
                cursor.execute(query_placas)
                filas = cursor.fetchall()
                if cursor.description:
                    columnas = [desc[0] for desc in cursor.description]
                    df_placas = pd.DataFrame(filas, columns=columnas)
    except Exception as e:
        st.error(f"Error al cargar conductores y vehículos: {e}")
    
    if not df_placas.empty:
        opciones_placas = [f"{row['placa']} (Chofer: {row['nombre']})" for index, row in df_placas.iterrows()]
    else:
        opciones_placas = ["No hay vehículos registrados"]

    # Creamos las pestañas de trabajo
    tab_registrar, tab_historial = st.tabs(["📝 Registrar Gasto de Ruta", "📊 Historial de Gastos"])

    # ----------------------------------------------------
    # PESTAÑA 1: FORMULARIO DE REGISTRO BIDIRECCIONAL
    # ----------------------------------------------------
    with tab_registrar:
        st.write("#### Asentar Gasto de Operación")

        # Creamos la estructura visual idéntica a tu diseño en dos columnas
        col1, col2 = st.columns(2)
        
        with col1:
            vehiculo_selected = st.selectbox("🚗 Camión / Unidad:", opciones_placas)
            c_fecha = st.date_input("Fecha del Gasto", datetime.now())
            
            tipo_gasto = st.selectbox(
                "💰 Concepto del Gasto:", 
                ["Viáticos (Comida/Hospedaje)", "Peajes", "Aseguramiento de Carga (Anime/Madera/Flejes)", "Imprevisto Mecánico Corto", "Otros Gastos de Ruta"]
            )
            ruta = st.text_input("🛣️ Ruta / Trayecto (Opcional):", placeholder="Ej: Caracas - Valencia")
            
        with col2:
            # Sub-columnas internas para el monto y la moneda pegados
            col_monto, col_moneda = st.columns([2, 1])
            
            with col_monto:
                monto_ingresado = st.number_input("Monto total gastado:", min_value=0.0, step=10.0, value=0.0)
            
            with col_moneda:
                moneda = st.selectbox("Moneda:", ["Bs.", "$"])
            
            # Dejamos la tasa a la vista, ajustable por si acaso
            c_tasa = st.number_input("Tasa BCV Aplicada:", min_value=0.0, value=float(tasa_bcv_sistema), step=0.01)
            observaciones = st.text_area("Detalle / Observación:", placeholder="Ej: Pago en la vía.")
            
            st.write("") # Espaciador
            boton_guardar = st.button("💾 Guardar Gasto de Viaje", use_container_width=True, type="primary")
        
        # 💸 LA MAGIA MATEMÁTICA: Calculamos los dos valores fijos antes de guardar según la moneda elegida
        if moneda == "Bs.":
            final_bs = monto_ingresado
            final_usd = monto_ingresado / c_tasa if c_tasa > 0 else 0.0
        else:
            final_usd = monto_ingresado
            final_bs = monto_ingresado * c_tasa

        # Tarjeta informativa abajo que confirma en tiempo real la conversión exacta
        st.info(f"📊 **Monto a registrar en los libros:** {final_bs:,.2f} Bs. ⇄ **{final_usd:,.2f} USD**")
        
        # LÓGICA DE PROCESAMIENTO AL DAR CLIC EN GUARDAR
        if boton_guardar:
            if df_placas.empty or opciones_placas[0] == "No hay vehículos registrados":
                st.error("❌ No se pueden asentar gastos sin unidades registradas.")
            elif monto_ingresado == 0.0:
                st.error("❌ El monto del gasto debe ser mayor a cero.")
            else:
                placa_limpia = str(vehiculo_selected).split(" ")[0]
                
                try:
                    with obtener_conexion_db() as conexion:
                        with conexion.cursor() as cursor:
                            query_insert = """
                                INSERT INTO gastos_operativos_viaje 
                                (fecha, placa, tipo_gasto, monto_bs, tasa_cambio, monto_usd, estacion_origen_destino, observaciones)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            cursor.execute(query_insert, (
                                c_fecha, 
                                placa_limpia, 
                                tipo_gasto, 
                                round(final_bs, 2), 
                                c_tasa, 
                                round(final_usd, 2), 
                                ruta, 
                                observaciones
                            ))
                            conexion.commit()
                            
                    st.success(f"✅ Gasto guardado con éxito: {round(final_bs, 2)} Bs. ({round(final_usd, 2)} USD)")
                    time.sleep(1.5)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar en PostgreSQL: {e}")
                    
    # ----------------------------------------------------
    # PESTAÑA 2: HISTORIAL DE GASTOS OPERATIVOS (Con Modificación y Borrado)
    # ----------------------------------------------------
    with tab_historial:
        st.write("#### Libro de Gastos de Ruta Acumulados")
        
        df_historial = pd.DataFrame()
        try:
            with obtener_conexion_db() as conexion:
                with conexion.cursor() as cursor:
                    query_historial = """
                        SELECT id AS "ID", fecha AS "Fecha", placa AS "Camión", tipo_gasto AS "Concepto", 
                               estacion_origen_destino AS "Ruta", monto_bs AS "Monto Bs", 
                               tasa_cambio AS "Tasa BCV", monto_usd AS "Costo $", observaciones AS "Detalle"
                        FROM gastos_operativos_viaje
                        ORDER BY id DESC
                    """
                    cursor.execute(query_historial)
                    filas = cursor.fetchall()
                    if cursor.description:
                        columnas = [desc[0] for desc in cursor.description]
                        df_historial = pd.DataFrame(filas, columns=columnas)
        except Exception as e:
            st.error(f"Error al consultar el historial de gastos: {e}")
        
        if df_historial.empty:
            st.info("No se han registrado gastos operativos de viaje todavía.")
        else:
            # Mostramos la tabla (incluye la columna ID de primero)
            st.dataframe(df_historial, use_container_width=True, hide_index=True)
            
            st.write("---")
            st.write("### ⚙️ Panel de Modificación y Ajustes")
            
            # Aseguramos que los IDs sean enteros limpios y no contengan None para evitar quejas de Pylance
            lista_ids = [int(x) for x in df_historial["ID"].dropna().tolist()]
            id_seleccionado = st.selectbox("✏️ Seleccione el ID del gasto que desea modificar o eliminar:", lista_ids)
            
            # Convertimos el ID seleccionado a entero seguro
            id_seguro = int(id_seleccionado) if id_seleccionado is not None else 0
            
            # Extraemos los datos actuales de ese ID para precargarlos en el formulario de edición
            registro_actual = df_historial[df_historial["ID"] == id_seguro].iloc[0]
            
            # Creamos tres columnas para las opciones de edición
            col_mod, col_elim = st.columns(2)
            
            # --- BLOQUE DE MODIFICACIÓN ---
            with col_mod:
                st.write("**📝 Modificar Datos:**")
                with st.expander(f"Haga clic aquí para editar el ID {id_seguro}"):
                    conceptos_validos = [
                        "Viáticos (Comida/Hospedaje)", "Peajes", 
                        "Aseguramiento de Carga (Anime/Madera/Flejes)", 
                        "Imprevisto Mecánico Corto", "Otros Gastos de Ruta"
                    ]
                    
                    # Determinamos el índice por defecto de forma segura
                    concepto_actual = str(registro_actual["Concepto"])
                    idx_defecto = conceptos_validos.index(concepto_actual) if concepto_actual in conceptos_validos else 0

                    nuevo_concepto = st.selectbox(
                        "Concepto:", 
                        conceptos_validos,
                        index=idx_defecto
                    )
                    
                    # Aseguramos el casteo a float evitando nulos para Pylance
                    monto_actual_bs = float(registro_actual["Monto Bs"]) if pd.notnull(registro_actual["Monto Bs"]) else 0.0
                    nuevo_monto_bs = st.number_input("Monto en Bs.:", min_value=0.0, value=monto_actual_bs, step=10.0, key="edit_bs")
                    
                    nueva_ruta = st.text_input("Ruta:", value=str(registro_actual["Ruta"] if pd.notnull(registro_actual["Ruta"]) else ""), key="edit_ruta")
                    nuevas_obs = st.text_area("Detalle:", value=str(registro_actual["Detalle"] if pd.notnull(registro_actual["Detalle"]) else ""), key="edit_obs")
                    
                    if st.button("💾 Aplicar Cambios", use_container_width=True):
                        # Recalculamos el contravalor en dólares con la tasa original evitando división por cero o None
                        tasa_registro = float(registro_actual["Tasa BCV"]) if pd.notnull(registro_actual["Tasa BCV"]) else 1.0
                        nuevo_monto_usd = nuevo_monto_bs / tasa_registro if tasa_registro > 0 else 0.0
                        
                        try:
                            with obtener_conexion_db() as conexion:
                                with conexion.cursor() as cursor:
                                    query_update = """
                                        UPDATE gastos_operativos_viaje
                                        SET tipo_gasto = %s, monto_bs = %s, monto_usd = %s, estacion_origen_destino = %s, observaciones = %s
                                        WHERE id = %s
                                    """
                                    cursor.execute(query_update, (
                                        nuevo_concepto, 
                                        round(nuevo_monto_bs, 2), 
                                        round(nuevo_monto_usd, 2), 
                                        nueva_ruta, 
                                        nuevas_obs, 
                                        id_seguro
                                    ))
                                    conexion.commit()
                                    
                            st.success(f"🎉 ¡Gasto ID {id_seguro} actualizado con éxito!")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {e}")

            # --- BLOQUE DE ELIMINACIÓN ---
            with col_elim:
                st.write("**🗑️ Eliminar Registro:**")
                st.warning(f"¿Está seguro de que desea borrar por completo el registro ID {id_seguro}?")
                
                # Botón de confirmación forzada para evitar accidentes
                confirmar_borrado = st.checkbox(f"Sí, confirmo que deseo borrar el ID {id_seguro}")
                
                if st.button("❌ Eliminar Permanentemente", use_container_width=True, disabled=not confirmar_borrado):
                    try:
                        with obtener_conexion_db() as conexion:
                            with conexion.cursor() as cursor:
                                query_delete = "DELETE FROM gastos_operativos_viaje WHERE id = %s"
                                cursor.execute(query_delete, (id_seguro,))
                                conexion.commit()
                                
                        st.success(f"💥 Gasto ID {id_seguro} eliminado del libro contable.")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al eliminar: {e}")