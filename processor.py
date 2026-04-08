import pandas as pd
import requests
from datetime import datetime, timedelta
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
BASE_TUNNEL_URL = "https://cotemporaneous-lory-semitruthfully.ngrok-free.dev"
ADMIN_EMAIL = "richard.guevara@greenmovil.com.co"

MAPEO_PIR = {
    "Puerta de Teja": ["H317", "L328", "B326"],
    "Puente Grande": ["G311", "H308", "H327"],
    "Recodo": ["A003", "A332"],
    "Brisas 1": ["L331", "B314", "H318", "L325"],
    "Brisas 2": ["L329", "L312", "K324"]
}

HEADERS_BYPASS = {"ngrok-skip-browser-warning": "true", "Accept": "application/json"}
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_usuarios():
    try:
        df_user = conn.read(worksheet="USUARIOS", ttl=0)
        df_user['correo'] = df_user['correo'].str.lower().str.strip()
        users_dict = df_user.set_index('correo').to_dict('index')
        # Llave maestra para Richard
        if ADMIN_EMAIL in users_dict: users_dict[ADMIN_EMAIL]['rol'] = 'admin'
        return users_dict
    except:
        return {ADMIN_EMAIL: {"nombre": "Richard Guevara", "cargo": "Coordinador", "pw": "Admin2026", "rol": "admin"}}

def guardar_usuario(correo, nombre, cargo, pw):
    try:
        df_actual = conn.read(worksheet="USUARIOS", ttl=0)
        admins_keywords = ["Profesional", "Supervisor", "Coordinador"]
        rol_asignado = "admin" if any(kw in cargo for kw in admins_keywords) else "user"
        nuevo = pd.DataFrame([{"correo": correo.lower().strip(), "nombre": nombre, "cargo": cargo, "pw": str(pw), "rol": rol_asignado}])
        df_final = pd.concat([df_actual, nuevo], ignore_index=True).drop_duplicates(subset=['correo'], keep='last')
        conn.update(worksheet="USUARIOS", data=df_final)
        return True
    except: return False

def registrar_gestion_viaje(datos, usuario):
    try:
        try: df_hist = conn.read(worksheet="GESTION_OPERATIVA", ttl=0)
        except: df_hist = pd.DataFrame(columns=["fecha_registro", "servbus", "bus_final", "ope_final", "motivo", "eliminar_km", "observaciones", "gestionado_por"])
        nueva_gest = pd.DataFrame([{"fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"), "servbus": str(datos['servbus']), "bus_final": datos['bus_final'], "ope_final": datos['ope_final'], "motivo": datos['motivo'], "eliminar_km": datos['eliminar_km'], "observaciones": datos['obs'], "gestionado_por": usuario}])
        df_f = pd.concat([df_hist, nueva_gest], ignore_index=True)
        conn.update(worksheet="GESTION_OPERATIVA", data=df_f)
        return True
    except: return False

def sincronizar_semana_por_dias(f_ini, f_fin):
    auth_app, data_auth = ('rigelWS', 'rigelWS2021'), {'username': 'nospina', 'password': 'ospina2023', 'grant_type': 'password'}
    try:
        r_t = requests.post(f"{BASE_TUNNEL_URL}/ws/oauth/token", data=data_auth, auth=auth_app, timeout=15, verify=False, headers=HEADERS_BYPASS)
        token = r_t.json().get('access_token')
    except: return False
    
    f_dt_ini, f_dt_fin = pd.to_datetime(f_ini), pd.to_datetime(f_fin)
    delta = (f_dt_fin - f_dt_ini).days + 1
    lista_total = []
    barra = st.progress(0)
    for i in range(delta):
        fecha_t = (f_dt_ini + timedelta(days=i)).strftime('%Y-%m-%d')
        url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{fecha_t}/{fecha_t}/0"
        try:
            r = requests.get(url, headers={**HEADERS_BYPASS, 'Authorization': f'Bearer {token}'}, timeout=30, verify=False)
            if r.status_code == 200 and r.json():
                df_dia = pd.DataFrame(r.json()); df_dia['fecha'] = fecha_t; lista_total.append(df_dia)
        except: continue
        barra.progress((i + 1) / delta)
    
    if not lista_total: return False
    df_full = pd.concat(lista_total, ignore_index=True)
    df_full['ruta'] = df_full['tipoTarea'].astype(str).str.split('_').str[0].str.strip().str[:5]
    df_full['punto_pir'] = df_full['ruta'].apply(lambda x: next((k for k, v in MAPEO_PIR.items() if any(r in x for r in v)), "Otros"))
    df_full['tabla'] = df_full['tabla'].astype(str).replace('None', 'N/A')
    
    # Mantenemos las columnas originales para el Drive
    cols = ['fecha', 'servbus', 'timeOrigin', 'ruta', 'tabla', 'codigoBus', 'nombre', 'km', 'codigoTm', 'punto_pir']
    df_res = df_full[cols].rename(columns={'codigoBus': 'bus_prog', 'nombre': 'ope_prog'})
    conn.update(worksheet="PRG_MASTER", data=df_res)
    return True

def cargar_datos_pantalla():
    try: return conn.read(worksheet="PRG_MASTER", ttl=0)
    except: return pd.DataFrame()
