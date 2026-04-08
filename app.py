import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import processor

st.set_page_config(page_title="NexOp | Green Móvil", layout="wide", page_icon="⚡")

# --- ESTILO CORPORATIVO ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/century-gothic');
    * { font-family: 'Century Gothic', sans-serif !important; }
    .stApp { background-color: #fcfdfc; }
    .main-header {
        background: linear-gradient(90deg, #1a531f 0%, #2e7d32 100%);
        padding: 20px; border-radius: 12px; color: white; text-align: center; margin-bottom: 25px;
    }
    .stMetric {
        background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 5px solid #1a531f;
    }
    .stTabs [aria-selected="true"] { background-color: #1a531f !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if "auth" not in st.session_state: st.session_state.auth = False

# --- LOGIN ---
if not st.session_state.auth:
    st.markdown('<div style="margin-top:100px;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1.2,1])
    with c2:
        st.markdown('<div class="main-header"><h1>NexOp Access</h1></div>', unsafe_allow_html=True)
        with st.container(border=True):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.button("INGRESAR", use_container_width=True):
                users = processor.obtener_usuarios()
                if u.lower() in users and str(users[u.lower()]["pw"]) == p:
                    st.session_state.auth = True
                    st.session_state.user_info = users[u.lower()]
                    st.rerun()
                else: st.error("Credenciales Inválidas")
    st.stop()

# --- APP ---
st.markdown('<div class="main-header"><h1>NexOp | Green Móvil</h1></div>', unsafe_allow_html=True)
st.sidebar.markdown(f"👤 **{st.session_state.user_info['nombre']}**")
st.sidebar.caption(f"Cargo: {st.session_state.user_info['cargo']}")

df = processor.cargar_datos_pantalla()
tabs = st.tabs(["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO", "⚙️ CONFIG"])

if df is not None and not df.empty and 'fecha' in df.columns:
    st.sidebar.divider()
    f_list = sorted(df['fecha'].unique().tolist())
    f_sel = st.sidebar.selectbox("📅 Día Operativo:", f_list)
    p_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    
    df_f = df[df['fecha'] == f_sel].copy()
    if p_sel != "Todas": df_f = df_f[df_f['punto_pir'] == p_sel]

    with tabs[0]: # DASHBOARD
        m1, m2, m3 = st.columns(3)
        m1.metric("Servicios", len(df_f))
        m2.metric("Rutas", len(df_f['ruta'].unique()))
        m3.metric("Tablas", len(df_f['tabla'].unique()))
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='Cant'), x='ruta', y='Cant', color_discrete_sequence=['#1a531f'], title="Carga por Ruta"), use_container_width=True)

    with tabs[1]: # PIR
        st.dataframe(df_f[['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog']], use_container_width=True, hide_index=True)

    with tabs[2]: # CONTROL
        st.dataframe(df_f, use_container_width=True, hide_index=True)
else:
    for i in range(3):
        with tabs[i]: st.info("Sincronice datos en la pestaña CONFIG.")

with tabs[3]: # CONFIG
    st.subheader("Administración de Sistema")
    
    if st.session_state.user_info.get('rol') == 'admin':
        with st.expander("👥 Registro de Personal y Perfiles", expanded=True):
            with st.form("reg_user", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n_nom = c1.text_input("Nombre")
                n_cor = c2.text_input("Correo")
                n_car = st.selectbox("Asignar Cargo:", [
                    "Auxiliar de Ejecución de la operación",
                    "Tecnico de ejecución de la operación",
                    "Profesional de Ejecución de la Operacion",
                    "Supervisor Logistico",
                    "Coordinador de Ejecución de la operación"
                ])
                n_pas = st.text_input("Clave")
                if st.form_submit_button("REGISTRAR"):
                    if processor.guardar_usuario(n_cor, n_nom, n_car, n_pas):
                        st.success("Usuario Guardado en Drive"); st.rerun()

    with st.expander("🚀 Sincronizar con Rigel"):
        c1, c2 = st.columns(2)
        fi, ff = c1.date_input("Inicio"), c2.date_input("Fin")
        if st.button("DESCARGAR SEMANA"):
            if processor.sincronizar_semana_por_dias(str(fi), str(ff)):
                st.success("¡Hecho!"); st.rerun()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False; st.rerun()
