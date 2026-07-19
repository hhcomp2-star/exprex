import streamlit as db_st  # Mantenemos tu alias db_st para este archivo
import pandas as pd
import time

# Importamos tu función centralizada de conexión (ajusta el import si es necesario)
from modulos.utils import obtener_conexion_db  

def mostrar_modulo_recuperar_contrasena():

    # Inicializar estados de navegación si no existen
    if "paso_recuperacion" not in db_st.session_state:
        db_st.session_state["paso_recuperacion"] = 1
    if "cedula_a_recuperar" not in db_st.session_state:
        db_st.session_state["cedula_a_recuperar"] = None

    db_st.write("##### 🔑 Recuperación de Contraseña Olvidada")
    db_st.caption("Por favor, sigue los pasos para validar tu identidad y restablecer el acceso al sistema.")

    # =========================================================================
    # PASO 1: INTRODUCIR CÉDULA Y VERIFICAR EXISTENCIA
    # =========================================================================
    if db_st.session_state["paso_recuperacion"] == 1:
        with db_st.form("form_paso1_recuperar"):
            cedula_input = db_st.text_input("Introduce tu número de Cédula:", key="rec_cedula").strip()
            boton_validar_cedula = db_st.form_submit_button("Verificar Usuario", use_container_width=True)
            
        if boton_validar_cedula:
            if not cedula_input:
                db_st.error("⚠️ El campo de la cédula no puede estar vacío.")
            else:
                try:
                    with obtener_conexion_db() as conexion:
                        # Buscamos al usuario sin importar el rol (aplica a choferes u operaciones)
                        # Adaptamos el marcador de posición a %s para PostgreSQL
                        query = "SELECT cedula, nombre, telefono, email FROM usuarios WHERE cedula = %s AND activo = 'Sí'"
                        df_user = pd.read_sql_query(query, conexion, params=(cedula_input,))
                    
                    if df_user.empty:
                        db_st.error("🛑 La cédula ingresada no coincide con ningún usuario activo en el sistema.")
                    else:
                        # Guardamos los datos en el session_state para el siguiente paso
                        db_st.session_state["cedula_a_recuperar"] = df_user.iloc[0]['cedula']
                        db_st.session_state["nombre_a_recuperar"] = df_user.iloc[0]['nombre']
                        db_st.session_state["tel_registrado"] = df_user.iloc[0]['telefono']
                        db_st.session_state["email_registrado"] = df_user.iloc[0]['email']
                        
                        db_st.session_state["paso_recuperacion"] = 2
                        db_st.rerun()
                except Exception as e:
                    db_st.error(f"❌ Error al consultar la base de datos: {e}")

    # =========================================================================
    # PASO 2: COMPROBACIÓN DE IDENTIDAD (DOBLE FACTOR DE DATOS)
    # =========================================================================
    elif db_st.session_state["paso_recuperacion"] == 2:
        nombre_oculto = db_st.session_state["nombre_a_recuperar"]
        db_st.info(f"👤 **Usuario identificado:** {nombre_oculto}. Para validar que eres el dueño de esta cuenta, introduce alguno de tus datos de contacto registrados.")
        
        # Preparamos textos enmascarados para dar pistas sin exponer datos sensibles en pantalla
        tel_conf = db_st.session_state["tel_registrado"] or "No registrado"
        email_conf = db_st.session_state["email_registrado"] or "No registrado"
        pista_tel = f"******{tel_conf[-4:]}" if len(tel_conf) > 4 else "###"
        pista_mail = f"{email_conf[:3]}******@{email_conf.split('@')[-1]}" if "@" in email_conf else "###"

        with db_st.form("form_paso2_validar"):
            db_st.markdown(f"📞 *Pista de Teléfono registrado:* `{pista_tel}`")
            confirmar_telefono = db_st.text_input("Introduce tu número telefónico completo:", placeholder="Ej: 04141234567").strip()
            
            db_st.markdown("---")
            db_st.markdown(f"📧 *Pista de Correo registrado:* `{pista_mail}`")
            confirmar_email = db_st.text_input("Introduce tu correo electrónico completo:", placeholder="Ej: usuario@gmail.com").strip().lower()
            
            boton_comprobar_datos = db_st.form_submit_button("Confirmar Identidad", use_container_width=True)
            
        if boton_comprobar_datos:
            # Validación: Debe coincidir de forma estricta el teléfono o el correo ingresado
            match_telefono = (confirmar_telefono == db_st.session_state["tel_registrado"]) if db_st.session_state["tel_registrado"] else False
            match_email = (confirmar_email == db_st.session_state["email_registrado"].lower()) if db_st.session_state["email_registrado"] else False
            
            if match_telefono or match_email:
                db_st.success("✅ ¡Identidad confirmada con éxito!")
                db_st.session_state["paso_recuperacion"] = 3
                time.sleep(1)
                db_st.rerun()
            else:
                db_st.error("❌ Los datos introducidos no coinciden con los registros de la cuenta. Inténtalo de nuevo.")
                
        if db_st.button("⬅️ Volver a empezar"):
            db_st.session_state["paso_recuperacion"] = 1
            db_st.rerun()

    # =========================================================================
    # PASO 3: ESTABLECER NUEVA CONTRASEÑA
    # =========================================================================
    elif db_st.session_state["paso_recuperacion"] == 3:
        db_st.warning("🔒 Introduce tu nueva credencial de acceso. Asegúrate de anotarla en un lugar seguro.")
        
        with db_st.form("form_paso3_password"):
            nueva_clave = db_st.text_input("Nueva Contraseña:", type="password").strip()
            repetir_clave = db_st.text_input("Repite la Nueva Contraseña:", type="password").strip()
            boton_cambiar_clave = db_st.form_submit_button("Actualizar Contraseña", use_container_width=True)
            
        if boton_cambiar_clave:
            if len(nueva_clave) < 4:
                db_st.error("⚠️ La contraseña debe tener mínimo 4 caracteres por seguridad.")
            elif nueva_clave != repetir_clave:
                db_st.error("❌ Las contraseñas ingresadas no coinciden.")
            else:
                try:
                    # Conectamos de forma segura con el pool de conexiones de Postgres
                    with obtener_conexion_db() as conexion:
                        with conexion.cursor() as cursor:
                            # Actualizamos la contraseña utilizando el marcador %s
                            sql_update = "UPDATE usuarios SET contrasena = %s WHERE cedula = %s"
                            cursor.execute(sql_update, (nueva_clave, db_st.session_state["cedula_a_recuperar"]))
                            
                            # Validamos la transacción
                            conexion.commit()
                    
                    db_st.success("🎉 ¡Tu contraseña ha sido restablecida con éxito! Ya puedes iniciar sesión.")
                    
                    # Limpiamos variables temporales de recuperación de la memoria de la sesión
                    db_st.session_state["paso_recuperacion"] = 1
                    db_st.session_state["cedula_a_recuperar"] = None
                    
                    time.sleep(2)
                    # Volvemos a la vista raíz del login cambiando tu bandera de navegación
                    if "vista_login" in db_st.session_state:
                        db_st.session_state["vista_login"] = "login"
                    db_st.rerun()
                    
                except Exception as e:
                    db_st.error(f"❌ Error crítico al actualizar base de datos: {e}")

        if db_st.button("⬅️ Cancelar Proceso"):
            db_st.session_state["paso_recuperacion"] = 1
            db_st.session_state["cedula_a_recuperar"] = None
            if "vista_login" in db_st.session_state:
                db_st.session_state["vista_login"] = "login"
            db_st.rerun()