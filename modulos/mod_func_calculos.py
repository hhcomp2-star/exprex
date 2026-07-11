import sqlite3
import os
import streamlit as st

def cambiar_estatus_viaje_maestro(id_viaje, nuevo_estatus, db_path, archivo_foto_streamlit=None):
    """
    Función Única Centralizada para controlar el ciclo de vida de un flete.
    Soporta transiciones a 'En Ruta', 'Entregado', etc., recalculando las cuentas
    al cerrar en base a la distancia real de la base de datos.
    """
    try:
        conexion = sqlite3.connect(db_path)
        cursor = conexion.cursor()
        
        if nuevo_estatus == 'Entregado':
            # 📁 1️⃣ GUARDADO FÍSICO DE LA FOTO (Si se envía desde el teléfono)
            ruta_foto_final = None
            if archivo_foto_streamlit is not None:
                carpeta_destino = "fotos_entregas"
                if not os.path.exists(carpeta_destino):
                    os.makedirs(carpeta_destino)
                
                extension = archivo_foto_streamlit.name.split(".")[-1]
                nombre_archivo = f"viaje_{id_viaje}_evidencia.{extension}"
                ruta_foto_final = os.path.join(carpeta_destino, nombre_archivo)
                
                with open(ruta_foto_final, "wb") as f:
                    f.write(archivo_foto_streamlit.getbuffer())

            # 2️⃣ LEER DISTANCIA REAL Y DATOS DEL CHOFER (Ignoramos montos previos tentativos)
            cursor.execute("""
                SELECT cedula_conductor, distancia_km, tipo_viaje 
                FROM viajes 
                WHERE id_viaje = ?
            """, (id_viaje,))
            res_v = cursor.fetchone()
            
            if res_v:
                cedula_chofer = res_v[0]
                # Aseguramos capturar la distancia real guardada en operaciones_viajes.py
                distancia_real = float(res_v[1]) if res_v[1] is not None else 0.0
                tipo_viaje = res_v[2]
                
                # 📊 Recálculo Matemático basado en el kilometraje real verificado
                distancia_calculo = max(distancia_real, 8.0) if distancia_real > 0 else 0.0
                tarifa_por_km = 4.0 if tipo_viaje == 'Express' else 2.5
                monto_flete_total = round(distancia_calculo * tarifa_por_km, 2)
                
                # Buscamos el tipo de unidad del conductor
                cursor.execute("SELECT propio FROM conductores WHERE cedula = ?", (cedula_chofer,))
                res_c = cursor.fetchone()
                es_propio = res_c[0] if res_c and res_c[0] else "No"
                
                # Fórmulas Financieras Oficiales de ExpreX
                descuento = round(monto_flete_total * 0.15, 2)
                importe_neto = round(monto_flete_total - descuento, 2)
                porcentaje_chofer = 0.75 if es_propio == "Sí" else 0.37
                pago_chofer = round(importe_neto * porcentaje_chofer, 2)
                beneficio_exprex = round(importe_neto - pago_chofer, 2)
                
                # 💾 Inyección total y cierre definitivo de la Hoja de Ruta
                sql_update = """
                    UPDATE viajes 
                    SET estatus_viaje = 'Entregado', 
                        foto_evidencia = ?, 
                        monto_flete_usd = ?,
                        descuento_usd = ?,
                        importe_neto_usd = ?, 
                        pago_chofer_usd = ?, 
                        beneficio_exprex_usd = ?  
                    WHERE id_viaje = ?
                """
                cursor.execute(sql_update, (
                    ruta_foto_final, monto_flete_total, descuento, 
                    importe_neto, pago_chofer, beneficio_exprex, id_viaje
                ))
                conexion.commit()
            else:
                st.error("❌ No se encontraron datos para procesar el flete financiero.")
                conexion.close()
                return False
                
        else:
            # 🚛 Para cualquier otro estatus (ej. 'En Ruta' desde el móvil o 'Asignado' en PC)
            cursor.execute("""
                UPDATE viajes 
                SET estatus_viaje = ? 
                WHERE id_viaje = ?
            """, (nuevo_estatus, id_viaje))
            conexion.commit()
            
        conexion.close()
        return True
        
    except Exception as e:
        st.error(f"❌ Error en el módulo maestro de actualización: {e}")
        return False
