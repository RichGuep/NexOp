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

RUTAS_ZMO_III = ["H317", "L328", "B326", "L329", "L312", "K324", "H308"]
HEADERS_BYPASS = {"ngrok-skip-browser-warning": "true", "Accept": "application/json"}
conn = st.connection("gsheets", type=GSheetsConnection)

def obtener_listado_buses_drive():
    try:
        df = conn.read(worksheet="VEHICULOS", ttl=0)
        df['label'] = df['Código'].astype(str) + " | " + df['Placa'].astype(str)
        return df
    except: return pd.DataFrame()

def obtener_usuarios():
    try:
        df = conn.read(worksheet="USUARIOS", ttl=0)
        df['correo'] = df['correo'].str.lower().str.strip()
        users_dict = df.set_index('correo').to_dict('index')
        if ADMIN_EMAIL in users_dict: users_dict[ADMIN_EMAIL]['rol'] = 'admin'
        return users_dict
    except:
        return {ADMIN_EMAIL: {"nombre": "Richard Guevara", "cargo": "Coordinador", "pw": "Admin2026", "rol": "admin"}}

def registrar_gestion_viaje(datos, usuario):
    try:
        try: df_hist = conn.read(worksheet="GESTION_OPERATIVA", ttl=0)
        except: df_hist = pd.DataFrame()
        nueva = pd.DataFrame([{
            "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "servbus": str(datos['servbus']), "bus_final": datos['bus_final'],
            "bus_adicional": datos['bus_adic'], "motivo_bus": datos['motivo_bus'],
            "ope_final": datos['ope_final'], "motivo_ope": datos['motivo_ope'],
            "eliminar_km": datos['eliminar_km'], "obs_final": datos['obs_final'], "gestionado_por": usuario
        }])
        df_f = pd.concat([df_hist, nueva], ignore_index=True)
        conn.update(worksheet="GESTION_OPERATIVA", data=df_f)
        return True
    except: return False

def sincronizar_semana_por_dias(f_ini, f_fin):
    auth_app, data_auth = ('rigelWS', 'rigelWS2021'), {'username': 'nospina', 'password': 'ospina2023', 'grant_type': 'password'}
    
    # 1. Obtener Token
    try:
        r_t = requests.post(f"{BASE_TUNNEL_URL}/ws/oauth/token", data=data_auth, auth=auth_app, timeout=15, verify=False, headers=HEADERS_BYPASS)
        token = r_t.json().get('access_token')
        if not token: return False, "Error de autenticación con Rigel"
    except: return False, "No se pudo conectar con el servidor de Rigel"
    
    f_dt_ini, f_dt_fin = pd.to_datetime(f_ini), pd.to_datetime(f_fin)
    delta = (f_dt_fin - f_dt_ini).days + 1
    lista_total = []
    
    status_placeholder = st.empty() # Espacio para mensajes de estado
    barra = st.progress(0)
    
    for i in range(delta):
        fecha_t = (f_dt_ini + timedelta(days=i)).strftime('%Y-%m-%d')
        status_placeholder.info(f"⏳ Descargando: {fecha_t}...") # Mensaje de estado
        
        url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{fecha_t}/{fecha_t}/0"
        try:
            r = requests.get(url, headers={**HEADERS_BYPASS, 'Authorization': f'Bearer {token}'}, timeout=30, verify=False)
            if r.status_code == 200 and r.json():
                df_dia = pd.DataFrame(r.json())
                df_dia['fecha'] = fecha_t
                lista_total.append(df_dia)
                status_placeholder.success(f"✅ {fecha_t} descargado correctamente.")
            else:
                status_placeholder.warning(f"⚠️ Sin datos para el día: {fecha_t}")
        except:
            status_placeholder.error(f"❌ Error al descargar el día: {fecha_t}")
            continue
        
        barra.progress((i + 1) / delta)
    
    if not lista_total: return False, "No se encontraron datos en el rango seleccionado"
    
    status_placeholder.info("📊 Procesando y subiendo a Google Sheets...")
    df_full = pd.concat(lista_total, ignore_index=True)
    df_full['ruta'] = df_full['tipoTarea'].astype(str).str.split('_').str[0].str.strip().str[:5]
    df_full['punto_pir'] = df_full['ruta'].apply(lambda x: next((k for k, v in MAPEO_PIR.items() if any(r in x for r in v)), "Otros"))
    df_full['tabla'] = df_full['tabla'].astype(str).replace('None', 'N/A')
    df_full['empresa'] = df_full['ruta'].apply(lambda x: "ZMO III" if x in RUTAS_ZMO_III else "ZMO V")
    
    cols = ['fecha', 'servbus', 'timeOrigin', 'ruta', 'tabla', 'codigoBus', 'nombre', 'km', 'codigoTm', 'punto_pir', 'empresa']
    df_res = df_full[cols].rename(columns={'codigoBus': 'bus_prog', 'nombre': 'ope_prog'})
    
    conn.update(worksheet="PRG_MASTER", data=df_res)
    status_placeholder.success("🎊 ¡Descarga y Sincronización completa!")
    return True, "Proceso finalizado con éxito"

def cargar_datos_pantalla():
    try:
        df = conn.read(worksheet="PRG_MASTER", ttl=0)
        if not df.empty and 'empresa' not in df.columns:
            df['empresa'] = df['ruta'].apply(lambda x: "ZMO III" if str(x)[:5] in RUTAS_ZMO_III else "ZMO V")
        return df
    except: return pd.DataFrame()
