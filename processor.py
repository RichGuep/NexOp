import pandas as pd
import requests
from datetime import datetime, time
import os
import json
import urllib3
import time as time_lib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- REEMPLAZA ESTA URL CON LA QUE VEAS EN TU TERMINAL NEGRA (NGROK) ---
# Debe empezar con https:// y terminar en .ngrok-free.dev o .app
BASE_TUNNEL_URL = "https://cotemporaneous-lory-semitruthfully.ngrok-free.dev"

TOKEN_URL = f"{BASE_TUNNEL_URL}/ws/oauth/token"
LOG_PATH = "trazabilidad_novedades.csv"
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

def inicializar_sistema():
    if not os.path.exists("historico"): os.makedirs("historico")
    if not os.path.exists(USERS_FILE):
        db_inicial = {ADMIN_EMAIL: {"nombre": "Richard Guevara", "cargo": "Administrador de Operaciones", "pw": "admin2026", "rol": "admin"}}
        with open(USERS_FILE, 'w') as f: json.dump(db_inicial, f, indent=4)

def obtener_usuarios():
    if not os.path.exists(USERS_FILE): inicializar_sistema()
    with open(USERS_FILE, 'r') as f: return json.load(f)

def obtener_token():
    auth_app = ('rigelWS', 'rigelWS2021')
    data_auth = {'username': 'nospina', 'password': 'ospina2023', 'grant_type': 'password'}
    try:
        r = requests.post(TOKEN_URL, data=data_auth, auth=auth_app, timeout=15, verify=False, headers=HEADERS_BYPASS)
        return r.json().get('access_token') if r.status_code == 200 else None
    except: return None

def cargar_datos_api():
    token = obtener_token()
    if not token: return None
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{fecha_hoy}/{fecha_hoy}/0"
    
    try:
        headers_final = {**HEADERS_BYPASS, 'Authorization': f'Bearer {token}'}
        r = requests.get(url, headers=headers_final, timeout=25, verify=False)
        raw_data = r.json()
        if not raw_data: return pd.DataFrame()
        
        df = pd.DataFrame(raw_data)
        if 'tabla' in df.columns:
            df['tabla'] = df['tabla'].astype(str).replace('None', 'N/A')
        else:
            df['tabla'] = "N/A"

        df['rutaLimpia'] = df['tipoTarea'].astype(str).apply(lambda x: x.split('_')[0].split(' ')[0].strip()[:5])
        df['hora_dt'] = pd.to_datetime(df['timeOrigin'], format='%H:%M:%S', errors='coerce').dt.time
        df['km'] = pd.to_numeric(df['km'], errors='coerce').fillna(0) / 1000
        df['punto_pir'] = df['rutaLimpia'].apply(lambda x: next((k for k, v in MAPEO_PIR.items() if any(r in x for r in v)), "Otros"))
        
        df['bus_real'] = df['codigoBus']; df['ope_real'] = df['nombre']
        df['estado_gestion'] = "PROGRAMADO"; df['soc_salida'] = "---"; df['km_ejecutado'] = 0.0; df['soc_num'] = 0
        
        return df
    except: return None

def registrar_novedad(tipo, datos, nombre_usuario):
    datos['fecha_registro'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    datos['tipo_evento'] = tipo
    datos['gestionado_por'] = nombre_usuario
    pd.DataFrame([datos]).to_csv(LOG_PATH, mode='a', index=False, header=not os.path.exists(LOG_PATH), sep=';')
