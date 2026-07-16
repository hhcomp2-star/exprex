# componentes.py
import streamlit as st
import os

def mostrar_encabezado_exprex():
    """
    Renderiza el logo de ExpreX y el título de la aplicación 
    alineados horizontalmente de forma idéntica en cualquier pantalla.
    """
    ruta_logo = "modulos/logo_exprex_7.png"

    # Creamos dos columnas: una pequeña para el logo y una grande para el texto
    col_logo, col_titulo = st.columns([1, 5])

    with col_logo:
        if os.path.exists(ruta_logo):
            # Un ancho de 60px para que actúe como un icono nítido
            st.image(ruta_logo, width=60)
        else:
            # Colocamos un espacio vacío o un emoji de respaldo si el archivo no existe
            st.write("🚛")

    with col_titulo:
        # Colocamos un pequeño margen superior en HTML para alinear verticalmente el texto con el logo
        st.markdown(
            "<h2 style='margin-top: 18px; margin-bottom: 0px; line-height: 1;'>ExpreX Logística</h2>",
            #"<h2 style='margin-top: 18px; margin-bottom: 0px;'>ExpreX Logística</h2>", 
            unsafe_allow_html=True
        )
