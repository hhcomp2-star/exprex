import streamlit as st
import pandas as pd
from datetime import datetime
from modulos.utils import obtener_conexion_db

# Asumo que importas 'obtener_conexion_db' desde tu módulo de base de datos, por ejemplo:
# from database import obtener_conexion_db

def mostrar_modulo_finanzas():
    st.markdown("### 📊 Panel de Control Financiero Operativo")
    st.write("Control manual, rápido e independiente con historial completo de movimientos.")
    
    # =========================================================================
    # CÁLCULO DE MÉTRICAS GLOBALES (Solo suma lo que de verdad está pendiente)
    # =========================================================================
    # Usamos la secuencia 'with' para conectarnos y leer con Pandas de manera segura
    with obtener_conexion_db() as conn:
        total_cxc = pd.read_sql_query(
            "SELECT SUM(monto_pendiente) AS total FROM cxc_independiente WHERE estatus != 'Pagado'", 
            conn
        )['total'].values[0] or 0.0
        
        total_cxp = pd.read_sql_query(
            "SELECT SUM(monto_pendiente) AS total FROM cxp_independiente WHERE estatus != 'Pagado'", 
            conn
        )['total'].values[0] or 0.0
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric(label="💰 Total por Cobrar (Activo en Calle)", value=f"$ {total_cxc:,.2f}", delta="Por recuperar")
    with m2:
        st.metric(label="📉 Total por Pagar (Compromisos Reales)", value=f"$ {total_cxp:,.2f}", delta="Deuda pendiente", delta_color="inverse")
    with m3:
        balance = total_cxc - total_cxp
        st.metric(label="⚖️ Balance Disponible de Pasillo", value=f"$ {balance:,.2f}", delta="Margen de maniobra")
        
    st.markdown("---")
    
    tab_ver_cxc, tab_ver_cxp, tab_nuevo_registro = st.tabs([
        "💵 Historial de Cuentas por Cobrar", 
        "🛠️ Historial de Cuentas por Pagar (Prueba de Pagos)", 
        "📝 Registrar Nuevo Movimiento"
    ])
    
    # =========================================================================
    # PESTAÑA 1: HISTORIAL Y COBROS (CUENTAS POR COBRAR)
    # =========================================================================
    with tab_ver_cxc:
        st.markdown("#### 🏢 Dinero a favor de la empresa (Historial Completo)")
        
        with obtener_conexion_db() as conn:
            # Traemos todo el historial sin filtros para que actúe como respaldo histórico
            df_cxc = pd.read_sql_query("""
                SELECT id_cxc AS "Ref", deudor AS "Deudor / Cliente", concepto AS "Tipo de Cobro", 
                       monto_inicial AS "Monto Original ($)", monto_pendiente AS "Saldo Pendiente ($)", 
                       fecha_registro AS "Fecha Registro", estatus AS "Estatus", notas AS "Historial de Abonos / Notas"
                FROM cxc_independiente
                ORDER BY id_cxc DESC
            """, conn)
        
        if df_cxc.empty:
            st.info("No hay registros en el historial de cobros.")
        else:
            # Se muestra la tabla con el historial de todo (Pendientes, Parciales y Pagados)
            st.dataframe(df_cxc, use_container_width=True, hide_index=True)
            
            # FILTRADO CLAVE: Para el selector de cobros, buscamos sólo las que NO estén totalmente pagadas
            with obtener_conexion_db() as conn:
                cxc_activas = pd.read_sql_query(
                    "SELECT id_cxc FROM cxc_independiente WHERE estatus != 'Pagado' ORDER BY id_cxc DESC", 
                    conn
                )['id_cxc'].tolist()
            
            if cxc_activas:
                with st.expander("🛠️ Registrar Abono o Cobro de Cuenta Activa"):
                    id_sel = st.selectbox("Seleccione Ref de la Cuenta a Cobrar:", cxc_activas, key="sb_pay_cxc")
                    fecha_cobro = st.date_input("Fecha en la que recibió el dinero:", datetime.now().date(), key="date_pay_cxc")
                    fecha_cobro_str = fecha_cobro.strftime("%Y-%m-%d")
                    abono = st.number_input("Monto que pagan ($):", min_value=0.01, step=5.0, key="num_pay_cxc")
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("🚀 Confirmar Cobro", use_container_width=True):
                            # Aplicamos la secuencia doble with compacta para leer y luego actualizar de manera segura
                            with obtener_conexion_db() as conn, conn.cursor() as cursor:
                                cursor.execute("SELECT monto_pendiente, notas FROM cxc_independiente WHERE id_cxc = %s", (id_sel,))
                                fila = cursor.fetchone()
                            
                                if fila is not None:
                                    pendiente_actual = float(fila[0])
                                    notas_actuales = fila[1] or ""
                                    
                                    nuevo_pendiente = max(0.0, pendiente_actual - abono)
                                    nuevo_estatus = "Pagado" if nuevo_pendiente == 0 else "Parcial"
                                    nueva_nota = f"{notas_actuales} | Cobro de ${abono} el {fecha_cobro_str}.".strip(" | ")
                                    
                                    cursor.execute("""
                                        UPDATE cxc_independiente 
                                        SET monto_pendiente = %s, estatus = %s, notas = %s 
                                        WHERE id_cxc = %s
                                    """, (nuevo_pendiente, nuevo_estatus, nueva_nota, id_sel))
                                else:
                                    st.error("No se encontró el registro de la cuenta por cobrar.")

                            st.success("¡Cobro guardado con éxito!")
                            st.rerun()
                    with b2:
                        if st.button("❌ Cancelar y Volver", use_container_width=True, key="btn_cancel_cxc"):
                            st.rerun()
            else:
                st.success("✨ ¡Estamos al día! No hay cobros pendientes por procesar.")
    #
    # =========================================================================
    # PESTAÑA 2: HISTORIAL Y PAGOS (CUENTAS POR PAGAR - TU ESCUDO)
    # =========================================================================
    with tab_ver_cxp:
        st.markdown("### 🛞 Compromisos y Pagos realizados por ExpreX")
        st.caption("Esta tabla almacena todo el historial. Si alguien reclama, búscalo aquí para comprobar las fechas.")
        
        with obtener_conexion_db() as conn:
            # Historial sin filtros para auditorías de pasillo ante reclamos
            df_cxp = pd.read_sql_query("""
                SELECT id_cxp AS "Ref", acreedor AS "Acreedor / Proveedor", concepto AS "Tipo de Gasto", 
                       monto_inicial AS "Monto Original ($)", monto_pendiente AS "Saldo por Pagar ($)", 
                       fecha_registro AS "Fecha Registro", estatus AS "Estatus", notas AS "Historial de Pagos / Pruebas"
                FROM cxp_independiente
                ORDER BY id_cxp DESC
            """, conn)
        
        if df_cxp.empty:
            st.info("No hay registros en el historial de deudas.")
        else:
            # Se despliega la tabla completa con el registro histórico
            st.dataframe(df_cxp, use_container_width=True, hide_index=True)
            
            # FILTRADO CLAVE: Para liquidar, sólo extraemos las deudas que tengan saldo pendiente
            with obtener_conexion_db() as conn:
                cxp_activas = pd.read_sql_query(
                    "SELECT id_cxp FROM cxp_independiente WHERE estatus != 'Pagado' ORDER BY id_cxp DESC", 
                    conn
                )['id_cxp'].tolist()
            
            if cxp_activas:
                with st.expander("🛠️ Registrar Pago o Liquidación de Deuda Activa"):
                    id_sel_cxp = st.selectbox("Seleccione Ref de la Cuenta a Pagar:", cxp_activas, key="sb_pay_cxp")
                    fecha_pago = st.date_input("Fecha en la que se entregó el dinero:", datetime.now().date(), key="date_pay_cxp")
                    fecha_pago_str = fecha_pago.strftime("%Y-%m-%d")
                    abono_cxp = st.number_input("Monto que pagamos ($):", min_value=0.01, step=5.0, key="num_pay_cxp")
                    
                    bp1, bp2 = st.columns(2)
                    with bp1:
                        if st.button("🚀 Confirmar Gasto / Pago", use_container_width=True, type="primary"):
                            with obtener_conexion_db() as conn, conn.cursor() as cursor:
                                cursor.execute("SELECT monto_pendiente, notas FROM cxp_independiente WHERE id_cxp = %s", (id_sel_cxp,))
                                fila_cxp = cursor.fetchone()
                                
                                # Validamos para limpiar el error de Pylance en la línea 156
                                if fila_cxp is not None:
                                    pendiente_actual = float(fila_cxp[0])
                                    notas_actuales = fila_cxp[1] or ""
                                    
                                    nuevo_pendiente = max(0.0, pendiente_actual - abono_cxp)
                                    nuevo_estatus = "Pagado" if nuevo_pendiente == 0 else "Parcial"
                                    nueva_nota = f"{notas_actuales} | Pago de ${abono_cxp} el {fecha_pago_str}.".strip(" | ")
                                    
                                    cursor.execute("""
                                        UPDATE cxp_independiente 
                                        SET monto_pendiente = %s, estatus = %s, notas = %s 
                                        WHERE id_cxp = %s
                                    """, (nuevo_pendiente, nuevo_estatus, nueva_nota, id_sel_cxp))
                                    
                                    st.success("¡Pago registrado correctamente!")
                                    st.rerun()
                                else:
                                    st.error("No se encontró el registro de la cuenta por pagar seleccionado.")
                    with bp2:
                        if st.button("❌ Cancelar y Volver", use_container_width=True, key="btn_cancel_cxp"):
                            st.rerun()
            else:
                st.success("✨ ¡Felicidades! ExpreX no tiene compromisos pendientes en la calle.")

    # =========================================================================
    # PESTAÑA 3: REGISTRO 100% MANUAL Y LIBRE
    # =========================================================================
    with tab_nuevo_registro:
        st.markdown("### ✍️ Formulario Manual de Anotaciones Rápidas")
        
        fecha_seleccionada = st.date_input("Fecha del Movimiento Real:", datetime.now().date(), key="date_registro_nuevo")
        fecha_registro_str = fecha_seleccionada.strftime("%Y-%m-%d")
        
        st.markdown("---")
        col_cxc, col_cxp = st.columns(2)
        
        # Alguien nos debe a nosotros
        with col_cxc:
            st.info("➕ Registrar Dinero por Cobrar (Alguien nos debe)")
            deudor_nombre = st.text_input("Quién debe (Persona, Chofer o Empresa):", placeholder="Ej: Juan Pérez")
            concepto_cxc = st.selectbox("Concepto del cobro:", ["Préstamo a Personal", "Avance de Efectivo", "Venta Minorista", "Gasto Reembolsable", "Otro Cobro"])
            monto_cxc = st.number_input("Monto ($):", min_value=0.0, step=5.0, key="input_m_cxc")
            notas_cxc = st.text_area("Detalles del cobro / Condiciones:", placeholder="Ej: Se compromete a pagar el próximo viernes.")
            
            if st.button("Guardar Cuenta por Cobrar", use_container_width=True):
                if deudor_nombre and monto_cxc > 0:
                    with obtener_conexion_db() as conn, conn.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO cxc_independiente (deudor, concepto, monto_inicial, monto_pendiente, fecha_registro, notas)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (deudor_nombre.strip(), concepto_cxc, monto_cxc, monto_cxc, fecha_registro_str, notas_cxc.strip()))
                    
                    st.success(f"Anclado con éxito: {deudor_nombre} por ${monto_cxc}")
                    st.rerun()
                else:
                    st.error("Rellena el nombre y el monto antes de guardar.")

        # Nosotros debemos en la calle
        with col_cxp:
            st.warning("⚠️ Registrar Compromiso por Pagar (ExpreX debe)")
            acreedor_nombre = st.text_input("A quién le debemos (Taller, Proveedor, Chofer):", placeholder="Ej: Talleres El Chamo")
            concepto_cxp = st.selectbox("Concepto de la deuda:", ["Mantenimiento Mecánico", "Compra de Repuestos", "Combustible Fiado", "Servicios de Terceros", "Otro Compromiso"])
            monto_cxp = st.number_input("Monto ($):", min_value=0.0, step=5.0, key="input_m_cxp")
            notas_cxp = st.text_area("Detalles del trabajo o acuerdo:", placeholder="Ej: Reparación de frenos camión 2.")
            
            if st.button("Guardar Cuenta por Pagar", use_container_width=True):
                if acreedor_nombre and monto_cxp > 0:
                    with obtener_conexion_db() as conn, conn.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO cxp_independiente (acreedor, concepto, monto_inicial, monto_pendiente, fecha_registro, notas)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (acreedor_nombre.strip(), concepto_cxp, monto_cxp, monto_cxp, fecha_registro_str, notas_cxp.strip()))
                    
                    st.success(f"Registrada deuda con: {acreedor_nombre} por ${monto_cxp}")
                    st.rerun()
                else:
                    st.error("Rellena el nombre del acreedor y el monto antes de guardar.")