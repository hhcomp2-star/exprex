import streamlit as st  # Usando tu alias estándar
import sqlite3
import pandas as pd
import time

def mostrar_modulo_registro():
    # 🎯 Inicializamos las variables de control de bienvenida en el session_state si no existen
    if "mostrar_bienvenida" not in st.session_state:
        st.session_state.mostrar_bienvenida = False
    if "usuario_registrado_nombre" not in st.session_state:
        st.session_state.usuario_registrado_nombre = ""

    st.write("## 📝 Registro de Nuevo Conductor")
    st.caption("Introduce tus datos básicos para darte de alta en la plataforma de ExpreX Logística.")

    # =========================================================================
    # MULTIPLEXOR VISUAL: Muestra el aviso de bienvenida O el formulario
    # =========================================================================
    if st.session_state.mostrar_bienvenida:
        st.markdown("---")
        # Tu mensaje personalizado usando el nombre capturado
        st.info(
            f"👋 ¡Bienvenido(a) a nuestro equipo, **{st.session_state.usuario_registrado_nombre}**! "
            f"Dentro de poco, el personal de Soporte se comunicará contigo vía WhatsApp o llamada "
            f"para completar tu registro personal y de vehículo, si fuera el caso."
            f"\n\nMientras tanto, puedes iniciar sesión con tu Cédula y Contraseña."
        )
        
        # Botón Aceptar para limpiar el estado e ir por fin al Login
        if st.button("Aceptar", type="primary", use_container_width=True):
            st.session_state.mostrar_bienvenida = False
            st.session_state.usuario_registrado_nombre = ""
            if "vista_login" in st.session_state:
                st.session_state["vista_login"] = "login"
            st.rerun()

    else:
        # Si no se está mostrando la bienvenida, se renderiza el formulario normal
        with st.form("formulario_registro_chofer"):
            cedula = st.text_input("Cédula de Identidad:", placeholder="Ej: 12345678").strip()
            nombre = st.text_input("Nombre y Apellido completo:").strip()
            
            # 🎯 NUEVO DATO SOLICITADO: Teléfono obligatorio para que soporte llame o escriba
            telefono = st.text_input("Número de Teléfono / WhatsApp:", placeholder="Ej: 04121234567").strip()
            
            email = st.text_input("Correo Electrónico:", placeholder="Ej: pedroperez@gmail.com").strip()
            banco = st.text_input("Nombre del Banco:", placeholder="Ej: Banco de Venezuela").strip()
            num_cuenta = st.text_input("Número de Cuenta:", placeholder="Ej: 01050123456789012345").strip()

            st.markdown("---")
            clave = st.text_input("Crea tu Contraseña de Acceso:", type="password")
            clave_confirmar = st.text_input("Confirma tu Contraseña:", type="password")

        # ----------------------------------------- Términos y condiciones ------------------------------------------------------------------    

            st.markdown("---")
            
            # Intentamos leer el archivo de texto externo con los términos largos
            try:
                with open("/home/hector/exprex/modulos/terminos.txt", "r", encoding="utf-8") as archivo:
                    texto_legal = archivo.read()
            except FileNotFoundError:
                texto_legal = "⚠️ **Error:** El archivo 'terminos.txt' no se encuentra en el servidor. Por favor, contacte al Administrador."

            # El expander que el usuario abre si desea leer todo el documento
            with st.expander("📋 Leer Términos, Condiciones y Política de Privacidad de ExpreX"):
                st.markdown(texto_legal)

            # Casilla de verificación visible dentro del formulario
            acepta_terminos = st.checkbox("Acepto los Términos de Uso y la Política de Privacidad")

            # Botón de envío del formulario
            boton_registrar = st.form_submit_button("Finalizar Registro", use_container_width=True)

        # =========================================================================
        # PROCESAMIENTO LOGÍSTICO AL HACER CLIC
        # =========================================================================
        if boton_registrar:
            # Validación A: Campos vacíos (incluyendo el nuevo campo de teléfono)
            if not cedula or not nombre or not telefono or not email or not clave:
                st.error("⚠️ Todos los campos son obligatorios para proceder con el registro.")
            
            # Validación B: Aceptación de términos obligatoria
            elif not acepta_terminos:
                st.error("⚠️ Debes leer y aceptar los Términos y Condiciones marcando la casilla para poder registrarte.")
            
            # Validación C: Coincidencia de contraseña
            elif clave != clave_confirmar:
                st.error("❌ Las contraseñas ingresadas no coinciden. Inténtalo de nuevo.")
                
            elif len(clave) < 6:
                st.error("⚠️ La contraseña debe tener al menos 6 caracteres por seguridad.")
                
            else:
                try:
                    # Conectamos a tu base de datos real
                    conexion = sqlite3.connect('exprex.db')
                    cursor = conexion.cursor()
                    
                    # Verificar si la cédula ya existe para evitar errores de Llave Primaria
                    cursor.execute("SELECT cedula FROM usuarios WHERE cedula = ?", (cedula,))
                    existe = cursor.fetchone()
                    
                    if existe:
                        st.error(f"🛑 La cédula {cedula} ya se encuentra registrada en el sistema. Si olvidaste tu acceso, usa la opción de recuperación.")
                        conexion.close()
                    else:
                        # 🎯 Insertar el nuevo usuario incluyendo el campo 'telefono'
                        # NOTA: Asegúrate de que tu tabla 'usuarios' tenga la columna 'telefono' creada
                        cursor.execute('''
                            INSERT INTO usuarios (cedula, nombre, telefono, email, contrasena, rol, activo, departamento)
                            VALUES (?, ?, ?, ?, ?, 'Conductor', 'Sí', 'Operaciones')
                        ''', (cedula, nombre, telefono, email, clave))
                        
                        conexion.commit()
                        conexion.close()
                        
                        # 🚀 GUARDAMOS EN SESIÓN PARA DISPARAR LA BIENVENIDA
                        st.session_state.usuario_registrado_nombre = nombre
                        st.session_state.mostrar_bienvenida = True
                        
                        # Forzamos recarga inmediata para ocultar el formulario y pintar el aviso
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Error al registrar en la base de datos: {e}")