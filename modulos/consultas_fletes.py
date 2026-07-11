import streamlit as st
import sqlite3
import pandas as pd
import os

def mostrar_modulo_consultas():
    st.subheader("📊 Centro de Consultas y Auditoría de Servicios")
    #st.markdown("---")
    
    tab_general, tab_individual = st.tabs([
        "📋 Historial General (Cuentas)", 
        "🔍 Auditoría Individual (Detalle Extendido)"
    ])
    
    # =========================================================================
    # PESTAÑA 1: HISTORIAL GENERAL (VISTA DE PÁJARO Y FINANZAS)
    # =========================================================================
    with tab_general:
        st.write("### 🚛 Bitácora Consolidada de Fletes Liquidados")
        try:
            conexion = sqlite3.connect('exprex.db')
            # Traemos las nuevas columnas contables guardadas en piedra
            sql_general = """
                SELECT 
                    v.id_viaje AS 'ID Viaje',
                    v.fecha_despacho AS 'Fecha',
                    c.razon_social AS 'Cliente',
                    v.num_factura AS 'N° Factura',
                    v.num_pedido AS 'N° Pedido',
                    v.monto_flete_usd AS 'Total ($)',
                    v.descuento_usd AS 'Desc ($)',
                    v.importe_neto_usd AS 'Importe ($)',
                    v.pago_chofer_usd AS 'Chofer ($)',
                    v.beneficio_exprex_usd AS 'Beneficio ($)',
                    v.estatus_viaje AS 'Estatus'
                FROM viajes v
                JOIN clientes c ON v.id_cliente = c.id_cliente
                ORDER BY v.id_viaje DESC
            """
            df_gen = pd.read_sql_query(sql_general, conexion)
            conexion.close()
            
            if not df_gen.empty:
                # 📊 TARJETAS DE MÉTRICAS OPERATIVAS (Suman las columnas del DataFrame)
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Total Fletes", f"{len(df_gen)}")
                with m2:
                    total_facturado = df_gen['Total ($)'].sum()
                    st.metric("Facturación Bruta", f"$ {total_facturado:,.2f}")
                with m3:
                    total_choferes = df_gen['Chofer ($)'].sum()
                    st.metric("Total Choferes", f"$ {total_choferes:,.2f}", delta="- Nómina", delta_color="inverse")
                with m4:
                    total_beneficio = df_gen['Beneficio ($)'].sum()
                    st.metric("Utilidad ExpreX", f"$ {total_beneficio:,.2f}", delta="+ Neto", delta_color="normal")
                
                st.markdown("---")
                
                # Renderizamos la tabla con todas las columnas contables idénticas a tu Excel
                st.dataframe(df_gen, use_container_width=True, hide_index=True)
            else:
                st.info("💡 No se encontraron registros de fletes en la base de datos.")
        except Exception as e:
            st.error(f"Error en consulta general: {e}")

    # =========================================================================
    # PESTAÑA 2: CONSULTA INDIVIDUAL (EXPEDIENTE COMPLETO)
    # =========================================================================
    with tab_individual:
        st.write("### 🔍 Auditoría de Flete por ID")
        
        try:
            conexion = sqlite3.connect('exprex.db')
            df_ids = pd.read_sql_query("SELECT id_viaje FROM viajes ORDER BY id_viaje DESC", conexion)
            conexion.close()
        except:
            df_ids = pd.DataFrame()
            
        if df_ids.empty:
            st.info("No hay fletes disponibles para consulta individual.")
        else:
            id_seleccionado = st.selectbox(
                "Seleccione el ID del flete a inspeccionar:",
                options=df_ids['id_viaje'].tolist(),
                format_func=lambda x: f"Flete N° {x}"
            )
            
            st.markdown("---")
            
            try:
                conexion = sqlite3.connect('exprex.db')
                cursor = conexion.cursor()
                # Consulta extendida que extrae todo, incluyendo la contabilidad fija
                sql_individual = """
                    SELECT 
                        v.id_viaje, v.fecha_despacho, c.razon_social, c.rif,
                        u.nombre, v.cedula_conductor, v.origen, v.destino,
                        v.tipo_material, v.peso_carga_kg, v.distancia_km, v.monto_flete_usd,
                        v.num_pedido, v.num_factura, v.persona_contacto_entrega, v.telefono_contacto_entrega,
                        v.observaciones, v.estatus_viaje, v.foto_evidencia,
                        v.descuento_usd, v.importe_neto_usd, v.pago_chofer_usd, v.beneficio_exprex_usd
                    FROM viajes v
                    JOIN clientes c ON v.id_cliente = c.id_cliente
                    JOIN usuarios u ON v.cedula_conductor = u.cedula
                    WHERE v.id_viaje = ?
                """
                cursor.execute(sql_individual, (id_seleccionado,))
                flete = cursor.fetchone()
                conexion.close()
                
                if flete:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"### 📋 Información General")
                        st.write(f"**🗓️ Fecha:** {flete[1]}")
                        st.write(f"**🏢 Cliente:** {flete[2]} (RIF: {flete[3]})")
                        st.write(f"**🧾 Factura:** {flete[13]} | **📦 Pedido:** {flete[12]}")
                        st.write(f"**📍 Ruta:** {flete[6]} ➡️ {flete[7]}")
                        st.write(f"**🛣️ Distancia:** {flete[10]} Km | **⚖️ Peso:** {flete[9]} Kg")
                        st.write(f"**🪵 Material:** {flete[8]}")
                        st.write(f"**🚦 Estatus Actual:** `{flete[17]}`")
                    
                    with col2:
                        st.markdown("### 💰 Liquidación de Cuentas (Fijo)")
                        st.write(f"**Monto Flete Inicial (Total):** ${flete[11]:,.2f}")
                        st.write(f"**Descuento Comercial (15%):** ${flete[19]:,.2f}")
                        st.markdown(f"**Importe Neto:** `${flete[20]:,.2f}`")
                        st.write(f"**Pago al Transportista (Chofer):** ${flete[21]:,.2f}")
                        st.markdown(f"### 🟩 Beneficio ExpreX: ${flete[22]:,.2f}")
                        
                        st.markdown("---")
                        st.write(f"**🧑‍✈️ Conductor:** {flete[4]} (C.I. {flete[5]})")
                        st.write(f"**👤 Recibe:** {flete[14]} | **📞 Telf:** {flete[15]}")
                        st.write(f"**📝 Observaciones:** {flete[16] if flete[16] else 'Ninguna'}")
                    
                    st.markdown("---")
                    st.markdown("### 📸 Soporte Físico Digitalizado (Factura Firmada)")
                    
                    ruta_foto = flete[18]
                    if ruta_foto and os.path.exists(ruta_foto):
                        st.image(ruta_foto, caption=f"Evidencia fotográfica vinculada al Flete N° {id_seleccionado}", use_container_width=True)
                    else:
                        st.warning("⚠️ No se ha cargado soporte fotográfico para este flete o el archivo no se encuentra en el servidor.")
                        
            except Exception as e:
                st.error(f"Error al cargar el detalle del flete: {e}")