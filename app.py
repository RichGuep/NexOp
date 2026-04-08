import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import processor

st.set_page_config(page_title="NexOp | Green Móvil", layout="wide", page_icon="⚡")

# --- ESTILO ---
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

# --- LOGIN (Simplificado para el ejemplo, usa el que ya tienes) ---
if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,1.2,1])
    with c2:
        st.markdown('<div class="main-header"><h1>NexOp Access</h1></div>', unsafe_allow_html=True)
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            users = processor.obtener_usuarios()
            if u.lower().strip() in users and str(users[u.lower().strip()]["pw"]) == p:
                st.session_state.auth = True; st.session_state.user_info = users[u.lower().strip()]; st.rerun()
    st.stop()

# --- VENTANA EMERGENTE ---
@st.dialog("🛠️ Gestión de Contingencia")
def ventana_gestion(viaje):
    st.markdown(f"**Servicio:** `{viaje['servbus']}` | **Tabla:** {viaje['tabla']}")
    with st.form("form_ajuste"):
        c1, c2 = st.columns(2)
        bus_r = c1.text_input("Bus Real", value=viaje['bus_prog'])
        ope_r = c2.text_input("Operador Real", value=viaje['ope_prog'])
        motivo = st.selectbox("Incumplimiento / Novedad:", ["Operación Normal", "Falta de movil", "Falta de operador", "Bus varado", "Accidente", "Falla SIRCI/ITS", "operador Enfermo", "vandalismo"])
        elim_km = st.checkbox("¿Eliminar Kilometraje?")
        obs = st.text_area("Notas de la novedad")
        if st.form_submit_button("✅ GUARDAR CAMBIOS", use_container_width=True):
            if processor.registrar_gestion_viaje({"servbus": viaje['servbus'], "bus_final": bus_r, "ope_final": ope_r, "motivo": motivo, "eliminar_km": "SÍ" if elim_km else "NO", "obs": obs}, st.session_state.user_info['nombre']):
                st.success("¡Registrado!"); st.rerun()

# --- APP LAYOUT ---
st.markdown('<div class="main-header"><h1>NexOp | Green Móvil</h1></div>', unsafe_allow_html=True)
st.sidebar.markdown(f"👤 **{st.session_state.user_info['nombre']}**")

df = processor.cargar_datos_pantalla()
user_rol = "admin" if st.session_state.user_info.get('correo') == "richard.guevara@greenmovil.com.co" else st.session_state.user_info.get('rol', 'user')

tabs = st.tabs(["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO", "⚙️ CONFIG"] if user_rol == "admin" else ["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO"])

if df is not None and not df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("🔍 Filtros de Operación")
    
    # 1. Filtro de Fecha
    f_list = sorted(df['fecha'].unique().tolist())
    f_sel = st.sidebar.selectbox("📅 Día Operativo:", f_list)
    df_f = df[df['fecha'] == f_sel].copy()

    # 2. Filtro de Turno (Franjas Horarias)
    turno = st.sidebar.radio("⏱️ Turno de Trabajo:", ["Completo", "Mañana (06:00 - 14:00)", "Tarde (14:00 - 22:00)"])
    if "Mañana" in turno:
        df_f = df_f[(df_f['hora_inicio'] >= 6) & (df_f['hora_inicio'] < 14)]
    elif "Tarde" in turno:
        df_f = df_f[(df_f['hora_inicio'] >= 14) & (df_f['hora_inicio'] < 22)]

    # 3. Filtro PIR y Ruta Específica
    p_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todos"] + list(processor.MAPEO_PIR.keys()))
    if p_sel != "Todos":
        df_f = df_f[df_f['punto_pir'] == p_sel]
    
    rutas_disponibles = sorted(df_f['ruta'].unique().tolist())
    r_sel = st.sidebar.selectbox("🛣️ Ruta Específica:", ["Todas"] + rutas_disponibles)
    if r_sel != "Todas":
        df_f = df_f[df_f['ruta'] == r_sel]

    # 4. Buscador de Bus u Operador
    st.sidebar.divider()
    search_query = st.sidebar.text_input("🔎 Buscar Bus u Operador:", "").strip().upper()
    if search_query:
        df_f = df_f[df_f['bus_prog'].str.contains(search_query) | df_f['ope_prog'].str.contains(search_query)]

    # --- PESTAÑAS ---
    with tabs[0]: # ESTADISTICAS
        m1, m2, m3 = st.columns(3)
        m1.metric("Servicios en Turno", len(df_f))
        m2.metric("Buses Programados", len(df_f['bus_prog'].unique()))
        m3.metric("Rutas Activas", len(df_f['ruta'].unique()))
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='Cant'), x='ruta', y='Cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: # GESTIÓN PIR
        st.info(f"Mostrando operación: {turno} | Ruta: {r_sel}")
        cols_v = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'servbus']
        sel = st.dataframe(df_f[cols_v], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows: ventana_gestion(df_f.iloc[sel.selection.rows[0]])

    with tabs[2]: # SEGUIMIENTO
        st.dataframe(df_f, use_container_width=True, hide_index=True)

# ... (Pestaña CONFIG queda igual que la anterior) ...
