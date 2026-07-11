import streamlit as st
import sqlite3
import pandas as pd
import time
from datetime import datetime

def mostrar_modulo_combustible():
    base_datos = 'exprex.db'

    # 🚀 1. BUSCAR LAS PLACAS Y CONDUCTORES DISPONIBLES EN LA BASE DE DATOS
    conexion = sqlite3.connect(base_datos)
    query_placas = """
        SELECT c.placa, u.nombre 
        FROM conductores c
        JOIN usuarios u ON c.cedula = u.cedula
        WHERE u.activo = 'Sí'
    """
    df_placas = pd.read_sql_query(query_placas, conexion)
    conexion.close()
    
    # Creamos la lista para el menú desplegable del registro
    if not df_placas.empty:
        opciones_placas = [f"{row['placa']} (Asignado a: {row['nombre']})" for index, row in df_placas.iterrows()]
        # Listas limpias y únicas para los filtros de búsqueda
        lista_placas_filtro = ["Todos"] + sorted(df_placas['placa'].unique().tolist())
        lista_choferes_filtro = ["Todos"] + sorted(df_placas['nombre'].unique().tolist())
    else:
        opciones_placas = ["No hay vehículos registrados"]
        lista_placas_filtro = ["Todos"]
        lista_choferes_filtro = ["Todos"]

    # 🚀 2. Recuperamos la tasa BCV automática del session_state
    tasa_bcv_sistema = st.session_state.get("tasa_bcv", 45.00)

    # Creamos dos pestañas: Registrar y Ver Historial
    tab_registrar, tab_historial = st.tabs(["📝 Registrar Carga", "📊 Historial de Consumo"])

    # ----------------------------------------------------
    # PESTAÑA 1: FORMULARIO DE REGISTRO
    # ----------------------------------------------------
    with tab_registrar:
        with st.form("form_combustible", clear_on_submit=True):
            st.write("### Registrar Nueva Carga de Gasolina")
            col1, col2 = st.columns(2)
            
            with col1:
                vehiculo_selected = st.selectbox("🚗 Seleccione el Vehículo / Placa:", opciones_placas)
                c_fecha = st.date_input("Fecha de la carga", datetime.now())
                c_km = st.number_input("Kilometraje Actual (Odómetro)", min_value=0, step=1)
                c_litros = st.number_input("Litros Comprados", min_value=0.0, step=0.1)
                
            with col2:
                monto_bs = st.number_input("Monto Total en Bolívares (Bs.)", min_value=0.0, step=10.0)
                
                c_costo_usd = monto_bs / tasa_bcv_sistema
                c_tasa = tasa_bcv_sistema
                
                st.number_input("Tasa BCV Aplicada (Fija)", value=c_tasa, disabled=True)
                c_estacion = st.text_input("Estación de Servicio (Nombre/Ubicación)")
                
                _, sub_col_centro, _ = st.columns([1, 2, 1])
                with sub_col_centro:
                    boton_gasolina = st.form_submit_button("Clic aquí para Registrar Combustible", use_container_width=True)
            
            st.info(f"📊 **Impacto en Costos:** Esta carga equivale a **{c_costo_usd:,.2f} USD** (Calculado automáticamente a {c_tasa:.2f} Bs.)")
            st.caption("💡 **Nota del Sistema:** Para cerrar esta ficha y limpiar la pantalla, simplemente seleccione otra opción en el menú de la izquierda o haga clic en **Inicio**.")    
            
            if boton_gasolina:
                if df_placas.empty or opciones_placas[0] == "No hay vehículos registrados":
                    st.error("❌ No se puede registrar combustible si no hay vehículos activos en el sistema.")
                elif c_km == 0 or c_litros == 0.0 or monto_bs == 0.0:
                    st.error("❌ Todos los campos numéricos (Km, Litros y Monto Bs.) deben ser mayores a cero.")
                else:
                    placa_limpia = vehiculo_selected.split(" ")[0]
                    
                    conexion = sqlite3.connect(base_datos)
                    cursor = conexion.cursor()
                    cursor.execute("SELECT cedula FROM conductores WHERE placa = ?", (placa_limpia,))
                    resultado_cedula = cursor.fetchone()
                    cedula_chofer = resultado_cedula[0] if resultado_cedula else "00000000"
                    
                    try:
                        cursor.execute("""
                            INSERT INTO control_combustible 
                            (cedula, fecha, km_actual, litros_comprados, costo_usd, tasa_cambio, costo_bs, estacion_servicio)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (cedula_chofer, str(c_fecha), c_km, c_litros, round(c_costo_usd, 2), c_tasa, round(monto_bs, 2), c_estacion))
                        
                        conexion.commit()
                        st.success(f"⛽ Carga guardada con éxito para la unidad **{placa_limpia}**. Total: {round(monto_bs, 2)} Bs.")
                        time.sleep(2)
                    except Exception as e:
                        st.error(f"Error al guardar en base de datos: {e}")
                    finally:
                        conexion.close()
                        st.rerun()

    # ----------------------------------------------------
    # PESTAÑA 2: HISTORIAL DE CARGAS (CON FILTROS AVANZADOS)
    # ----------------------------------------------------
    with tab_historial:
        st.write("### Historial General de Gastos de Combustible")
        
        # 📥 Extracción inicial de todo el universo de datos
        conexion = sqlite3.connect(base_datos)
        query_historial = """
            SELECT cc.fecha AS Fecha, c.placa AS Placa, u.nombre AS [Reportado Por], 
                   cc.km_actual AS [Km Odómetro], cc.litros_comprados AS Litros, 
                   cc.costo_usd AS [Costo $], cc.tasa_cambio AS [Tasa BCV], 
                   cc.costo_bs AS [Costo Bs], cc.estacion_servicio AS [Estación]
            FROM control_combustible cc
            JOIN usuarios u ON cc.cedula = u.cedula
            JOIN conductores c ON cc.cedula = c.cedula
            ORDER BY cc.fecha DESC
        """
        df_historial = pd.read_sql_query(query_historial, conexion)
        conexion.close()
        
        if df_historial.empty:
            st.info("No hay registros de combustible reportados hasta ahora.")
        else:
            # =================================================================
            # 🔍 BLOQUE DE HERRAMIENTAS DE FILTRADO (AUDITORÍA)
            # =================================================================
            with st.expander("🔍 Hacer Auditoría Específica (Filtrar por Período, Placa o Chofer)"):
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filtro_inicio = st.date_input("🗓️ Desde:", datetime.now().date().replace(day=1), key="f_comb_ini")
                    filtro_placa = st.selectbox("🚗 Filtrar por Unidad / Placa:", lista_placas_filtro, key="f_comb_placa")
                with col_f2:
                    filtro_fin = st.date_input("🗓️ Hasta:", datetime.now().date(), key="f_comb_fin")
                    filtro_chofer = st.selectbox("🧑‍✈️ Filtrar por Conductor:", lista_choferes_filtro, key="f_comb_chofer")
            
            # --- Proceso de filtrado dinámico en memoria con Pandas ---
            # 1. Filtro por Rango de Fechas
            df_historial['Fecha_dt'] = pd.to_datetime(df_historial['Fecha']).dt.date
            df_filtrado = df_historial[
                (df_historial['Fecha_dt'] >= filtro_inicio) & 
                (df_historial['Fecha_dt'] <= filtro_fin)
            ]
            
            # 2. Filtro por Placa
            if filtro_placa != "Todos":
                df_filtrado = df_filtrado[df_filtrado['Placa'] == filtro_placa]
                
            # 3. Filtro por Conductor
            if filtro_chofer != "Todos":
                df_filtrado = df_filtrado[df_filtrado['Reportado Por'] == filtro_chofer]
                
            # Borramos la columna auxiliar de fecha para no alterar la visualización de la tabla
            df_filtrado = df_filtrado.drop(columns=['Fecha_dt'])
            
            # =================================================================
            # 📊 SECCIÓN DE TOTALES DINÁMICOS RECALCULADOS
            # =================================================================
            total_litros = df_filtrado['Litros'].sum()
            total_usd = df_filtrado['Costo $'].sum()
            total_bs = df_filtrado['Costo Bs'].sum()
            
            m_litros, m_usd, m_bs = st.columns(3)
            with m_litros:
                st.metric(label="⛽ Volumen Surtido (Período)", value=f"{total_litros:,.1f} Ltrs")
            with m_usd:
                st.metric(label="💵 Gasto en Combustible (USD)", value=f"$ {total_usd:,.2f}")
            with m_bs:
                st.metric(label="🇻🇪 Gasto en Combustible (Bs)", value=f"{total_bs:,.2f} Bs")
                
            st.markdown("---")
            
            # Despliegue de la tabla según los filtros aplicados
            if df_filtrado.empty:
                st.warning("⚠️ No se encontraron cargas de combustible que coincidan con los filtros seleccionados.")
            else:
                st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
            
        st.info("💡 Clic en Inicio para volver atrás")