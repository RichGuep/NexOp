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
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_token():
    auth_app = ('rigelWS', 'rigelWS2021')
    data_auth = {'username': 'nospina', 'password': 'ospina2023', 'grant_type': 'password'}
    try:
        url = f"{BASE_TUNNEL_URL}/ws/oauth/token"
        r = requests.post(url, data=data_auth, auth=auth_app, timeout=15, verify=False, headers=HEADERS_BYPASS)
        return r.json().get('access_token') if r.status_code == 200 else None
    except: return None

def sincronizar_semana_por_dias(f_ini, f_fin):
    """
    IMPORTANTE: Esta función consulta día por día para evitar que la API 
    recorte la información a un solo día.
    """
    token = obtener_token()
    if not token: return False
    
    # Convertir fechas para el bucle
    f_dt_ini = pd.to_datetime(f_ini)
    f_dt_fin = pd.to_datetime(f_fin)
    dias_a_consultar = (f_dt_fin - f_dt_ini).days + 1
    
    lista_total = []
    barra = st.progress(0)
    status_text = st.empty()

    for i in range(dias_a_consultar):
        fecha_target = (f_dt_ini + timedelta(days=i)).strftime('%Y-%m-%d')
        status_text.text(f"⏳ Descargando Rigel: {fecha_target}...")
        
        # Consultamos el día exacto (ini y fin iguales)
        url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{fecha_target}/{fecha_target}/0"
        headers_f = {**HEADERS_BYPASS, 'Authorization': f'Bearer {token}'}
        
        try:
            r = requests.get(url, headers=headers_f, timeout=30, verify=False)
            if r.status_code == 200 and r.json():
                df_dia = pd.DataFrame(r.json())
                df_dia['fecha'] = fecha_target
                lista_total.append(df_dia)
        except Exception as e:
            st.warning(f"No se pudo obtener datos del día {fecha_target}")
        
        barra.progress((i + 1) / dias_a_consultar)

    if not lista_total: 
        st.error("No se recolectó ningún dato de Rigel.")
        return False
    
    # Unimos todos los días en un solo DataFrame
    df_full = pd.concat(lista_total, ignore_index=True)
    
    # Limpieza y Mapeo
    df_full['ruta'] = df_full['tipoTarea'].astype(str).str.split('_').str[0].str.strip().str[:5]
    df_full['punto_pir'] = df_full['ruta'].apply(lambda x: next((k for k, v in MAPEO_PIR.items() if any(r in x for r in v)), "Otros"))
    df_full['tabla'] = df_full['tabla'].astype(str).replace('None', 'N/A')
    
    cols = ['fecha', 'servbus', 'timeOrigin', 'ruta', 'tabla', 'codigoBus', 'nombre', 'km', 'codigoTm', 'punto_pir']
    df_final = df_full[cols].rename(columns={'codigoBus': 'bus_prog', 'nombre': 'ope_prog'})
    df_final['servbus'] = df_final['servbus'].astype(str)

    # --- GUARDADO EN DRIVE ---
    # 1. Maestro General
    conn.update(worksheet="PRG_MASTER", data=df_final)
    
    # 2. Hojas por Ruta (Orden en el Drive)
    rutas = df_final['ruta'].unique()
    for r in rutas:
        df_r = df_final[df_final['ruta'] == r]
        try:
            # Intentamos actualizar la pestaña con el nombre de la ruta
            conn.update(worksheet=str(r), data=df_r)
        except:
            # Si la pestaña no existe, el programa sigue para no bloquearse
            pass
            
    status_text.text("✅ ¡Sincronización Completa!")
    return True

def cargar_datos_pantalla():
    try: return conn.read(worksheet="PRG_MASTER", ttl=0)
    except: return pd.DataFrame()
