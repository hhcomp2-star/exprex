import streamlit as st
import os
import time
from streamlit_option_menu import option_menu
from modulos.nomina import mostrar_modulo_nomina
from modulos.clientes import mostrar_modulo_clientes
from modulos.vehiculos import mostrar_modulo_vehiculos
from modulos.gestion_gastos import mostrar_modulo_gastos
from modulos.combustible import mostrar_modulo_combustible
from modulos.gastos_viaje import mostrar_modulo_gastos_viaje
from modulos.finanzas_rapidas import mostrar_modulo_finanzas
from modulos.reportes_financieros import mostrar_modulo_reportes
from modulos.operaciones_viajes import mostrar_modulo_operaciones
from modulos.reporte_general import mostrar_modulo_reporte_general
from modulos.mantenimiento_sistema import mostrar_modulo_mantenimiento
from modulos.utils import contar_viajes_solicitados_global, reproducir_alerta_victoria


# ===============================================================================
# 🛠️ FUNCIONES AUXILIARES Y SIMULADORES (Ajusta las importaciones si ya existen)
# ===============================================================================

@st.dialog("Salir del Sistema")
def confirmar_salida_sistema_modal():
    st.write("¿Está seguro de que desea cerrar su sesión en ExpreX?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sí, Salir", use_container_width=True, type="primary"):
            st.session_state.autenticado = False
            st.session_state.usuario_cedula = ""
            st.session_state.usuario_nombre = ""
            st.session_state.usuario_rol = ""
            st.session_state.cliente_id = None
            st.session_state.vista_login = "login"
            st.rerun()
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

# =========================================================================
# 💻 FUNCIÓN PRINCIPAL DEL MÓDULO ADMINISTRADOR
# =========================================================================

def mostrar_panel_administrador():
    st.header("💼 ExpreX - Control de Operaciones")
    
    # Validación por si acaso no se ha inicializado la tasa en el main
    tasa = st.session_state.get('tasa_bcv', '0.00')
    st.sidebar.success(f"Tasa BCV activa: {tasa} Bs.")

    # Alertas de fletes pendientes
    pendientes = contar_viajes_solicitados_global()
    if pendientes > 0:
        st.sidebar.markdown(f"---")
        st.sidebar.error(f"🚨 **¡ATENCIÓN!** Hay {pendientes} fletes pendientes de aprobación.")
        reproducir_alerta_victoria()
    
    opciones_menu = [
        "Inicio", "Control Operativo", "Gestión de Clientes", "Nómina",  
        "Control de Flota", "Combustible", "Registrar Gastos", "Gastos de Viaje", 
        "Cuentas", "Reportes", "Reporte General", "Mantenimiento", "Salir del Sistema"
    ]
    iconos_menu = [
        "house", "book", "briefcase", "person-badge", "truck", "fuel-pump", 
        "receipt", "map", "book", "file-earmark-bar-graph", "building-up", 
        "database-gear", "door-open"
    ]
    
    with st.sidebar:
        st.success(f"Perfil: {st.session_state.usuario_rol}")
        if "menu_navegacion" not in st.session_state:
            st.session_state["menu_navegacion"] = "Inicio"

        seleccion = option_menu(
            menu_title="Navegación",
            options=opciones_menu,
            icons=iconos_menu,
            menu_icon="cast",
            key="menu_navegacion"
        )

    # --- ENRUTADOR DE MÓDULOS DE ADMINISTRACIÓN ---
    if seleccion == "Inicio":
        st.subheader(f"Hola, {st.session_state.usuario_nombre}")
        st.write("Bienvenido al sistema de gestión de transporte de materiales livianos.")
        
        # Validación de la ruta de la imagen
        ruta_logo = "modulos/Flete_Flash_Logo_2.png"
        if os.path.exists(ruta_logo):
            st.image(ruta_logo)
        else:
            st.info("Logo de ExpreX — (Colocar imagen Flete_Flash_Logo_2.png)")
            
        st.info("Selecciona una opción en el menú izquierdo para empezar a trabajar.")
        
    elif seleccion == "Gestión de Clientes":
        mostrar_modulo_clientes()
    elif seleccion == "Control Operativo":
        mostrar_modulo_operaciones()
    elif seleccion == "Control de Flota":
        mostrar_modulo_vehiculos()
    elif seleccion == "Nómina":
        mostrar_modulo_nomina()  
    elif seleccion == "Combustible":
        mostrar_modulo_combustible()
    elif seleccion == "Registrar Gastos":
        mostrar_modulo_gastos()
    elif seleccion == "Gastos de Viaje":
        mostrar_modulo_gastos_viaje()
    elif seleccion == "Cuentas":
        mostrar_modulo_finanzas()
    elif seleccion == "Reportes":
        mostrar_modulo_reportes()
    elif seleccion == "Reporte General":
        mostrar_modulo_reporte_general()
    elif seleccion == "Mantenimiento":
        mostrar_modulo_mantenimiento()
    elif seleccion == "Salir del Sistema":
        confirmar_salida_sistema_modal()
