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
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border-left: 5px solid #1a531f; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .stTabs [aria-selected="true"] { background-color: #1a531f !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

if "auth" not in st.session_state: st.session_state.auth = False

# --- LOGIN ---
if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,1.2,1])
    with c2:
        st.markdown('<div class="main-header"><h1>NexOp Access</h1></div>', unsafe_allow_html=True)
        u = st.text_input("Usuario (Correo)").lower().strip()
        p = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            users = processor.obtener_usuarios()
            if u in users and str(users[u]["pw"]) == p:
                st.session_state.auth = True; st.session_state.user_info = users[u]; st.rerun()
            else: st.error("Acceso Denegado")
    st.stop()

# --- POPUP GESTIÓN ---
@st.dialog("🛠️ Gestión Operativa")
def ventana_gestion(viaje):
    st.markdown(f"**Servicio:** `{viaje['servbus']}`")
    with st.form("form_ajuste"):
        bus_r = st.text_input("Bus Real", value=viaje['bus_prog'])
        ope_r = st.text_input("Operador Real", value=viaje['ope_prog'])
        motivo = st.selectbox("Incumplimiento / Novedad:", ["Operación Normal", "Falta de movil", "Falta de operador", "Bus varado", "Accidente", "Falla SIRCI/ITS", "operador Enfermo", "vandalismo"])
        elim_km = st.checkbox("¿Eliminar Kilometraje?")
        obs = st.text_area("Notas")
        if st.form_submit_button("✅ GUARDAR CAMBIOS", use_container_width=True):
            if processor.registrar_gestion_viaje({"servbus": viaje['servbus'], "bus_final": bus_r, "ope_final": ope_r, "motivo": motivo, "eliminar_km": "SÍ" if elim_km else "NO", "obs": obs}, st.session_state.user_info['nombre']):
                st.success("¡Registrado!"); st.rerun()

# --- APP LAYOUT ---
st.markdown('<div class="main-header"><h1>NexOp | Green Móvil</h1></div>', unsafe_allow_html=True)
st.sidebar.markdown(f"👤 **{st.session_state.user_info['nombre']}**")

df = processor.cargar_datos_pantalla()

# Validación de ROL
user_info = st.session_state.user_info
is_admin = (user_info.get('correo') == "richard.guevara@greenmovil.com.co" or user_info.get('rol') == 'admin')

tabs = st.tabs(["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO", "⚙️ CONFIG"] if is_admin else ["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO"])

if df is not None and not df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("🔍 Filtros de Operación")
    
    # 1. Filtro Fecha
    f_sel = st.sidebar.selectbox("📅 Día Operativo:", sorted(df['fecha'].unique().tolist()))
    df_f = df[df['fecha'] == f_sel].copy()

    # 2. Lógica de Turnos usando 'timeOrigin'
    # Convertimos timeOrigin a formato hora para filtrar en memoria
    df_f['temp_hora'] = pd.to_datetime(df_f['timeOrigin']).dt.hour
    
    turno = st.sidebar.radio("⏱️ Turno de Trabajo:", ["Completo", "Mañana (06:00 - 14:00)", "Tarde (14:00 - 22:00)"])
    if "Mañana" in turno:
        df_f = df_f[(df_f['temp_hora'] >= 6) & (df_f['temp_hora'] < 14)]
    elif "Tarde" in turno:
        df_f = df_f[(df_f['temp_hora'] >= 14) & (df_f['temp_hora'] < 22)]

    # 3. Filtros PIR y Buscadores
    p_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todos"] + list(processor.MAPEO_PIR.keys()))
    if p_sel != "Todos": df_f = df_f[df_f['punto_pir'] == p_sel]
    
    r_sel = st.sidebar.selectbox("🛣️ Ruta Específica:", ["Todas"] + sorted(df_f['ruta'].unique().tolist()))
    if r_sel != "Todas": df_f = df_f[df_f['ruta'] == r_sel]
    
    search = st.sidebar.text_input("🔎 Buscar Bus o Conductor:").upper().strip()
    if search:
        df_f = df_f[df_f['bus_prog'].str.contains(search) | df_f['ope_prog'].str.contains(search)]

    # --- PESTAÑAS ---
    with tabs[0]: # DASHBOARD
        c1, c2, c3 = st.columns(3)
        c1.metric("Servicios", len(df_f))
        c2.metric("Buses", len(df_f['bus_prog'].unique()))
        c3.metric("Rutas", len(df_f['ruta'].unique()))
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='Cant'), x='ruta', y='Cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: # GESTIÓN
        st.info(f"Mostrando: {turno} | Fila seleccionable para cambios")
        sel = st.dataframe(df_f[['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'servbus']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows: ventana_gestion(df_f.iloc[sel.selection.rows[0]])

    with tabs[2]: # SEGUIMIENTO
        st.dataframe(df_f.drop(columns=['temp_hora']), use_container_width=True, hide_index=True)

# --- PESTAÑA CONFIG ---
if is_admin:
    with tabs[-1]:
        st.subheader("⚙️ Configuración")
        with st.expander("🚀 Descarga Rigel"):
            c1, c2 = st.columns(2)
            if st.button("SINCRONIZAR SEMANA"):
                if processor.sincronizar_semana_por_dias(str(c1.date_input("Inicio")), str(c2.date_input("Fin"))):
                    st.success("¡Sincronizado!"); st.rerun()
        st.divider()
        with st.form("u_reg"):
            st.write("**Registrar Personal**")
            n, c, k, p = st.columns(4)
            nom, cor = n.text_input("Nombre"), c.text_input("Correo")
            car, pas = k.selectbox("Cargo", ["Auxiliar", "Técnico", "Coordinador"]), p.text_input("Clave")
            if st.form_submit_button("REGISTRAR"):
                if processor.guardar_usuario(cor, nom, car, pas): st.success("Guardado"); st.rerun()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False; st.rerun()
