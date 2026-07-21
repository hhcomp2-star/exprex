import streamlit as st
import pandas as pd
import io
from datetime import datetime, date

# Importamos la conexión centralizada desde tus utilidades
from modulos.utils import obtener_conexion_db

def mostrar_modulo_reporte_general():
    ano = datetime.now().year
    st.title(f"📊 Control Financiero y Gerencial ExpreX - {ano}")

    # =========================================================================
    # EXTRACCIÓN DE DATOS CENTRALIZADA (POSTGRESQL)
    # =========================================================================
    df_viajes_empresa = pd.DataFrame(columns=["fecha_despacho", "monto_flete_usd", "descuento_usd", "pago_chofer_usd"])
    df_viajes_empresa['fecha_dt'] = pd.Series(dtype='datetime64[ns]')

    df_combustible = pd.DataFrame(columns=["fecha", "costo_usd"])
    df_combustible['fecha_dt'] = pd.Series(dtype='datetime64[ns]')

    df_gastos_op = pd.DataFrame(columns=["fecha", "tipo_gasto", "monto_usd"])
    df_gastos_op['fecha_dt'] = pd.Series(dtype='datetime64[ns]')

    df_gastos_gen = pd.DataFrame(columns=["fecha", "categoria", "monto_usd"])
    df_gastos_gen['fecha_dt'] = pd.Series(dtype='datetime64[ns]')

    try:
        with obtener_conexion_db() as conexion:
            # A. Leer Viajes
            with conexion.cursor() as cursor:
                cursor.execute("SELECT fecha_despacho, monto_flete_usd, descuento_usd, pago_chofer_usd FROM viajes")
                filas = cursor.fetchall()
                if cursor.description:
                    df_viajes_empresa = pd.DataFrame(filas, columns=[desc[0] for desc in cursor.description])
                    df_viajes_empresa['fecha_dt'] = pd.to_datetime(df_viajes_empresa['fecha_despacho'])
                    # 💡 CONVERSIÓN A FLOAT PARA EVITAR ERROR CON DECIMAL
                    for col in ["monto_flete_usd", "descuento_usd", "pago_chofer_usd"]:
                        if col in df_viajes_empresa.columns:
                            df_viajes_empresa[col] = df_viajes_empresa[col].astype(float).fillna(0.0)

            # B. Leer Combustible
            with conexion.cursor() as cursor:
                cursor.execute("SELECT fecha, costo_usd FROM control_combustible")
                filas = cursor.fetchall()
                if cursor.description:
                    df_combustible = pd.DataFrame(filas, columns=[desc[0] for desc in cursor.description])
                    df_combustible['fecha_dt'] = pd.to_datetime(df_combustible['fecha'])
                    if "costo_usd" in df_combustible.columns:
                        df_combustible["costo_usd"] = df_combustible["costo_usd"].astype(float).fillna(0.0)

            # C. Leer Gastos Operativos de Viaje
            with conexion.cursor() as cursor:
                cursor.execute("SELECT fecha, tipo_gasto, monto_usd FROM gastos_operativos_viaje")
                filas = cursor.fetchall()
                if cursor.description:
                    df_gastos_op = pd.DataFrame(filas, columns=[desc[0] for desc in cursor.description])
                    df_gastos_op['fecha_dt'] = pd.to_datetime(df_gastos_op['fecha'])
                    if "monto_usd" in df_gastos_op.columns:
                        df_gastos_op["monto_usd"] = df_gastos_op["monto_usd"].astype(float).fillna(0.0)

            # D. Leer Gastos Generales
            with conexion.cursor() as cursor:
                cursor.execute("SELECT fecha, categoria, monto_usd FROM gastos")
                filas = cursor.fetchall()
                if cursor.description:
                    df_gastos_gen = pd.DataFrame(filas, columns=[desc[0] for desc in cursor.description])
                    df_gastos_gen['fecha_dt'] = pd.to_datetime(df_gastos_gen['fecha'])
                    if "monto_usd" in df_gastos_gen.columns:
                        df_gastos_gen["monto_usd"] = df_gastos_gen["monto_usd"].astype(float).fillna(0.0)

    except Exception as e:
        st.error(f"Error al extraer los datos de PostgreSQL: {e}")

    # =========================================================================
    # CREACIÓN DE PESTAÑAS (TABS) EN STREAMLIT
    # =========================================================================
    tab_flujo_caja, tab_kpis_gerenciales = st.tabs([
        "📋 Flujo de Caja Mensual", 
        "🏛️ Indicadores Gerenciales (KPIs)"
    ])

    # -------------------------------------------------------------------------
    # PESTAÑA 1: FLUJO DE CAJA MENSUAL Y CONSULTA RÁPIDA
    # -------------------------------------------------------------------------
    with tab_flujo_caja:
        st.write(f"### 💵 Flujo de Caja Matriz Anual - Año {ano}")

        meses_abreviados = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
        matriz_ingresos = pd.DataFrame(0.0, index=meses_abreviados, columns=["Servicios", "Otr Ing.", "Total Ingresos"])
        columnas_egresos = ["Descuento", "Sueldo", "Pago Chofer", "Viáticos", "Combustible", "Estacionam.", "Mantenim.", 
                            "Multas", "Grúas", "Seguros", "GPS", "Impuestos", "Gtos Varios", "Total Egresos"]
        matriz_egresos = pd.DataFrame(0.0, index=meses_abreviados, columns=columnas_egresos)

        # Llenado Fletes
        for _, fila in df_viajes_empresa.iterrows():
            try:
                if pd.notnull(fila['fecha_dt']):
                    mes_txt = meses_abreviados[fila['fecha_dt'].month - 1]
                    matriz_ingresos.at[mes_txt, "Servicios"] += float(fila['monto_flete_usd'])
                    if pd.notnull(fila['descuento_usd']):
                        matriz_egresos.at[mes_txt, "Descuento"] += float(fila['descuento_usd'])
                    if pd.notnull(fila['pago_chofer_usd']):
                        matriz_egresos.at[mes_txt, "Pago Chofer"] += float(fila['pago_chofer_usd'])
            except Exception:
                continue

        # Llenado Combustible
        for _, fila in df_combustible.iterrows():
            try:
                if pd.notnull(fila['fecha_dt']):
                    mes_txt = meses_abreviados[fila['fecha_dt'].month - 1]
                    matriz_egresos.at[mes_txt, "Combustible"] += float(fila['costo_usd'])
            except Exception:
                continue

        # Llenado Gastos Operativos
        for _, fila in df_gastos_op.iterrows():
            try:
                if pd.notnull(fila['fecha_dt']):
                    mes_txt = meses_abreviados[fila['fecha_dt'].month - 1]
                    concepto, monto = str(fila['tipo_gasto']), float(fila['monto_usd'])
                    if "Viáticos" in concepto: 
                        matriz_egresos.at[mes_txt, "Viáticos"] += monto
                    elif "Peajes" in concepto: 
                        matriz_egresos.at[mes_txt, "Estacionam."] += monto
                    elif "Mecánico" in concepto or "Imprevisto" in concepto: 
                        matriz_egresos.at[mes_txt, "Mantenim."] += monto
                    elif "Aseguramiento" in concepto: 
                        matriz_egresos.at[mes_txt, "Seguros"] += monto
                    else: 
                        matriz_egresos.at[mes_txt, "Gtos Varios"] += monto
            except Exception:
                continue

        # Llenado Gastos Generales
        for _, fila in df_gastos_gen.iterrows():
            try:
                if pd.notnull(fila['fecha_dt']):
                    mes_txt = meses_abreviados[fila['fecha_dt'].month - 1]
                    cat, monto = str(fila['categoria']).strip(), float(fila['monto_usd'])
                    if cat == "Estacionamiento": 
                        matriz_egresos.at[mes_txt, "Estacionam."] += monto
                    elif cat == "Mantenimiento": 
                        matriz_egresos.at[mes_txt, "Mantenim."] += monto
                    elif cat == "Seguros": 
                        matriz_egresos.at[mes_txt, "Seguros"] += monto
                    elif cat == "Impuestos": 
                        matriz_egresos.at[mes_txt, "Impuestos"] += monto
                    elif cat == "Grúas": 
                        matriz_egresos.at[mes_txt, "Grúas"] += monto
                    elif cat == "Multas": 
                        matriz_egresos.at[mes_txt, "Multas"] += monto
                    else: 
                        matriz_egresos.at[mes_txt, "Gtos Varios"] += monto
            except Exception:
                continue

        matriz_ingresos["Total Ingresos"] = matriz_ingresos["Servicios"] + matriz_ingresos["Otr Ing."]
        matriz_egresos["Total Egresos"] = matriz_egresos.iloc[:, :-1].sum(axis=1)

        matriz_resumen = pd.DataFrame(index=meses_abreviados, columns=["Ingresos", "Egresos", "Saldos", "Márgenes"])
        matriz_resumen["Ingresos"] = matriz_ingresos["Total Ingresos"]
        matriz_resumen["Egresos"] = matriz_egresos["Total Egresos"]
        matriz_resumen["Saldos"] = matriz_resumen["Ingresos"] - matriz_resumen["Egresos"]
        matriz_resumen["Márgenes"] = matriz_resumen.apply(
            lambda r: f"{(float(r['Saldos']) / float(r['Ingresos']) * 100.0):,.2f} %" if float(r['Ingresos']) > 0 else "0,00 %", 
            axis=1
        )

        matriz_ingresos.loc["Totales"] = matriz_ingresos.sum()
        matriz_egresos.loc["Totales"] = matriz_egresos.sum()
        
        tot_ing = float(matriz_resumen["Ingresos"].sum())
        tot_egr = float(matriz_resumen["Egresos"].sum())
        tot_sal = tot_ing - tot_egr

        totales_res = pd.Series({
            "Ingresos": tot_ing, 
            "Egresos": tot_egr, 
            "Saldos": tot_sal
        }, name="Totales")
        totales_res["Márgenes"] = f"{(tot_sal / tot_ing * 100.0):,.2f} %" if tot_ing > 0 else "0,00 %"
        matriz_resumen.loc["Totales"] = totales_res

        def mapear_moneda(df):
            return df.applymap(lambda x: f"$ {float(x):,.2f}" if isinstance(x, (int, float)) else x)

        st.write("##### 🟢 Bloque de Ingresos")
        st.dataframe(mapear_moneda(matriz_ingresos), use_container_width=True)

        st.write("##### 🔴 Bloque de Egresos")
        st.dataframe(mapear_moneda(matriz_egresos), use_container_width=True)

        col_izq, col_der = st.columns([2, 1])
        with col_izq: 
            st.write("##### 🔵 Resumen de Totales y Márgenes Anuales")
        with col_der:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                matriz_ingresos.to_excel(writer, sheet_name='Ingresos')
                matriz_egresos.to_excel(writer, sheet_name='Egresos')
                matriz_resumen.to_excel(writer, sheet_name='Resumen_Saldos')
            buffer.seek(0)
            st.download_button(
                label="📥 Exportar Matrices a Calc", 
                data=buffer, 
                file_name=f"flujo_caja_exprex_{ano}.xlsx", 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )

        st.dataframe(mapear_moneda(matriz_resumen), use_container_width=True)

        # Consulta Rápida por Fechas dentro de la Pestaña 1
        st.markdown("---")
        st.write("### 🔍 Consulta Rápida por Rango de Fechas")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_inicio = st.date_input("Desde:", date(ano, 1, 1), key="f_ini_t1")
        with col_f2:
            fecha_fin = st.date_input("Hasta:", date.today(), key="f_fin_t1")
            
        if fecha_inicio <= fecha_fin:
            t_inicio = pd.to_datetime(fecha_inicio)
            t_fin = pd.to_datetime(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            
            ingresos_r = float(df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_inicio) & (df_viajes_empresa['fecha_dt'] <= t_fin)]['monto_flete_usd'].sum())
            egreso_desc_r = float(df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_inicio) & (df_viajes_empresa['fecha_dt'] <= t_fin)]['descuento_usd'].sum())
            egreso_chof_r = float(df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_inicio) & (df_viajes_empresa['fecha_dt'] <= t_fin)]['pago_chofer_usd'].sum())
            egreso_comb_r = float(df_combustible[(df_combustible['fecha_dt'] >= t_inicio) & (df_combustible['fecha_dt'] <= t_fin)]['costo_usd'].sum())
            egreso_op_r = float(df_gastos_op[(df_gastos_op['fecha_dt'] >= t_inicio) & (df_gastos_op['fecha_dt'] <= t_fin)]['monto_usd'].sum())
            egreso_gen_r = float(df_gastos_gen[(df_gastos_gen['fecha_dt'] >= t_inicio) & (df_gastos_gen['fecha_dt'] <= t_fin)]['monto_usd'].sum())
            
            egresos_tot_r = egreso_chof_r + egreso_comb_r + egreso_op_r + egreso_gen_r + egreso_desc_r
            saldo_r = ingresos_r - egresos_tot_r
            margen_r = (saldo_r / ingresos_r * 100.0) if ingresos_r > 0 else 0.0
            
            df_rango_resumen = pd.DataFrame({
                "Métricas": ["Monto Total ($)"],
                "Ingresos Totales": [ingresos_r],
                "Egresos Totales": [egresos_tot_r],
                "Saldo Neto": [saldo_r],
                "Margen Comercial": [f"{margen_r:,.2f} %"]
            }).set_index("Métricas")
            
            st.dataframe(df_rango_resumen.applymap(lambda v: f"$ {float(v):,.2f}" if isinstance(v, (int, float)) else v), use_container_width=True)
        else:
            st.error("Error: La fecha de inicio no puede ser mayor que la fecha final.")

    # -------------------------------------------------------------------------
    # PESTAÑA 2: INDICADORES FINANCIEROS Y GERENCIALES (KPIs)
    # -------------------------------------------------------------------------
    with tab_kpis_gerenciales:
        st.write("### 🏛️ Rendimiento de Capital y Análisis Financiero")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            f_ini_kpi = st.date_input("Período Desde:", date(ano, 1, 1), key="f_ini_t2")
        with col_g2:
            f_fin_kpi = st.date_input("Período Hasta:", date.today(), key="f_fin_t2")

        with st.expander("⚙️ Configuración de Capital Invertido y Patrimonio (Insumos)"):
            c_inv1, c_inv2 = st.columns(2)
            with c_inv1:
                inversion_inicial = float(st.number_input("Inversión Inicial Total ($)", value=1000.0, step=100.0))
            with c_inv2:
                patrimonio_propio = float(st.number_input("Capital Propio / Patrimonio ($)", value=1000.0, step=100.0))

        if f_ini_kpi <= f_fin_kpi:
            t_ini_k = pd.to_datetime(f_ini_kpi)
            t_fin_k = pd.to_datetime(f_fin_kpi) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

            ing_k = float(df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_ini_k) & (df_viajes_empresa['fecha_dt'] <= t_fin_k)]['monto_flete_usd'].sum())
            pago_chof_k = float(df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_ini_k) & (df_viajes_empresa['fecha_dt'] <= t_fin_k)]['pago_chofer_usd'].sum())
            comb_k = float(df_combustible[(df_combustible['fecha_dt'] >= t_ini_k) & (df_combustible['fecha_dt'] <= t_fin_k)]['costo_usd'].sum())
            g_op_k = float(df_gastos_op[(df_gastos_op['fecha_dt'] >= t_ini_k) & (df_gastos_op['fecha_dt'] <= t_fin_k)]['monto_usd'].sum())
            g_gen_k = float(df_gastos_gen[(df_gastos_gen['fecha_dt'] >= t_ini_k) & (df_gastos_gen['fecha_dt'] <= t_fin_k)]['monto_usd'].sum())
            desc_k = float(df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_ini_k) & (df_viajes_empresa['fecha_dt'] <= t_fin_k)]['descuento_usd'].sum())

            # Cálculos Gerenciales garantizados como float
            egresos_directos = pago_chof_k + comb_k + g_op_k
            ebitda = ing_k - egresos_directos
            
            utilidad_neta = ebitda - (g_gen_k + desc_k)
            
            margen_bruto_pct = (ebitda / ing_k * 100.0) if ing_k > 0 else 0.0
            margen_neto_pct = (utilidad_neta / ing_k * 100.0) if ing_k > 0 else 0.0
            
            roi_pct = (utilidad_neta / inversion_inicial * 100.0) if inversion_inicial > 0 else 0.0
            roe_pct = (utilidad_neta / patrimonio_propio * 100.0) if patrimonio_propio > 0 else 0.0

            dias_evaluados = max((t_fin_k - t_ini_k).days, 1)
            meses_evaluados = float(dias_evaluados) / 30.0
            ganancia_promedio_mensual = utilidad_neta / meses_evaluados if meses_evaluados > 0 else 0.0
            
            meses_payback = (inversion_inicial / ganancia_promedio_mensual) if ganancia_promedio_mensual > 0 else 0.0

            st.markdown("---")
            st.subheader("📈 Cuadro de Mando Financiero")

            k1, k2, k3 = st.columns(3)
            k1.metric("EBITDA (Ganancia Operativa)", f"$ {ebitda:,.2f}")
            k2.metric("Margen Bruto", f"{margen_bruto_pct:.2f} %")
            k3.metric("Margen Neto", f"{margen_neto_pct:.2f} %")

            st.markdown(" ")

            k4, k5, k6 = st.columns(3)
            k4.metric("ROI (Retorno s/ Inversión)", f"{roi_pct:.2f} %")
            k5.metric("ROE (Retorno s/ Patrimonio)", f"{roe_pct:.2f} %")
            
            if meses_payback > 0:
                k6.metric("Tiempo de Recuperación", f"{meses_payback:.1f} Meses")
            else:
                k6.metric("Tiempo de Recuperación", "N/D (Sin Ganancia Neta)")
        else:
            st.error("Error: La fecha de inicio no puede ser mayor que la fecha final.")