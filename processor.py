import pandas as pd
import requests
from datetime import datetime
import streamlit as st
from streamlit_gsheets import GSheetsConnection
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
BASE_TUNNEL_URL = "https://cotemporaneous-lory-semitruthfully.ngrok-free.dev"
URL_SHEET = "https://docs.google.com/spreadsheets/d/15bhEUubJKdxpaKujNFo_aSShIPQAova-ffMR92vhiOc/edit#gid=0"

# Conexión a Google Sheets
conn_gs = st.connection("gsheets", type=GSheetsConnection)

def inicializar_gsheet():
    """Crea las pestañas y encabezados si el archivo está virgen."""
    # Columnas necesarias
    cols_prg = ["fecha", "servbus", "timeOrigin", "ruta", "tabla", "bus_prog", "ope_prog", "km"]
    cols_ejec = ["fecha_ejec", "servbus", "bus_real", "ope_real", "soc", "estado", "gestionado_por"]
    cols_auditoria = ["timestamp", "usuario", "accion", "detalle"]

    try:
        # Intentamos leer la primera hoja para ver si hay algo
        conn_gs.read(worksheet="PRG_MASTER", ttl=0)
    except:
        # Si falla, es que no existen. Aquí las inicializamos (esto requiere permisos de escritura)
        st.warning("Configurando tablas en Google Sheets por primera vez...")
        # Nota: La creación de pestañas inicial se hace mejor manualmente una vez, 
        # pero el código puede escribir los encabezados.
        pass

def sincronizar_semana_rigel(fecha_inicio, fecha_fin):
    """Descarga de Rigel y guarda en PRG_MASTER de Google Sheets."""
    import processor # Para el token
    token = processor.obtener_token()
    if not token: return False
    
    url = f"{BASE_TUNNEL_URL}/ws/reportes/semanaActual/{fecha_inicio}/{fecha_fin}/0"
    headers = {"ngrok-skip-browser-warning": "true", 'Authorization': f'Bearer {token}'}
    
    try:
        r = requests.get(url, headers=headers, timeout=30, verify=False)
        datos = r.json()
        if not datos: return False
        
        # Convertir a DataFrame con el formato de nuestra base de datos
        nuevos_registros = []
        for d in datos:
            nuevos_registros.append({
                "fecha": fecha_inicio, # O la fecha real del objeto si Rigel la trae
                "servbus": str(d['servbus']),
                "timeOrigin": d['timeOrigin'],
                "ruta": str(d.get('tipoTarea', ''))[:5],
                "tabla": d.get('tabla', 'N/A'),
                "bus_prog": d['codigoBus'],
                "ope_prog": d['nombre'],
                "km": d['km']
            })
        
        df_nuevo = pd.DataFrame(nuevos_registros)
        
        # Guardar en Google Sheets (PRG_MASTER)
        # Esto añade los datos al final de lo que ya existe
        df_actual = conn_gs.read(worksheet="PRG_MASTER")
        df_final = pd.concat([df_actual, df_nuevo]).drop_duplicates(subset=['servbus', 'fecha'])
        conn_gs.update(worksheet="PRG_MASTER", data=df_final)
        return True
    except:
        return False

def registrar_ejecucion_gsheet(datos_gestion, usuario):
    """Guarda un cambio de bus/ope en la hoja EJECUCION."""
    df_ejec = conn_gs.read(worksheet="EJECUCION")
    
    nueva_fila = pd.DataFrame([{
        "fecha_ejec": datetime.now().strftime("%Y-%m-%d"),
        "servbus": datos_gestion['servbus'],
        "bus_real": datos_gestion['bus_real'],
        "ope_real": datos_gestion['ope_real'],
        "soc": datos_gestion['soc'],
        "estado": datos_gestion['estado'],
        "gestionado_por": usuario
    }])
    
    df_final = pd.concat([df_ejec, nueva_fila])
    conn_gs.update(worksheet="EJECUCION", data=df_final)
