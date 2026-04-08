import pandas as pd
import requests
from datetime import datetime, timedelta
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN MAESTRA ---
BASE_TUNNEL_URL = "https://cotemporaneous-lory-semitruthfully.ngrok-free.dev"
ADMIN_EMAIL = "richard.guevara@greenmovil.com.co"

# Mapeo de PIR (Puntos de inicio)
MAPEO_PIR = {
    "Puerta de Teja": ["H317", "L328", "KB326"],
    "Puente Grande": ["G311", "H308", "H327"],
    "Recodo": ["A003", "KA332"],
    "Brisas 1": ["L331", "B314", "H318", "L325"],
    "Brisas 2": ["L329", "L312", "KA324"]
}

# Clasificación EXACTA según imagen image_0396ca.png
RUTAS_ZMO_III = ["H317", "L328", "KB326", "H308", "L329", "L312", "KA324","A003","A332"]
RUTAS_ZMO_V = ["G311", "H327", "KA332", "L331", "B314", "H318", "L325"]

HEADERS_BYPASS = {"ngrok-skip-browser-warning": "true", "Accept": "application/json"}
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_usuarios():
    try:
        df = conn.read(worksheet="USUARIOS", ttl=0)
        df.columns = [str(c).lower().strip() for c in df.columns]
        df = df.rename(columns={df.columns[0]: 'correo', df.columns[3]: 'pw', df.columns[4]: 'rol'})
        df['correo'] = df['correo'].astype(str).str.lower().str.strip()
        users_dict = df.set_index('correo').to_dict('index')
        if ADMIN_EMAIL in users_dict: users_dict[ADMIN_EMAIL]['rol'] = 'admin'
        return users_dict
    except:
        return {ADMIN_EMAIL: {"nombre": "Richard Guevara", "cargo": "Coordinador", "pw": "Admin2026", "rol": "admin"}}

def obtener_listado_buses_drive():
    try:
        df = conn.read(worksheet="VEHICULOS", ttl=0)
        df.columns = [str(c).strip() for c in df.columns]
        df['label'] = df['Código'].astype(str) + " | " + df['Placa'].astype(str)
        return df
    except: return pd.DataFrame()

def aplicar_gestion_servicio(datos, usuario):
    try:
        # 1. GESTION_OPERATIVA: Agregamos columnas de control Programado vs Real
        try: df_hist = conn.read(worksheet="GESTION_OPERATIVA", ttl=0)
        except: df_hist = pd.DataFrame()
        
        nueva_fila = pd.DataFrame([{
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "servbus": str(datos['servbus']),
            "bus_programado": datos['bus_prog'],
            "bus_real": datos['bus_real'],
            "motivo_movil": datos['motivo_movil'],
            "ope_programado": datos['ope_prog'],
            "ope_real": datos['ope_real'],
            "motivo_ope": datos['motivo_ope'],
            "eliminar_km": datos['eliminar_km'],
            "observacion_final": datos['obs_final'],
            "gestionado_por": usuario
        }])
        df_hist_final = pd.concat([df_hist, nueva_fila], ignore_index=True)
        conn.update(worksheet="GESTION_OPERATIVA", data=df_hist_final)

        # 2. PRG_MASTER: Actualizamos para que cambie en la pantalla principal
        df_master = conn.read(worksheet="PRG_MASTER", ttl=0)
        mask = df_master['servbus'].astype(str) == str(datos['servbus'])
        if mask.any():
            df_master.loc[mask, 'bus_prog'] = datos['bus_real']
            df_master.loc[mask, 'ope_prog'] = datos['ope_real']
            conn.update(worksheet="PRG_MASTER", data=df_master)
            return True
        return False
    except: return False

def sincronizar_semana_por_dias(f_ini, f_fin):
    auth_app, data_auth = ('rigelWS', 'rigelWS2021'), {'username': 'nospina', 'password': 'ospina2023', 'grant_type': 'password'}
    try:
        r_t = requests.post(f"{BASE_TUNNEL_URL}/ws/oauth/token", data=data_auth, auth=auth_app, timeout=15, verify=False, headers=HEADERS_BYPASS)
        token = r_t.json().get('access_token')
    except: return False, "Error Rigel"
    
    f_dt_ini, f_dt_fin = pd.to_datetime(f_ini), pd.to_datetime(f_fin)
    delta = (f_dt_fin - f_dt_ini).days + 1
    lista_total = []
    status_p = st.empty()
    
    for i in range(delta):
        fecha_t = (f_dt_ini + timedelta(days=i)).strftime('%Y-%m-%d')
        status_p.info(f"⏳ Descargando: {fecha_t}...")
        url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{fecha_t}/{fecha_t}/0"
        try:
            r = requests.get(url, headers={**HEADERS_BYPASS, 'Authorization': f'Bearer {token}'}, timeout=30, verify=False)
            if r.status_code == 200 and r.json():
                df_dia = pd.DataFrame(r.json()); df_dia['fecha'] = fecha_t; lista_total.append(df_dia)
        except: continue
    
    if not lista_total: return False, "Sin datos"
    df_full = pd.concat(lista_total, ignore_index=True)
    df_full['ruta'] = df_full['tipoTarea'].astype(str).str.split('_').str[0].str.strip().str[:5]
    df_full['punto_pir'] = df_full['ruta'].apply(lambda x: next((k for k, v in MAPEO_PIR.items() if any(r in x for r in v)), "Otros"))
    df_full['tabla'] = df_full['tabla'].astype(str).replace('None', 'N/A')
    
    # Lógica de Empresa basada en tu listado
    df_full['empresa'] = df_full['ruta'].apply(lambda x: "ZMO III" if x in RUTAS_ZMO_III else ("ZMO V" if x in RUTAS_ZMO_V else "Otros"))
    
    cols = ['fecha', 'servbus', 'timeOrigin', 'ruta', 'tabla', 'codigoBus', 'nombre', 'km', 'codigoTm', 'punto_pir', 'empresa']
    df_res = df_full[cols].rename(columns={'codigoBus': 'bus_prog', 'nombre': 'ope_prog'})
    conn.update(worksheet="PRG_MASTER", data=df_res)
    return True, "Sincronización Exitosa"

def cargar_datos_pantalla():
    try:
        df = conn.read(worksheet="PRG_MASTER", ttl=0)
        # Re-validar empresa si la columna falta
        if not df.empty and 'empresa' not in df.columns:
            df['empresa'] = df['ruta'].apply(lambda x: "ZMO III" if str(x) in RUTAS_ZMO_III else "ZMO V")
        return df
    except: return pd.DataFrame()
