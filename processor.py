import pandas as pd
import requests
from datetime import datetime, timedelta
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import urllib3
import json
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
BASE_TUNNEL_URL = "https://cotemporaneous-lory-semitruthfully.ngrok-free.dev"
USERS_FILE = "usuarios.json"
ADMIN_EMAIL = "richard.guevara@greenmovil.com.co"

# Mapeo de rutas a Puntos PIR
MAPEO_PIR = {
    "Puerta de Teja": ["H317", "L328", "B326"],
    "Puente Grande": ["G311", "H308", "H327"],
    "Recodo": ["A003", "A332"],
    "Brisas 1": ["L331", "B314", "H318", "L325"],
    "Brisas 2": ["L329", "L312", "K324"]
}

# Headers para saltar el muro de Ngrok
HEADERS_BYPASS = {
    "ngrok-skip-browser-warning": "true",
    "Accept": "application/json"
}

# Conexión a Google Sheets (Usa los Secrets de Streamlit)
conn = st.connection("gsheets", type=GSheetsConnection)

def inicializar_gsheet():
    """Esta función la llama app.py al iniciar para verificar la conexión."""
    try:
        # Intenta leer la pestaña PRG_MASTER
        conn.read(worksheet="PRG_MASTER", ttl=0)
    except:
        st.warning("Pestaña PRG_MASTER no encontrada. Se creará al sincronizar por primera vez.")

def inicializar_sistema():
    """Mantiene la compatibilidad con la creación de usuarios local."""
    if not os.path.exists(USERS_FILE):
        db_inicial = {ADMIN_EMAIL: {"nombre": "Richard Guevara", "cargo": "Administrador de Operaciones", "pw": "admin2026", "rol": "admin"}}
        with open(USERS_FILE, 'w') as f: json.dump(db_inicial, f, indent=4)

def obtener_usuarios():
    if not os.path.exists(USERS_FILE): inicializar_sistema()
    with open(USERS_FILE, 'r') as f: return json.load(f)

def guardar_usuario(correo, nombre, cargo, pw):
    db = obtener_usuarios()
    rol = "pro" if any(x in cargo for x in ["Profesional", "Administrador"]) else "auxiliar"
    db[correo.lower().strip()] = {"nombre": nombre, "cargo": cargo, "pw": pw, "rol": rol}
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
    """Descarga de Rigel y guarda en la hoja PRG_MASTER de Google Sheets."""
    token = obtener_token()
    if not token: return False
    
    url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{f_ini}/{f_fin}/0"
    headers = {**HEADERS_BYPASS, 'Authorization': f'Bearer {token}'}
    
    try:
        r = requests.get(url, headers=headers, timeout=60, verify=False)
        raw = r.json()
        if not raw: return False
        
        df_nuevo = pd.DataFrame(raw)
        # Limpieza y formateo
        df_nuevo['ruta'] = df_nuevo['tipoTarea'].astype(str).str.split('_').str[0].str.strip().str[:5]
        df_nuevo['punto_pir'] = df_nuevo['ruta'].apply(lambda x: next((k for k, v in MAPEO_PIR.items() if any(r in x for r in v)), "Otros"))
        df_nuevo['tabla'] = df_nuevo['tabla'].astype(str).replace('None', 'N/A')
        
        # Seleccionamos columnas para el Excel
        cols = ['servbus', 'timeOrigin', 'ruta', 'tabla', 'codigoBus', 'nombre', 'km', 'codigoTm', 'punto_pir']
        df_final = df_nuevo[cols].rename(columns={'codigoBus': 'bus_prog', 'nombre': 'ope_prog'})
        
        # Actualizar Google Sheets
        conn.update(worksheet="PRG_MASTER", data=df_final)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def cargar_datos_pantalla():
    """Lee del Excel lo que se va a mostrar."""
    try:
        return conn.read(worksheet="PRG_MASTER", ttl=0)
    except:
        return pd.DataFrame()

def registrar_ejecucion_gsheet(datos_gestion, usuario):
    """Guarda un cambio en la hoja EJECUCION."""
    try:
        try:
            df_ejec = conn.read(worksheet="EJECUCION", ttl=0)
        except:
            df_ejec = pd.DataFrame(columns=["fecha_ejec", "servbus", "bus_real", "ope_real", "soc", "estado", "gestionado_por"])
        
        nueva_fila = pd.DataFrame([{
            "fecha_ejec": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "servbus": str(datos_gestion['servbus']),
            "bus_real": datos_gestion['bus_real'],
            "ope_real": datos_gestion['ope_real'],
            "soc": datos_gestion['soc'],
            "estado": datos_gestion['estado'],
            "gestionado_por": usuario
        }])
        
        df_final = pd.concat([df_ejec, nueva_fila], ignore_index=True)
        conn.update(worksheet="EJECUCION", data=df_final)
        return True
    except:
        return False
