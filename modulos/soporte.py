import streamlit as st
import urllib.parse 

def llamar_soporte():
    # 1. El chofer ingresa su número de teléfono
    telefono_usuario = st.text_input(
        "📞 Ingresa tu número de teléfono registrado:", 
        placeholder="Ej: +584141234567",
        key="tel_soporte"
    )

    # 2. Si el usuario escribió su número, le mostramos el botón de enviar
    if telefono_usuario.strip():
        # Tu número de soporte de ExpreX que recibirá el caso
        numero_soporte_empresa = "584140335554"
        
        # Armamos y codificamos el mensaje para que no falle con las tildes
        mensaje_soporte = f"Hola, soy chofer de ExpreX. Necesito soporte técnico con mi usuario. Mi número de teléfono registrado es: {telefono_usuario}."
        mensaje_codificado = urllib.parse.quote(mensaje_soporte)
        url_whatsapp = f"https://wa.me/{numero_soporte_empresa}?text={mensaje_codificado}"
        
        # Mostramos un botón real y llamativo de "Enviar" que abre la URL
        st.link_button(
            label="🚀 Enviar reporte por WhatsApp", 
            url=url_whatsapp, 
            type="primary",          # Esto lo pinta de azul/color principal de tu tema
            use_container_width=True # Hace que ocupe todo el ancho en la pantalla del celular
        )
    else:
        # Mensaje amigable mientras el campo está vacío
        st.info("💡 Por favor, escribe tu número de teléfono arriba y luego taca aquí para habilitar el botón de envío.")
