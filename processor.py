import pandas as pd
import requests
from datetime import datetime, timedelta
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import urllib3
import json
import os

# Desactivar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
BASE_TUNNEL_URL = "https://cotemporaneous-lory-semitruthfully.ngrok-free.dev"
USERS_FILE = "usuarios.json"
ADMIN_EMAIL = "richard.guevara@greenmovil.com.co"

MAPEO_PIR = {
    "Puerta de Teja": ["H317", "L328", "B326"],
    "Puente Grande": ["G311", "H308", "H327"],
    "Recodo": ["A003", "A332"],
    "Brisas 1": ["L331", "B314", "H318", "L325"],
    "Brisas 2": ["L329", "L312", "K324"]
}

HEADERS_BYPASS = {
    "ngrok-skip-browser-warning": "true",
    "Accept": "application/json"
}

# Conexión oficial con Service Account
conn = st.connection("gsheets", type=GSheetsConnection)

def inicializar_gsheet():
    try:
        conn.read(worksheet="PRG_MASTER", ttl=0)
    except:
        pass

def obtener_usuarios():
    if not os.path.exists(USERS_FILE):
        db_inicial = {ADMIN_EMAIL: {"nombre": "Richard Guevara", "cargo": "Administrador", "pw": "admin2026"}}
        with open(USERS_FILE, 'w') as f: json.dump(db_inicial, f, indent=4)
    with open(USERS_FILE, 'r') as f: return json.load(f)

def guardar_usuario(correo, nombre, cargo, pw):
    db = obtener_usuarios()
    db[correo.lower().strip()] = {"nombre": nombre, "cargo": cargo, "pw": pw}
    with open(USERS_FILE, 'w') as f: json.dump(db, f, indent=4)

def obtener_token():
    auth_app = ('rigelWS', 'rigelWS2021')
    data_auth = {'username': 'nospina', 'password': 'ospina2023', 'grant_type': 'password'}
    try:
        url = f"{BASE_TUNNEL_URL}/ws/oauth/token"
        r = requests.post(url, data=data_auth, auth=auth_app, timeout=15, verify=False, headers=HEADERS_BYPASS)
        return r.json().get('access_token') if r.status_code == 200 else None
    except: return None

def sincronizar_rango_rigel(f_ini, f_fin):
    """Descarga la semana completa de Rigel y la guarda organizada por fecha."""
    token = obtener_token()
    if not token: return False
    
    # URL para descargar el rango seleccionado
    url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{f_ini}/{f_fin}/0"
    headers_f = {**HEADERS_BYPASS, 'Authorization': f'Bearer {token}'}
    
    try:
        r = requests.get(url, headers=headers_f, timeout=60, verify=False)
        raw = r.json()
        if not raw: return False
        
        df = pd.DataFrame(raw)
        
        # --- PROCESAMIENTO DE FECHAS ---
        # Extraemos la fecha pura (AAAA-MM-DD) del campo timeOrigin de Rigel
        df['fecha'] = pd.to_datetime(df['timeOrigin']).dt.strftime('%Y-%m-%d')
        
        # Limpieza de Rutas y Puntos PIR
        df['ruta'] = df['tipoTarea'].astype(str).str.split('_').str[0].str.strip().str[:5]
        df['punto_pir'] = df['ruta'].apply(lambda x: next((k for k, v in MAPEO_PIR.items() if any(r in x for r in v)), "Otros"))
        df['tabla'] = df['tabla'].astype(str).replace('None', 'N/A')
        
        # Selección de columnas finales para el Excel
        cols = ['fecha', 'servbus', 'timeOrigin', 'ruta', 'tabla', 'codigoBus', 'nombre', 'km', 'codigoTm', 'punto_pir']
        df_final = df[cols].rename(columns={'codigoBus': 'bus_prog', 'nombre': 'ope_prog'})
        df_final['servbus'] = df_final['servbus'].astype(str)

        # SOBRESCRIBIR LA HOJA: Google Sheets guardará todos los días del rango
        conn.update(worksheet="PRG_MASTER", data=df_final)
        return True
    except Exception as e:
        st.error(f"Error técnico en Rigel: {e}")
        return False

def cargar_datos_pantalla():
    try:
        return conn.read(worksheet="PRG_MASTER", ttl=0)
    except:
        return pd.DataFrame()

def registrar_ejecucion_gsheet(datos_gestion, usuario):
    try:
        try: df_ejec = conn.read(worksheet="EJECUCION", ttl=0)
        except: df_ejec = pd.DataFrame(columns=["fecha_ejec", "servbus", "bus_real", "ope_real", "soc", "estado", "gestionado_por"])
        
        nueva_fila = pd.DataFrame([{
            "fecha_ejec": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "servbus": str(datos_gestion['servbus']),
            "bus_real": datos_gestion['bus_real'],
            "ope_real": datos_gestion['ope_real'],
            "soc": datos_gestion['soc'],
            "estado": datos_gestion['estado'],
            "gestionado_por": usuario
        }])
        
        df_f = pd.concat([df_ejec, nueva_fila], ignore_index=True)
        conn.update(worksheet="EJECUCION", data=df_f)
        return True
    except: return False
