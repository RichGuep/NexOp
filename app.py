import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import processor

ADMIN_EMAIL = "richard.guevara@greenmovil.com.co"
st.set_page_config(page_title="NexOp | Green Móvil", layout="wide", page_icon="⚡")

# --- ESTILO ---
st.markdown("<style>@import url('https://fonts.cdnfonts.com/css/century-gothic'); * { font-family: 'Century Gothic', sans-serif !important; } .stApp { background-color: #fcfdfc; } .main-header { background: linear-gradient(90deg, #1a531f 0%, #2e7d32 100%); padding: 20px; border-radius: 12px; color: white; text-align: center; margin-bottom: 25px; } .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1a531f; box-shadow: 0 2px 8px rgba(0,0,0,0.05); } .stTabs [aria-selected='true'] { background-color: #1a531f !important; color: white !important; }</style>", unsafe_allow_html=True)

if "auth" not in st.session_state: st.session_state.auth = False

# --- LOGIN ---
if not st.session_state.auth:
    c2 = st.columns([1,1.2,1])[1]
    with c2:
        st.markdown('<div class="main-header"><h1>NexOp Access</h1></div>', unsafe_allow_html=True)
        u = st.text_input("Usuario").lower().strip()
        p = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            users = processor.obtener_usuarios()
            if u in users and str(users[u]["pw"]) == p:
                st.session_state.auth = True; st.session_state.user_info = users[u]; st.rerun()
            else: st.error("Acceso Denegado")
    st.stop()

# --- APP ---
st.markdown('<div class="main-header"><h1>NexOp | Green Móvil</h1></div>', unsafe_allow_html=True)
df = processor.cargar_datos_pantalla()
u_info = st.session_state.user_info
is_admin = (u_info.get('correo') == ADMIN_EMAIL or u_info.get('rol') == 'admin')

tabs = st.tabs(["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO", "⚙️ CONFIG"] if is_admin else ["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO"])

st.sidebar.markdown(f"👤 **{u_info.get('nombre', 'Usuario')}**")
st.sidebar.caption(f"Cargo: {u_info.get('cargo', 'N/A')}")

if not df.empty:
    st.sidebar.subheader("🔍 Filtros")
    f_sel = st.sidebar.selectbox("📅 Día Operativo:", sorted(df['fecha'].unique().tolist()))
    df_f = df[df['fecha'] == f_sel].copy()
    
    # Filtro Turno
    df_f['temp_hora'] = pd.to_datetime(df_f['timeOrigin']).dt.hour
    turno = st.sidebar.radio("⏱️ Turno:", ["Completo", "Mañana (06:00-14:00)", "Tarde (14:00-22:00)"])
    if "Mañana" in turno: df_f = df_f[(df_f['temp_hora'] >= 6) & (df_f['temp_hora'] < 14)]
    elif "Tarde" in turno: df_f = df_f[(df_f['temp_hora'] >= 14) & (df_f['temp_hora'] < 22)]

    # ... (Resto de filtros de PIR y Ruta igual que antes) ...

    with tabs[1]: # GESTIÓN
        st.info(f"Consola PIR - {f_sel}")
        # Definición de columnas a mostrar
        cols_v = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'empresa', 'servbus']
        st.dataframe(df_f[cols_v], use_container_width=True, hide_index=True)
    
    with tabs[2]: st.dataframe(df_f.drop(columns=['temp_hora']), use_container_width=True, hide_index=True)

# --- PESTAÑA CONFIG (CORREGIDA PARA EVITAR REINICIOS) ---
if is_admin:
    with tabs[-1]:
        st.subheader("⚙️ Configuración de Descarga Rigel")
        
        with st.form("descarga_form"):
            col1, col2 = st.columns(2)
            f_inicio = col1.date_input("Fecha Inicio", value=datetime.now())
            f_fin = col2.date_input("Fecha Fin", value=datetime.now())
            
            submit = st.form_submit_button("🚀 INICIAR DESCARGA", use_container_width=True)
            
            if submit:
                if f_inicio > f_fin:
                    st.error("La fecha de inicio no puede ser mayor a la de fin.")
                else:
                    success, mensaje = processor.sincronizar_semana_por_dias(str(f_inicio), str(f_fin))
                    if success:
                        st.balloons()
                        st.success(mensaje)
                        # st.rerun() # Opcional: reiniciar para ver datos nuevos
                    else:
                        st.error(mensaje)

if st.sidebar.button("Cerrar Sesión"): st.session_state.auth = False; st.rerun()
