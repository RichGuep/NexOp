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

MAPEO_PIR = {
    "Puerta de Teja": ["H317", "L328", "B326"],
    "Puente Grande": ["G311", "H308", "H327"],
    "Recodo": ["A003", "A332"],
    "Brisas 1": ["L331", "B314", "H318", "L325"],
    "Brisas 2": ["L329", "L312", "K324"]
}

HEADERS_BYPASS = {"ngrok-skip-browser-warning": "true", "Accept": "application/json"}

# Conexión a Google Sheets (Asegúrate de tener los Secrets configurados)
conn = st.connection("gsheets", type=GSheetsConnection)

def inicializar_gsheet():
    try: conn.read(worksheet="PRG_MASTER", ttl=0)
    except: pass

def obtener_usuarios():
    if not os.path.exists(USERS_FILE):
        db = {ADMIN_EMAIL: {"nombre": "Richard Guevara", "cargo": "Admin", "pw": "admin2026"}}
        with open(USERS_FILE, 'w') as f: json.dump(db, f, indent=4)
    with open(USERS_FILE, 'r') as f: return json.load(f)

def obtener_token():
    auth_app = ('rigelWS', 'rigelWS2021')
    data_auth = {'username': 'nospina', 'password': 'ospina2023', 'grant_type': 'password'}
    try:
        url = f"{BASE_TUNNEL_URL}/ws/oauth/token"
        r = requests.post(url, data=data_auth, auth=auth_app, timeout=15, verify=False, headers=HEADERS_BYPASS)
        return r.json().get('access_token') if r.status_code == 200 else None
    except: return None

def sincronizar_semana_por_dias(f_ini, f_fin):
    """Consulta día por día para evitar que Rigel devuelva solo el día actual."""
    token = obtener_token()
    if not token: return False
    
    f_dt_ini = pd.to_datetime(f_ini)
    f_dt_fin = pd.to_datetime(f_fin)
    delta_dias = (f_dt_fin - f_dt_ini).days + 1
    
    lista_total = []
    barra = st.progress(0)
    status = st.empty()

    for i in range(delta_dias):
        fecha_t = (f_dt_ini + timedelta(days=i)).strftime('%Y-%m-%d')
        status.text(f"⏳ Extrayendo de Rigel: {fecha_t}...")
        
        # Petición específica para un solo día (ini y fin iguales)
        url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{fecha_t}/{fecha_t}/0"
        headers_f = {**HEADERS_BYPASS, 'Authorization': f'Bearer {token}'}
        
        try:
            r = requests.get(url, headers=headers_f, timeout=30, verify=False)
            if r.status_code == 200 and r.json():
                df_dia = pd.DataFrame(r.json())
                df_dia['fecha'] = fecha_t
                lista_total.append(df_dia)
        except: continue
        
        barra.progress((i + 1) / delta_dias)

    if not lista_total: return False
    
    df_full = pd.concat(lista_total, ignore_index=True)
    
    # Procesamiento y Limpieza
    df_full['ruta'] = df_full['tipoTarea'].astype(str).str.split('_').str[0].str.strip().str[:5]
    df_full['punto_pir'] = df_full['ruta'].apply(lambda x: next((k for k, v in MAPEO_PIR.items() if any(r in x for r in v)), "Otros"))
    df_full['tabla'] = df_full['tabla'].astype(str).replace('None', 'N/A')
    
    cols = ['fecha', 'servbus', 'timeOrigin', 'ruta', 'tabla', 'codigoBus', 'nombre', 'km', 'codigoTm', 'punto_pir']
    df_final = df_full[cols].rename(columns={'codigoBus': 'bus_prog', 'nombre': 'ope_prog'})
    df_final['servbus'] = df_final['servbus'].astype(str)

    # --- GUARDADO MULTI-HOJA EN DRIVE ---
    # 1. Guardar en la hoja Maestra
    conn.update(worksheet="PRG_MASTER", data=df_final)
    
    # 2. Guardar por pestañas de ruta (ej. H317, G311...)
    rutas_encontradas = df_final['ruta'].unique()
    for r in rutas_encontradas:
        df_ruta = df_final[df_final['ruta'] == r]
        try:
            # Intentar actualizar la pestaña. Si no existe en el Drive, fallará silenciosamente.
            conn.update(worksheet=str(r), data=df_ruta)
        except: pass
            
    status.text("✅ ¡Sincronización Semanal Exitosa!")
    return True

def cargar_datos_pantalla():
    try: return conn.read(worksheet="PRG_MASTER", ttl=0)
    except: return pd.DataFrame()

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
