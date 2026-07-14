import streamlit as st
import sqlite3
import pandas as pd
import time

def renderizar_pestana_asignar(personal_base_datos='exprex.db'):
    st.write("### 📋 Cotización y Asignación Previa de Choferes")
    st.info("Consulte las solicitudes de los clientes, estime el kilometraje y pre-asigne un conductor antes del despacho definitivo.")

    # 1️⃣ Carga de datos crudos de la BD
    try:
        conexion = sqlite3.connect(personal_base_datos)
        df_choferes = pd.read_sql_query("SELECT cedula, nombre FROM usuarios WHERE rol = 'Conductor' AND activo = 'Sí'", conexion)
        
        # 🎯 AJUSTE DE COORDINACIÓN: Solo traemos solicitudes sin chofer asignado aún
        df_solicitudes = pd.read_sql_query('''
            SELECT id_viaje, cliente_solicitante, origen, destino, tipo_material, tipo_viaje, peso_carga_kg, observaciones 
            FROM viajes 
            WHERE estatus_viaje = 'Solicitado'
              AND cedula_conductor IS NULL  -- 🔑 Esto evita que se dupliquen con la pestaña de despacho
            ORDER BY CASE WHEN tipo_viaje = 'Express' THEN 1 ELSE 2 END, id_viaje DESC
        ''', conexion)
        conexion.close()
    except Exception as e:
        st.error(f"❌ Error de conexión al inicializar asignación: {e}")
        return

    # 2️⃣ Validación de bandejas vacías
    if df_choferes.empty:
        st.warning("⚠️ No hay conductores activos en el sistema para realizar asignaciones.")
        return
        
    if df_solicitudes.empty:
        st.success("✅ ¡Al día! No existen nuevas solicitudes pendientes por cotizar o asignar chofer.")
        return

    # 3️⃣ Construcción del Selector Seguro (Usa mapeo por diccionario para evitar fallas de Pandas)
    dicc_solicitudes = {}
    for idx, fila in df_solicitudes.iterrows():
        urgencia = "🚨 [EXPRESS]" if fila['tipo_viaje'] == 'Express' else "🕒 [Normal]"
        
        # Validamos si el id_viaje es None para que la visualización no se rompa
        id_v = fila['id_viaje']
        id_v_texto = str(id_v) if id_v is not None and str(id_v).strip() != "" else "S/N"
        
        info_texto = f"{urgencia} Flete N° {id_v_texto} - {fila['cliente_solicitante']} -> Destino: {fila['destino']}"
        
        # Usamos el ÍNDICE de la fila (idx) como CLAVE del selector para que NUNCA sea None
        dicc_solicitudes[idx] = info_texto

    lista_indices = list(dicc_solicitudes.keys())
    
    indice_seleccionado = st.selectbox(
        "🔍 Seleccione la solicitud que desea procesar:",
        options=lista_indices,
        format_func=lambda x: dicc_solicitudes.get(x, "Flete no identificado")
    )

    # 4️⃣ ESCUDO DEFENSIVO SEGURO: Extraemos la fila directamente usando el índice seleccionado
    if indice_seleccionado is not None and indice_seleccionado in df_solicitudes.index:
        fila_filtrada = df_solicitudes.loc[[indice_seleccionado]]
    else:
        fila_filtrada = pd.DataFrame() # Vacío si no hay selección válida
    
    if fila_filtrada.empty:
        st.warning("🔄 Sincronizando datos de la lista... Seleccione un flete de la lista.")
        return

    # A partir de aquí, cuando uses los datos de la solicitud, hazlo con la fila_filtrada:
    # Ejemplo: datos_viaje = fila_filtrada.iloc[0]

    # Si pasa el escudo, extraemos los datos de manera 100% segura
    viaje_sel = fila_filtrada.iloc[0]

    # 🎫 Tarjeta informativa limpia (HTML)
    st.markdown(f"""
    <div style="background-color:#1e1e1e; padding:15px; border-radius:8px; border-left: 5px solid {'#ff4b4b' if viaje_sel['tipo_viaje']=='Express' else '#3b82f6'};">
        <h4>📦 Detalles del Requerimiento del Cliente</h4>
        <table style="width:100%; border:none; color:#ffffff;">
            <tr><td><b>🏢 Solicitante:</b> {viaje_sel['cliente_solicitante']}</td><td><b>⚡ Servicio:</b> {viaje_sel['tipo_viaje']}</td></tr>
            <tr><td><b>📍 Origen:</b> {viaje_sel['origen']}</td><td><b>🏁 Destino Final:</b> {viaje_sel['destino']}</td></tr>
            <tr><td><b>⚖️ Peso Carga:</b> {viaje_sel['peso_carga_kg']} Kg</td><td><b>📦 Material:</b> {viaje_sel['tipo_material']}</td></tr>
        </table>
        <p style="margin-top:8px; margin-bottom:0; color:#b0b0b0;"><b>🗒️ Notas del Cliente:</b> <i>{viaje_sel['observaciones'] if viaje_sel['observaciones'] else 'Ninguna'}</i></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    # 5️⃣ Formulario aislado de recolección de datos operativos
    with st.form(f"form_core_asignar_{id_seleccionado}", clear_on_submit=False):
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            distancia_km = st.number_input("📏 Distancia Real Estimada (Km):", min_value=0.0, value=0.0, step=1.0)
        with col_in2:
            tipo_propiedad_vehiculo = st.radio("🚛 Tipo de Unidad de Carga:", options=["Tercero (Afiliado)", "Vehículo Propio"], index=0, horizontal=True)

        # 🧮 Simulación matemática en tiempo real para visualización en el formulario
        distancia_calculo = max(distancia_km, 8.0) if distancia_km > 0 else 0.0
        tarifa_por_km = 4.0 if viaje_sel['tipo_viaje'] == 'Express' else 2.5
        
        monto_flete_calculado = distancia_calculo * tarifa_por_km
        descuento_aplicado = monto_flete_calculado * 0.15
        importe_neto = monto_flete_calculado - descuento_aplicado
        
        porcentaje_chofer = 0.75 if tipo_propiedad_vehiculo == "Vehículo Propio" else 0.37
        pago_chofer_calculado = importe_neto * porcentaje_chofer
        beneficio_exprex = importe_neto - pago_chofer_calculado

        st.markdown("##### 📊 Proyección Financiera Estimada")
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric(label="💵 Flete Bruto Est.", value=f"${monto_flete_calculado:,.2f}")
        with col_m2:
            st.metric(label="🛡️ Importe Neto Est.", value=f"${importe_neto:,.2f}")
        with col_m3:
            st.metric(label="📈 Margen ExpreX Est.", value=f"${beneficio_exprex:,.2f}")

        st.markdown("---")
        
        # Selector de Choferes mapeado de forma segura
        # 1. Validamos que el DataFrame no esté vacío y tenga datos válidos
        if df_choferes is not None and not df_choferes.empty:
            # Creamos el diccionario asegurándonos de que no haya valores nulos en cédula o nombre
            dict_choferes = {
                str(row['cedula']): f"{row['nombre']} (C.I. {row['cedula']})" 
                for _, row in df_choferes.iterrows() 
                if row['cedula'] and row['nombre']
            }
        else:
            dict_choferes = {}

        # 2. Renderizamos el selector condicionalmente
        if dict_choferes:
            chofer_assigned = st.selectbox(
                "👤 Seleccione el Conductor a Asignar:",
                options=list(dict_choferes.keys()),
                format_func=lambda x: dict_choferes.get(x, "Chofer no identificado")
            )
        else:
            # Si está vacío, mostramos una advertencia y asignamos None de forma segura
            st.warning("⚠️ No se encontraron choferes registrados o disponibles en el sistema.")
            chofer_assigned = None

        boton_confirmar = st.form_submit_button("🚀 Registrar Pre-Asignación", use_container_width=True)
        
        if boton_confirmar:
            if distancia_km <= 0:
                st.error("❌ Error: Debe ingresar un kilometraje estimado válido de ruta para continuar.")
            else:
                try:
                    conexion = sqlite3.connect(personal_base_datos)
                    cursor = conexion.cursor()
                    
                    # 📝 UPDATE QUIRÚRGICO: Mantiene estatus 'Solicitado' intacto, pero inyecta los datos bases
                    cursor.execute('''
                        UPDATE viajes 
                        SET cedula_conductor = ?,
                            distancia_km = ?,
                            monto_flete_usd = ?,
                            estatus_viaje = 'Solicitado'
                        WHERE id_viaje = ?
                    ''', (chofer_assigned, distancia_km, monto_flete_calculado, id_seleccionado))
                    
                    conexion.commit()
                    conexion.close()
                    
                    st.success(f"🎉 ¡Flete N° {id_seleccionado} configurado! Conductor asignado y guardado en estatus Solicitado.")
                    time.sleep(1.2)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al procesar la actualización en la base de datos: {e}")