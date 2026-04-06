import pandas as pd
import requests
from datetime import datetime, time
import os
import json
import urllib3
import time as time_lib

# Desactivar advertencias de certificados (necesario para conexiones por túnel/VPN)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN DE URLS (NGROK TUNNEL) ---
# Esta es la URL que generaste en tu terminal negra
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

def inicializar_sistema():
    if not os.path.exists("historico"): os.makedirs("historico")
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
        # Petición a través del túnel
        r = requests.post(TOKEN_URL, data=data_auth, auth=auth_app, timeout=15, verify=False)
        return r.json().get('access_token') if r.status_code == 200 else None
    except: return None

def registrar_novedad(tipo, datos, nombre_usuario):
    if os.path.exists(LOG_PATH):
        fecha_arch = datetime.fromtimestamp(os.path.getmtime(LOG_PATH)).date()
        if datetime.now().date() > fecha_arch:
            os.rename(LOG_PATH, f"historico/novedades_{fecha_arch}.csv")
    datos['fecha_registro'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    datos['tipo_evento'] = tipo
    datos['gestionado_por'] = nombre_usuario
    pd.DataFrame([datos]).to_csv(LOG_PATH, mode='a', index=False, header=not os.path.exists(LOG_PATH), sep=';')

def cargar_datos_api():
    token = obtener_token()
    if not token: return None
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    # URL de reportes actualizada con el túnel
    url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{fecha_hoy}/{fecha_hoy}/0"
    
    try:
        r = requests.get(url, headers={'Authorization': f'Bearer {token}'}, timeout=25, verify=False)
        raw_data = r.json()
        if not raw_data: return pd.DataFrame()
        
        df = pd.DataFrame(raw_data)
        
        # --- VALIDACIÓN DIRECTA DE COLUMNA TABLA ---
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
        
        if os.path.exists(LOG_PATH):
            try:
                df_log = pd.read_csv(LOG_PATH, sep=';', on_bad_lines='skip')
                for _, row in df_log.iterrows():
                    sid = str(row['servbus'])
                    mask = df['servbus'] == sid
                    if any(mask):
                        quien, tipo_e = row.get('gestionado_por', 'Sistema'), row.get('tipo_evento', 'EVENTO')
                        if tipo_e in ["DESPACHO", "RETOMA"]:
                            df.loc[mask, 'estado_gestion'] = f"✅ {tipo_e} ({quien})"
                            df.loc[mask, 'bus_real'] = row.get('bus_nue')
                            df.loc[mask, 'ope_real'] = row.get('ope_nue')
                            df.loc[mask, 'soc_salida'] = str(row.get('soc', '100%'))
                            df.loc[mask, 'km_ejecutado'] = df.loc[mask, 'km']
                            df.loc[mask, 'soc_num'] = row.get('soc_num', 100)
                        elif tipo_e == "ELIMINACION":
                            df.loc[mask, 'estado_gestion'] = f"❌ ELIMINADO ({quien})"
            except: pass
        return df
    except: return None