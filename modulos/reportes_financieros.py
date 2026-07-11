import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

def mostrar_modulo_reportes():
    st.write("### 📊 Tablero de Control y Distribución de Ingresos")
#    st.write("### Tablero de Control y Distribución de Ingresos")
#    st.markdown("---")
    
    # =========================================================================
    # 🗓️ FILTRO DE FECHAS (PERÍODO)
    # =========================================================================
    st.write("#### 🔍 Filtrar Período de Análisis")
    col_f1, col_f2 = st.columns(2)
    
    hoy = datetime.now().date()
    primer_dia_mes = hoy.replace(day=1)
    
    with col_f1:
        fecha_inicio = st.date_input("🗓️ Fecha Inicial:", primer_dia_mes)
    with col_f2:
        fecha_fin = st.date_input("🗓️ Fecha Final:", hoy)
        
    if fecha_inicio > fecha_fin:
        st.error("❌ La fecha inicial no puede ser mayor que la fecha final.")
        return

    st.markdown("---")

    f_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    f_fin_str = fecha_fin.strftime("%Y-%m-%d")

    # =========================================================================
    # 💾 PROCESAMIENTO DE DATOS EN BD (Combustible Incluido)
    # =========================================================================
    try:
        conexion = sqlite3.connect('exprex.db')
        cursor = conexion.cursor()
        
        # 1. Ingresos por servicios
        sql_viajes = "SELECT SUM(beneficio_exprex_usd) FROM viajes WHERE (estatus_viaje = 'Entregado' OR estatus_viaje = 'Completado') AND fecha_despacho BETWEEN ? AND ?"
        cursor.execute(sql_viajes, (f_inicio_str, f_fin_str))
        total_servicios = cursor.fetchone()[0]
        total_servicios = float(total_servicios) if total_servicios else 0.0
        
        # 2. Gastos operativos comunes (Tabla gastos)
        sql_gastos = "SELECT SUM(monto_usd) FROM gastos WHERE fecha BETWEEN ? AND ?"
        cursor.execute(sql_gastos, (f_inicio_str, f_fin_str))
        total_gastos = cursor.fetchone()[0]
        total_gastos = float(total_gastos) if total_gastos else 0.0
        
        # 3. ⛽ NUEVO: Consumo de combustible acumulado en el período
        sql_combustible = "SELECT SUM(costo_usd) FROM control_combustible WHERE fecha BETWEEN ? AND ?"
        cursor.execute(sql_combustible, (f_inicio_str, f_fin_str))
        total_combustible = cursor.fetchone()[0]
        total_combustible = float(total_combustible) if total_combustible else 0.0

        # 4. Gastos operativos en Viaje (Tabla gastos_operativos_viaje).
        sql_gastos_viaje = "SELECT SUM(monto_usd) FROM gastos_operativos_viaje WHERE fecha BETWEEN ? AND ?"
        cursor.execute(sql_gastos_viaje, (f_inicio_str, f_fin_str))
        total_gastos_viaje = cursor.fetchone()[0]
        total_gastos_viaje = float(total_gastos_viaje) if total_gastos_viaje else 0.0

        conexion.close()
    except Exception as e:
        st.error(f"Error al conectar a la base de datos: {e}")
        return

    # Matemática Financiera Central (Ajustada con Egreso Real)
    otros_ingresos = 0.0  
    total_ingresos = total_servicios + otros_ingresos
    
    # El egreso real es la suma de los gastos administrativos/talleres + el combustible surtido
    total_egresos_reales = total_gastos + total_combustible + total_gastos_viaje
    resultado_operacion = total_ingresos - total_egresos_reales

    # Distribución porcentual basada en la utilidad real
    junta_directiva = resultado_operacion * 0.74
    provision = resultado_operacion * 0.20
    administracion = resultado_operacion * 0.05
    ahorro = resultado_operacion * 0.01

    # =========================================================================
    # 📊 RENDERIZADO DEL REPORTE VISUAL
    # =========================================================================
    if resultado_operacion >= 0:
        estilo_caja = "background-color: #e2f0d9; border: 2px solid #385723; padding: 15px; border-radius: 5px; text-align: center;"
        color_subcajas = "background-color: #f2f2f2; border: 1px solid #d9d9d9; padding: 10px; border-radius: 5px; text-align: center;"
    else:
        estilo_caja = "background-color: #fce4d6; border: 2px solid #c65911; padding: 15px; border-radius: 5px; text-align: center;"
        color_subcajas = "background-color: #fce4d6; border: 1px solid #c65911; padding: 10px; border-radius: 5px; text-align: center;"

    st.write(f"##### 📊 Resultado Parcial del Período ({fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')})")
    
    st.markdown(f"""
    <div style="{estilo_caja}">
        <h4 style='margin:0; color:#333333;'>Resultado Total de la Operación (Utilidad Neta)</h4>
        <h2 style='margin:5px 0 0 0; color:{"#c00000" if resultado_operacion < 0 else "#385723"};'>
            $ {resultado_operacion:,.2f}
        </h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="{estilo_caja}">
        <h4 style='margin:0; color:#333333;'>Junta Directiva (74,00%)</h4>
        <h3 style='margin:5px 0 0 0; color:{"#c00000" if junta_directiva < 0 else "#385723"};'>
            $ {junta_directiva:,.2f}
        </h3>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_adm, col_prov = st.columns(2)
    with col_adm:
        st.markdown(f"""
        <div style="{color_subcajas}">
            <h5 style='margin:0; color:#333333;'>Administración (5,00%)</h5>
            <h3 style='margin:5px 0 0 0; color:{"#c00000" if administracion < 0 else "#385723"};'>
                $ {administracion:,.2f}
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
    with col_prov:
        st.markdown(f"""
        <div style="{color_subcajas}">
            <h5 style='margin:0; color:#333333;'>Provisión (20,00%)</h5>
            <h3 style='margin:5px 0 0 0; color:{"#c00000" if provision < 0 else "#385723"};'>
                $ {provision:,.2f}
            </h3>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="{color_subcajas}">
        <h5 style='margin:0; color:#333333;'>Ahorro (1,00%)</h5>
        <h3 style='margin:5px 0 0 0; color:{"#c00000" if ahorro < 0 else "#385723"};'>
            $ {ahorro:,.2f}
        </h3>
    </div>
    """, unsafe_allow_html=True)

    # =========================================================================
    # 📋 BITÁCORA DETALLADA DE DISTRIBUCIÓN DEL INGRESO (Actualizada)
    # =========================================================================
    st.markdown("---")
    st.write("#### 🧾 Resumen Analítico de Caja")
    
    datos_resumen = {
        "Concepto Financiero": [
            "(+) Ingresos por Servicios (Fletes)", 
            "(+) Otros Ingresos", 
            "(=) Total Ingresos Brutos", 
            "(-) Gastos de Operación (Tabla Gastos)", 
            "(-) Gastos de Viaje (Tabla Gastos Operativos Viaje)",
            "(-) Gasto de Combustible (Flota)", # ⛽ Nueva fila visible
            "(=) SALDO NETO A REPARTIR"
        ],
        "Monto ($ USD)": [
            f"$ {total_servicios:,.2f}",
            f"$ {otros_ingresos:,.2f}",
            f"$ {total_ingresos:,.2f}",
            f"$ {total_gastos:,.2f}",
            f"$ {total_gastos_viaje:,.2f}", # Monto mapeado de la nueva consulta
            f"$ {total_combustible:,.2f}", # Monto mapeado de la nueva consulta
            f"$ {resultado_operacion:,.2f}"
        ]
    }
    df_resumen = pd.DataFrame(datos_resumen)
    st.table(df_resumen)