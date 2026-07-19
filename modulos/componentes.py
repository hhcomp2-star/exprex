# componentes.py
import streamlit as st
import os
from streamlit.components.v1 import html
import pandas as pd

def mostrar_encabezado_exprex():
    """
    Renderiza el logo de ExpreX y el título de la aplicación 
    alineados horizontalmente de forma idéntica en cualquier pantalla.
    """
    ruta_logo = "favicon.ico"

    # Creamos dos columnas: una pequeña para el logo y una grande para el texto
    col_logo, col_titulo = st.columns([0.4,0.6], vertical_alignment="center", width="stretch")

    with col_logo:
        if os.path.exists(ruta_logo):
            # Un ancho de 60px para que actúe como un icono nítido
            st.image(ruta_logo, width=65)
        else:
            # Colocamos un espacio vacío o un emoji de respaldo si el archivo no existe
            st.write("🚛")

    with col_titulo:
        # Colocamos un pequeño margen superior en HTML para alinear verticalmente el texto con el logo
        #st.markdown(
        st.markdown("<h2 style='margin:0; padding:0; line-height:1.1;'>ExpreX Logística</h2>", unsafe_allow_html=True)
            #"<h2 style='margin-top: 25px; margin-bottom: 0px; line-height: 1;'>ExpreX Logística</h2>",
            #"<h2 style='margin-top: 18px; margin-bottom: 0px;'>ExpreX Logística</h2>", 
            #unsafe_allow_html=True
        #)


def mostrar_encabezado_exprex_chofer():
    """
    Renderiza el logo de ExpreX y el título de la aplicación 
    alineados horizontalmente de forma idéntica en cualquier pantalla.
    """
    ruta_logo = "favicon.ico"

    # Creamos dos columnas: una pequeña para el logo y una grande para el texto
    col_logo, col_titulo = st.columns([0.2, 0.8], vertical_alignment="center", width="stretch")

    with col_logo:
        if os.path.exists(ruta_logo):
            # Un ancho de 60px para que actúe como un icono nítido
            st.image(ruta_logo, width=60)
        else:
            # Colocamos un espacio vacío o un emoji de respaldo si el archivo no existe
            st.write("🚛")

    with col_titulo:
        # Colocamos un pequeño margen superior en HTML para alinear verticalmente el texto con el logo
        #st.markdown(
        st.markdown("<h4 style='margin:0; padding:0; line-height:1.1;'>ExpreX Logística</h4>", unsafe_allow_html=True)