import pandas as pd
import requests
from datetime import datetime, timedelta
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
BASE_TUNNEL_URL = "https://cotemporaneous-lory-semitruthfully.ngrok-free.dev"
# Los Secrets de Streamlit manejarán la conexión real, pero definimos el link por si acaso
URL_SHEET = "https://docs.google.com/spreadsheets/d/15bhEUubJKdxpaKujNFo_aSShIPQAova-ffMR92vhiOc/edit"

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_token():
    auth_app = ('rigelWS', 'rigelWS2021')
    data_auth = {'username': 'nospina', 'password': 'ospina2023', 'grant_type': 'password'}
    try:
        url = f"{BASE_TUNNEL_URL}/ws/oauth/token"
        headers = {"ngrok-skip-browser-warning": "true"}
        r = requests.post(url, data=data_auth, auth=auth_app, timeout=15, verify=False, headers=headers)
        return r.json().get('access_token') if r.status_code == 200 else None
    except: return None

def sincronizar_rango_rigel(f_ini, f_fin):
    """Descarga de Rigel y guarda en la hoja PRG_MASTER de Google Sheets."""
    token = obtener_token()
    if not token: 
        st.error("No se pudo obtener el Token de Rigel. ¿Está el túnel y la VPN activos?")
        return False
    
    # Rigel a veces prefiere consultas día por día para no saturar
    # Aquí lo haremos simple por el rango solicitado
    url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{f_ini}/{f_fin}/0"
    headers = {"ngrok-skip-browser-warning": "true", 'Authorization': f'Bearer {token}'}
    
    try:
        r = requests.get(url, headers=headers, timeout=60, verify=False)
        raw = r.json()
        if not raw: return False
        
        # Formatear para nuestro Excel
        df_nuevo = pd.DataFrame(raw)
        df_nuevo['fecha_consulta'] = f_ini # O la fecha que retorne el registro
        df_nuevo['ruta'] = df_nuevo['tipoTarea'].astype(str).str[:5]
        
        cols_finales = ['servbus', 'timeOrigin', 'ruta', 'tabla', 'codigoBus', 'nombre', 'km', 'codigoTm']
        df_sub = df_nuevo[cols_finales].copy()
        df_sub['fecha_registro'] = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Leer lo que ya hay en el Excel para no duplicar
        try:
            df_existente = conn.read(worksheet="PRG_MASTER")
            df_final = pd.concat([df_existente, df_sub]).drop_duplicates(subset=['servbus'])
        except:
            df_final = df_sub

        # Actualizar Google Sheets
        conn.update(worksheet="PRG_MASTER", data=df_final)
        return True
    except Exception as e:
        st.error(f"Error en la sincronización: {e}")
        return False

def cargar_datos_pantalla():
    """Lee del Excel lo que se va a mostrar hoy."""
    try:
        df_prg = conn.read(worksheet="PRG_MASTER")
        # Aquí podrías filtrar por la fecha de hoy si en PRG_MASTER guardas la fecha del servicio
        return df_prg
    except:
        return pd.DataFrame()
