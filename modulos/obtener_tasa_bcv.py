import streamlit as st
import sqlite3
import requests
from bs4 import BeautifulSoup
import urllib3

# Desactivar advertencias de SSL inseguro (ya que usas verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================================================================
# 🕵️‍♂️ FUNCIÓN DE WEB SCRAPING PARA EL BANCO CENTRAL DE VENEZUELA
# =========================================================================
def obtener_tasa_bcv_en_vivo():
    """Intenta leer la tasa del dólar directo de la web oficial del BCV."""
    try:
        url = "https://www.bcv.org.ve/"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            contenedor_dolar = soup.find(id="dolar")
            if contenedor_dolar:
                tasa_texto = contenedor_dolar.find("strong").text.strip()
                tasa_float = float(tasa_texto.replace(",", "."))
                return tasa_float
    except Exception as e:
        # Usamos st.write en consola interna o dejamos el print tradicional de Linux
        print(f"⚠️ Alerta BCV: No se pudo raspar la web ({e}). Usando respaldo de Base de Datos.")
    return None

# =========================================================================
# 🔄 GESTIÓN DE TASA EN BASE DE DATOS
# =========================================================================
def sincronizar_tasa_bcv():
    """Busca la tasa en internet; si la halla, la guarda. Si no, lee la anterior."""
    conn = sqlite3.connect("exprex.db")
    cursor = conn.cursor()
    tasa_bcv_internet = obtener_tasa_bcv_en_vivo()
    
    # 1. Asegurar que la tabla exista
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
    """)

    # 2. Asegurar que exista el registro de la tasa para poder actualizarlo
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor) VALUES ('tasa_bcv', '0')")

    if tasa_bcv_internet:
        cursor.execute("UPDATE configuracion SET valor = ? WHERE clave = 'tasa_bcv'", (str(tasa_bcv_internet),))
        conn.commit()
        st.toast(f"✅ Tasa BCV actualizada automáticamente: {tasa_bcv_internet} Bs.", icon="🚀")
        tasa_final = tasa_bcv_internet
    else:
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'tasa_bcv'")
        tasa_final = float(cursor.fetchone()[0])
        st.toast("📡 Modo Offline: Usando última tasa BCV registrada en sistema.", icon="📦")
        
    conn.close()
    
    # Guardamos la tasa formateada en texto en el session_state global
    st.session_state['tasa_bcv'] = f"{tasa_final:.2f}"
    
    return tasa_final
