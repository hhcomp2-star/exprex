import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import datetime, date

def mostrar_modulo_reporte_general():
# -------------------------------------------------------------------------------------------------------------------------------
    # 1.Para indicar el período traemos el año actual del reloj del sistema (2026)
    from datetime import datetime
    ano = datetime.now().year
    
    # 2. Ahora que 'ano' existe, lo pintamos sin errores
    st.write(f"### 📊 Flujo de Caja Mensual - Año {ano}")

# -------------------------------------------------------------------------------------------------------------------------------    
    # 1. CONEXIÓN A BASE DE DATOS Y EXTRACCIÓN DE DATOS REALES
    conexion = sqlite3.connect('exprex.db')
    
    # A. Leer Viajes (Ingresos de fletes Descuentos 15% y Pagos a los Choferes)
    try:
        df_viajes_empresa = pd.read_sql_query("SELECT fecha_despacho, monto_flete_usd, descuento_usd, pago_chofer_usd FROM viajes", conexion)
        df_viajes_empresa['fecha_dt'] = pd.to_datetime(df_viajes_empresa['fecha_despacho'])
    except:
        df_viajes_empresa = pd.DataFrame(columns=["fecha_despacho", "monto_flete_usd", "descuento_usd", "pago_chofer_usd"])
        df_viajes_empresa['fecha_dt'] = pd.Series(dtype='datetime64[ns]')
        
    # B. Leer Egresos de Combustible
    try:
        df_combustible = pd.read_sql_query("SELECT fecha, costo_usd FROM control_combustible", conexion)
        df_combustible['fecha_dt'] = pd.to_datetime(df_combustible['fecha'])
    except:
        df_combustible = pd.DataFrame(columns=["fecha", "costo_usd"])
        df_combustible['fecha_dt'] = pd.Series(dtype='datetime64[ns]')
        
    # C. Leer Egresos Operativos de Viaje
    try:
        df_gastos_op = pd.read_sql_query("SELECT fecha, tipo_gasto, monto_usd FROM gastos_operativos_viaje", conexion)
        df_gastos_op['fecha_dt'] = pd.to_datetime(df_gastos_op['fecha'])
    except:
        df_gastos_op = pd.DataFrame(columns=["fecha", "tipo_gasto", "monto_usd"])
        df_gastos_op['fecha_dt'] = pd.Series(dtype='datetime64[ns]')

    # D. Leer Gastos Generales
    try:
        df_gastos_gen = pd.read_sql_query("SELECT fecha, categoria, monto_usd FROM gastos", conexion)
        df_gastos_gen['fecha_dt'] = pd.to_datetime(df_gastos_gen['fecha'])
    except:
        df_gastos_gen = pd.DataFrame(columns=["fecha", "categoria", "monto_usd"])
        df_gastos_gen['fecha_dt'] = pd.Series(dtype='datetime64[ns]')
        
    conexion.close()

    # 2. PROCESAMIENTO MATRIZ ANUAL (TABLAS SUPERIORES)
    meses_abreviados = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    matriz_ingresos = pd.DataFrame(0.0, index=meses_abreviados, columns=["Servicios", "Otr Ing.", "Total Ingresos"])
    columnas_egresos = ["Descuento", "Sueldo", "Pago Chofer", "Viáticos", "Combustible", "Estacionam.", "Mantenim.", 
                        "Multas", "Grúas", "Seguros", "GPS", "Impuestos", "Gtos Varios", "Total Egresos"]
    matriz_egresos = pd.DataFrame(0.0, index=meses_abreviados, columns=columnas_egresos)

    # LLenado de Matriz anual (Descunto de fletes)


    # Llenado de matriz anual (Fletes)
    for _, fila in df_viajes_empresa.iterrows():
        try:
            if pd.notnull(fila['fecha_dt']):
                mes_txt = meses_abreviados[fila['fecha_dt'].month - 1]
                matriz_ingresos.at[mes_txt, "Servicios"] += float(fila['monto_flete_usd'])
                if pd.notnull(fila['descuento_usd']):
                    matriz_egresos.at[mes_txt, "Descuento"] += float(fila['descuento_usd'])
                if pd.notnull(fila['pago_chofer_usd']):
                    matriz_egresos.at[mes_txt, "Pago Chofer"] += float(fila['pago_chofer_usd'])
        except: continue

    # Llenado de matriz anual (Combustible)
    for _, fila in df_combustible.iterrows():
        try:
            if pd.notnull(fila['fecha_dt']):
                mes_txt = meses_abreviados[fila['fecha_dt'].month - 1]
                matriz_egresos.at[mes_txt, "Combustible"] += float(fila['costo_usd'])
        except: continue

    # Llenado de matriz anual (Gastos de Viaje)
    for _, fila in df_gastos_op.iterrows():
        try:
            if pd.notnull(fila['fecha_dt']):
                mes_txt = meses_abreviados[fila['fecha_dt'].month - 1]
                concepto, monto = fila['tipo_gasto'], float(fila['monto_usd'])
                if "Viáticos" in concepto: matriz_egresos.at[mes_txt, "Viáticos"] += monto
                elif "Peajes" in concepto: matriz_egresos.at[mes_txt, "Estacionam."] += monto
                elif "Mecánico" in concepto or "Imprevisto" in concepto: matriz_egresos.at[mes_txt, "Mantenim."] += monto
                elif "Aseguramiento" in concepto: matriz_egresos.at[mes_txt, "Seguros"] += monto
                else: matriz_egresos.at[mes_txt, "Gtos Varios"] += monto
        except: continue

    # Llenado de matriz anual (Gastos Generales)
    for _, fila in df_gastos_gen.iterrows():
        try:
            if pd.notnull(fila['fecha_dt']):
                mes_txt = meses_abreviados[fila['fecha_dt'].month - 1]
                cat, monto = str(fila['categoria']).strip(), float(fila['monto_usd'])
                if cat == "Estacionamiento": matriz_egresos.at[mes_txt, "Estacionam."] += monto
                elif cat == "Mantenimiento": matriz_egresos.at[mes_txt, "Mantenim."] += monto
                elif cat == "Seguros": matriz_egresos.at[mes_txt, "Seguros"] += monto
                elif cat == "Impuestos": matriz_egresos.at[mes_txt, "Impuestos"] += monto
                elif cat == "Grúas": matriz_egresos.at[mes_txt, "Grúas"] += monto
                elif cat == "Multas": matriz_egresos.at[mes_txt, "Multas"] += monto
                else: matriz_egresos.at[mes_txt, "Gtos Varios"] += monto
        except: continue

    # Totales Matriz Anual
    matriz_ingresos["Total Ingresos"] = matriz_ingresos["Servicios"] + matriz_ingresos["Otr Ing."]
    matriz_egresos["Total Egresos"] = matriz_egresos.iloc[:, :-1].sum(axis=1)

    matriz_resumen = pd.DataFrame(index=meses_abreviados, columns=["Ingresos", "Egresos", "Saldos", "Márgenes"])
    matriz_resumen["Ingresos"] = matriz_ingresos["Total Ingresos"]
    matriz_resumen["Egresos"] = matriz_egresos["Total Egresos"]
    matriz_resumen["Saldos"] = matriz_resumen["Ingresos"] - matriz_resumen["Egresos"]
    matriz_resumen["Márgenes"] = matriz_resumen.apply(lambda r: f"{(r['Saldos'] / r['Ingresos'] * 100):,.2f} %" if r['Ingresos'] > 0 else "0,00 %", axis=1)

    # Agregar filas de Totales
    matriz_ingresos.loc["Totales"] = matriz_ingresos.sum()
    matriz_egresos.loc["Totales"] = matriz_egresos.sum()
    
    totales_res = pd.Series({"Ingresos": matriz_resumen["Ingresos"].sum(), "Egresos": matriz_resumen["Egresos"].sum(), "Saldos": matriz_resumen["Ingresos"].sum() - matriz_resumen["Egresos"].sum()}, name="Totales")
    totales_res["Márgenes"] = f"{(totales_res['Saldos'] / totales_res['Ingresos'] * 100):,.2f} %" if totales_res["Ingresos"] > 0 else "0,00 %"
    matriz_resumen.loc["Totales"] = totales_res

    def mapear_moneda(df):
        return df.map(lambda x: f"$ {x:,.2f}" if isinstance(x, (int, float)) else x)

    # RENDERIZADO TABLAS ANUALES
    st.write("##### 🟢 Bloque de Ingresos")
    st.dataframe(mapear_moneda(matriz_ingresos), use_container_width=True)

    st.write("##### 🔴 Bloque de Egresos")
    st.dataframe(mapear_moneda(matriz_egresos), use_container_width=True)

    col_izq, col_der = st.columns([2, 1])
    with col_izq: st.write("##### 🔵 Resumen de Totales y Márgenes Anuales")
    with col_der:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            matriz_ingresos.to_excel(writer, sheet_name='Ingresos')
            matriz_egresos.to_excel(writer, sheet_name='Egresos')
            matriz_resumen.to_excel(writer, sheet_name='Resumen_Saldos')
        buffer.seek(0)
        st.download_button(label="📥 Exportar Matrices a Calc", data=buffer, file_name="flujo_caja_exprex_2026.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.dataframe(mapear_moneda(matriz_resumen), use_container_width=True)

    # =========================================================================
    # 🛠️ NUEVA PARTE BAJA: RESUMEN POR RANGO DE FECHAS (FILTRO DINÁMICO)
    # =========================================================================
    st.markdown("---")
    st.write("### 🔍 Consulta Rápida por Rango de Fechas")
    
    # Selectores dinámicos alineados en columnas
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_inicio = st.date_input("Desde:", date(2026, 1, 1))
    with col_f2:
        fecha_fin = st.date_input("Hasta:", date.today())
        
    if fecha_inicio <= fecha_fin:
        # Convertimos las entradas de streamlit a formato Timestamp para comparar con Pandas
        t_inicio = pd.to_datetime(fecha_inicio)
        t_fin = pd.to_datetime(fecha_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) # Incluir el día completo
        
        # Filtrado inteligente con Pandas aplicando las máscaras de fecha
        ingresos_rango = df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_inicio) & (df_viajes_empresa['fecha_dt'] <= t_fin)]['monto_flete_usd'].sum()
       
        egreso_descuento_rango = df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_inicio) & (df_viajes_empresa['fecha_dt'] <= t_fin)]['descuento_usd'].sum()
        egreso_chofer_rango = df_viajes_empresa[(df_viajes_empresa['fecha_dt'] >= t_inicio) & (df_viajes_empresa['fecha_dt'] <= t_fin)]['pago_chofer_usd'].sum()
        egreso_comb_rango = df_combustible[(df_combustible['fecha_dt'] >= t_inicio) & (df_combustible['fecha_dt'] <= t_fin)]['costo_usd'].sum()
        egreso_op_rango = df_gastos_op[(df_gastos_op['fecha_dt'] >= t_inicio) & (df_gastos_op['fecha_dt'] <= t_fin)]['monto_usd'].sum()
        egreso_gen_rango = df_gastos_gen[(df_gastos_gen['fecha_dt'] >= t_inicio) & (df_gastos_gen['fecha_dt'] <= t_fin)]['monto_usd'].sum()
        
        # Consolidación final de egresos
        egresos_totales_rango = egreso_chofer_rango + egreso_comb_rango + egreso_op_rango + egreso_gen_rango + egreso_descuento_rango
        saldo_rango = ingresos_rango - egresos_totales_rango
        
        # Margen % del rango
        margen_rango = (saldo_rango / ingresos_rango * 100) if ingresos_rango > 0 else 0.0
        
        # Armamos un mini DataFrame horizontal estético para mostrarlo limpio
        df_rango_resumen = pd.DataFrame({
            "Métricas": ["Monto Total ($)"],
            "Ingresos Totales": [ingresos_rango],
            "Egresos Totales": [egresos_totales_rango],
            "Saldo Neto": [saldo_rango],
            "Margen Comercial": [f"{margen_rango:,.2f} %"]
        }).set_index("Métricas")
        
        # Renderizado del cuadro de control final
        def mapear_moneda_rango(val):
            if isinstance(val, (int, float)):
                return f"$ {val:,.2f}"
            return val
            
        st.dataframe(df_rango_resumen.map(mapear_moneda_rango), use_container_width=True)
    else:
        st.error("Error: La fecha de inicio ('Desde') no puede ser mayor que la fecha final ('Hasta').")