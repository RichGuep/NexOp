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

# --- CARGA DE VEHÍCULOS ---
df_buses_raw = processor.obtener_listado_buses_drive()

@st.dialog("🛠️ Gestión Operativa (PIR)", width="large")
def ventana_gestion(viaje):
    empresa = viaje.get('empresa', 'ZMO V')
    prefijo = "Z63-" if empresa == "ZMO III" else "Z67-"
    
    if not df_buses_raw.empty:
        df_filtrado = df_buses_raw[df_buses_raw['Código'].astype(str).str.startswith(prefijo)]
        lista_opciones = ["N/A"] + df_filtrado['label'].tolist()
    else: lista_opciones = ["N/A"]

    st.markdown(f"### Servicio: `{viaje['servbus']}` | Empresa: **{empresa}**")
    with st.form("form_gestion"):
        c1, c2 = st.columns(2)
        with c1:
            bus_p = c1.selectbox("Bus Principal:", options=lista_opciones, index=next((i for i, x in enumerate(lista_opciones) if str(viaje['bus_prog']) in x), 0))
            bus_a = c1.selectbox("Bus Adicional:", options=lista_opciones)
            mot_b = c1.selectbox("Motivo Bus:", ["Normal", "Falta movil", "Varado", "Accidente", "Vandalismo"])
        with c2:
            ope_r = c2.text_input("Operador Real", value=viaje.get('ope_prog', ''))
            mot_o = c2.selectbox("Motivo Operador:", ["Normal", "Falta operador", "Enfermo", "No llegó"])
            elim_k = c2.toggle("Eliminar KM")
        obs_f = st.text_area("📝 Observación Final")
        if st.form_submit_button("🚀 GUARDAR"):
            datos = {"servbus": viaje['servbus'], "bus_final": bus_p.split(" | ")[0], "bus_adic": bus_a.split(" | ")[0] if bus_a != "N/A" else "", "motivo_bus": mot_b, "ope_final": ope_r, "motivo_ope": mot_o, "eliminar_km": "SI" if elim_k else "NO", "obs_final": obs_f}
            if processor.registrar_gestion_viaje(datos, st.session_state.user_info.get('nombre', 'Admin')): st.rerun()

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

    # Filtro PIR y Buscadores
    p_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todos"] + list(processor.MAPEO_PIR.keys()))
    if p_sel != "Todos": df_f = df_f[df_f['punto_pir'] == p_sel]
    r_sel = st.sidebar.selectbox("🛣️ Ruta:", ["Todas"] + sorted(df_f['ruta'].unique().tolist()))
    if r_sel != "Todas": df_f = df_f[df_f['ruta'] == r_sel]
    buscar = st.sidebar.text_input("🔎 Buscar Bus o Conductor:").upper()
    if buscar: df_f = df_f[df_f['bus_prog'].astype(str).str.contains(buscar) | df_f['ope_prog'].astype(str).str.contains(buscar)]

    with tabs[0]:
        st.metric("Servicios", len(df_f))
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='Cant'), x='ruta', y='Cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]:
        st.info(f"Consola PIR - {f_sel}")
        cols_v = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'empresa', 'servbus']
        sel = st.dataframe(df_f[cols_v], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows: ventana_gestion(df_f.iloc[sel.selection.rows[0]])
    
    with tabs[2]: st.dataframe(df_f.drop(columns=['temp_hora']), use_container_width=True, hide_index=True)

if is_admin:
    with tabs[-1]:
        st.subheader("⚙️ Configuración")
        if st.button("DESCARGAR PROGRAMACIÓN RIGEL"):
            if processor.sincronizar_semana_por_dias(str(st.date_input("Inicio")), str(st.date_input("Fin"))): st.rerun()

if st.sidebar.button("Cerrar Sesión"): st.session_state.auth = False; st.rerun()
