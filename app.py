import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import processor

APP_NAME = "NexOp | Green Móvil"
st.set_page_config(page_title=APP_NAME, layout="wide", page_icon="⚡")

try: processor.inicializar_gsheet()
except: pass

st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/century-gothic');
    html, body, [class*="css"], .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, p, a, span, div { font-family: 'Century Gothic', sans-serif !important; }
    .stApp { background-color: #f4f7f6; }
    .main-header { background-color: #1a531f; padding: 20px; border-radius: 12px; color: white; text-align: center; margin-bottom: 2rem; }
    .stTabs [data-baseweb="tab"] { background-color: #e2e8f0; border-radius: 30px !important; padding: 10px 25px !important; }
    .stTabs [aria-selected="true"] { background-color: #1a531f !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown(f'<div class="main-header"><h1>{APP_NAME}</h1></div>', unsafe_allow_html=True)

# LOGIN
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            u_in = st.text_input("Correo").lower().strip()
            p_in = st.text_input("Contraseña", type="password")
            if st.button("INGRESAR", use_container_width=True):
                users = processor.obtener_usuarios()
                if u_in in users and users[u_in]["pw"] == p_in:
                    st.session_state.auth = True
                    st.session_state.user_info = users[u_in]
                    st.rerun()
                else: st.error("Credenciales incorrectas")
    st.stop()

# SIDEBAR
st.sidebar.markdown(f"<h2 style='color:#1a531f; text-align:center;'>Green Móvil</h2>", unsafe_allow_html=True)
st.sidebar.write(f"👤 **{st.session_state.user_info['nombre']}**")

df = processor.cargar_datos_pantalla()
tabs = st.tabs(["📊 DASHBOARD", "🚀 PIR", "📋 CONTROL", "⚙️ ADMIN"])

# VALIDACIÓN DE FILTRO SEMANAL
if df is not None and not df.empty and 'fecha' in df.columns:
    st.sidebar.divider()
    lista_fechas = sorted(df['fecha'].unique().tolist())
    fecha_sel = st.sidebar.selectbox("📅 Seleccione Día:", lista_fechas)
    pir_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    
    df_f = df[df['fecha'] == fecha_sel].copy()
    if pir_sel != "Todas": df_f = df_f[df_f['punto_pir'] == pir_sel]

    with tabs[0]: 
        st.subheader(f"Métricas del {fecha_sel}")
        st.metric("Servicios Programados", len(df_f))
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='cant'), x='ruta', y='cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: 
        st.subheader(f"Gestión PIR - {fecha_sel}")
        st.dataframe(df_f[['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog']], use_container_width=True, hide_index=True)

    with tabs[2]: 
        st.dataframe(df_f, use_container_width=True, hide_index=True)
else:
    for i in range(3):
        with tabs[i]: st.warning("⚠️ Base de datos vacía. Sincroniza la semana en ADMIN.")

# ADMIN
with tabs[3]:
    st.header("Configuración de Sistema")
    with st.expander("🚀 Descarga Masiva (Día por Día)", expanded=True):
        c1, c2 = st.columns(2)
        f_i = c1.date_input("Fecha Inicio", datetime.now())
        f_f = c2.date_input("Fecha Fin", datetime.now() + timedelta(days=7))
        if st.button("DESCARGAR SEMANA COMPLETA", use_container_width=True):
            if processor.sincronizar_semana_por_dias(str(f_i), str(f_f)):
                st.success("¡Semana descargada!"); st.rerun()
            else: st.error("Error en conexión Rigel.")

    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False; st.rerun()
