import streamlit as st
import pandas as pd
from io import BytesIO
from modulos.utils import obtener_conexion_db
from typing import Any, List


def renderizar_auditoria_fletes_subtab():
    st.markdown("#### 🚚 Auditoría de Fletes e Ingresos por Conductor")
    st.caption("Filtra y audita el acumulado de viajes, clientes asociados y montos a liquidar por período.")

    # 1. Filtros superiores
    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])

    with col_f1:
        fecha_inicio = st.date_input(
            "Fecha Inicio", 
            value=pd.to_datetime("today").replace(day=1), 
            key="aud_fletes_f_ini"
        )
    with col_f2:
        fecha_fin = st.date_input(
            "Fecha Fin", 
            value=pd.to_datetime("today"), 
            key="aud_fletes_f_fin"
        )

    # 2. Carga de usuarios: SOLO conductores activos
    conn = obtener_conexion_db()
    
    # 🛠️ FILTRO APLICADO: rol == 'conductor' Y activo == 'Sí'
    query_cond = """
        SELECT cedula, nombre 
        FROM usuarios 
        WHERE LOWER(rol) = 'conductor' AND (activo = 'Sí' OR activo = 'Si' OR activo = 'true')
        ORDER BY nombre ASC;
    """
    df_cond = pd.read_sql_query(query_cond, conn)
    
    dict_conductores = {"TODOS": "Todos los conductores (Consulta General)"}
    for _, row in df_cond.iterrows():
        dict_conductores[row["cedula"]] = f"{row['nombre']} ({row['cedula']})"

    with col_f3:
        seleccion_chofer = st.selectbox(
            "Seleccionar Conductor (General / Individual)",
            options=list(dict_conductores.keys()),
            format_func=lambda x: dict_conductores[x],
            key="aud_fletes_chofer_select"
        )

    # 3. Consulta SQL con JOINs a clientes y usuarios
    query_viajes = """
        SELECT 
            v.id_viaje,
            v.origen,
            v.num_pedido,
            v.cedula_conductor,
            u.nombre AS nombre_conductor,
            v.destino,
            c.razon_social AS cliente,
            v.pago_chofer_usd
        FROM viajes v
        LEFT JOIN clientes c ON v.id_cliente = c.id_cliente
        LEFT JOIN usuarios u ON v.cedula_conductor = u.cedula
        WHERE DATE(v.fecha_viaje) BETWEEN %s AND %s
    """
    params: list = [fecha_inicio, fecha_fin]

    if seleccion_chofer != "TODOS":
        query_viajes += " AND v.cedula_conductor = %s"
        params.append(seleccion_chofer)

    query_viajes += " ORDER BY v.id_viaje DESC;"

    df_fletes = pd.read_sql_query(query_viajes, conn, params=tuple(params))
    conn.close()

    st.markdown("---")

    if df_fletes.empty:
        st.info("ℹ️ No se encontraron viajes registrados para las condiciones seleccionadas.")
        return

    # 4. Métricas acumuladas y descarga
    total_viajes = len(df_fletes)
    total_pago_usd = df_fletes["pago_chofer_usd"].sum()

    m_col1, m_col2, m_col3 = st.columns([2, 2, 3])
    with m_col1:
        st.metric("Total Viajes Realizados", f"{total_viajes} 🚚")
    with m_col2:
        st.metric("Total Pago Chofer (USD)", f"${total_pago_usd:,.2f}")
    with m_col3:
        # Generar archivo de Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df_fletes.to_excel(writer, index=False, sheet_name="Auditoria_Fletes")
        output.seek(0)

        st.download_button(
            label="📥 Descargar Hoja de Cálculo (Excel)",
            data=output,
            file_name=f"auditoria_fletes_{fecha_inicio}_al_{fecha_fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # 5. Formato de nombres de columna para pantalla
    df_mostrar = df_fletes.rename(
        columns={
            "id_viaje": "ID Viaje",
            "origen": "Origen",
            "num_pedido": "N° Pedido",
            "cedula_conductor": "Cédula Conductor",
            "nombre_conductor": "Nombre Conductor",
            "destino": "Destino",
            "cliente": "Razón Social Cliente",
            "pago_chofer_usd": "Pago Chofer ($USD)"
        }
    )

    # 6. Visualización de la tabla
    st.dataframe(
        df_mostrar.style.format({"Pago Chofer ($USD)": "${:,.2f}"}),
        use_container_width=True,
        hide_index=True
    )