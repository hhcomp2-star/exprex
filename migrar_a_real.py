import sqlite3
import psycopg2
import os

# 1. Conexión a la base de datos temporal (Local)
conn_local = sqlite3.connect('exprex.db')
cursor_local = conn_local.cursor()

# 2. Conexión a la base de datos indestructible (Nube de Railway)
# Reemplaza con la cadena completa que te dé Railway si pruebas localmente
DATABASE_URL = "postgresql://postgres:GEwvrkHjgplcirKtSztYrISoKEqcBdXC@tokaido.proxy.rlwy.net:42381/railway" 

try:
    conn_nube = psycopg2.connect(DATABASE_URL)
    cursor_nube = conn_nube.cursor()
    print("🔋 Conexión exitosa con la base de datos permanente en Railway.")

    # Crear las tablas primero leyendo el archivo de esquema
    with open('esquema_postgres.sql', 'r') as f:
        cursor_nube.execute(f.read())
    conn_nube.commit()
    print("✅ Tablas creadas/verificadas en la nube.")

    # Lista de tablas a migrar de manera ordenada
    tablas = [
        "usuarios", "conductores", "finanzas_personal", "vehiculos", 
        "control_combustible", "combustible", "gastos", "configuracion", 
        "gastos_operativos_viaje", "cxc_independiente", "cxp_independiente", 
        "clientes", "sucursales", "cuentas_por_cobrar", "viajes"
    ]

    for tabla in tablas:
        # Leer datos locales
        cursor_local.execute(f"SELECT * FROM {tabla}")
        filas = cursor_local.fetchall()
        
        if not filas:
            continue
            
        # Obtener nombres de columnas
        cursor_local.execute(f"PRAGMA table_info({tabla})")
        columnas = [col[1] for col in cursor_local.fetchall()]
        
        # Preparar la inserción en Postgres
        nombres_columnas = ", ".join(columnas)
        valores_placeholders = ", ".join(["%s"] * len(columnas))
        
        query_insert = f"INSERT INTO {tabla} ({nombres_columnas}) VALUES ({valores_placeholders}) ON CONFLICT DO NOTHING"
        
        print(f"Migrando {len(filas)} registros de la tabla '{tabla}'...")
        cursor_nube.executemany(query_insert, filas)
        conn_nube.commit()

    print("🚀 ¡MIGRACIÓN COMPLETADA CON ÉXITO! Todos tus datos históricos están a salvo en la nube.")

except Exception as e:
    print(f"❌ Error durante la migración: {e}")
finally:
    cursor_local.close()
    conn_local.close()
    if 'conn_nube' in locals():
        cursor_nube.close()
        conn_nube.close()
