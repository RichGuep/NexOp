import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import processor

ADMIN_EMAIL = "richard.guevara@greenmovil.com.co"
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
    c2 = st.columns([1,1.2,1])[1]
    with c2:
        st.markdown('<div class="main-header"><h1>NexOp Access</h1></div>', unsafe_allow_html=True)
        u = st.text_input("Correo").lower().strip()
        p = st.text_input("Contraseña", type="password").strip()
        if st.button("INGRESAR", use_container_width=True):
            users = processor.obtener_usuarios()
            if u in users and str(users[u].get('pw')) == p:
                st.session_state.auth = True; st.session_state.user_info = users[u]; st.rerun()
            else: st.error("Acceso Denegado")
    st.stop()

# --- POPUP GESTIÓN ---
@st.dialog("🛠️ Gestión Operativa (PIR)", width="large")
def ventana_gestion(viaje):
    empresa = viaje.get('empresa', 'ZMO V')
    prefijo = "Z63-" if empresa == "ZMO III" else "Z67-"
    df_b = processor.obtener_listado_buses_drive()
    
    # Filtrar buses por empresa
    df_filtrado = df_b[df_b['Código'].astype(str).str.startswith(prefijo)] if not df_b.empty else pd.DataFrame()
    lista_b = ["N/A"] + df_filtrado['label'].tolist()
    
    # Pre-seleccionar el bus actual
    try: idx_def = next(i for i, x in enumerate(lista_b) if str(viaje['bus_prog']) in x)
    except: idx_def = 0

    st.markdown(f"### Servicio: `{viaje['servbus']}` | Empresa: **{empresa}**")
    with st.form("form_gestion"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🚌 Vehículo")
            st.caption(f"Prog: {viaje['bus_prog']}")
            bus_r = st.selectbox("Bus Real:", options=lista_b, index=idx_def)
            mot_m = st.selectbox("Motivo:", ["Operación Normal", "RETOMA", "Falta movil", "Bus varado", "Accidente"])
        with col2:
            st.markdown("#### 👤 Operador")
            st.caption(f"Prog: {viaje['ope_prog']}")
            ope_r = st.text_input("Operador Real:", value=viaje['ope_prog'])
            mot_o = st.selectbox("Motivo:", ["Operación Normal", "Falta operador", "Enfermo", "No llegó"])
            elim_k = st.toggle("¿Eliminar Kilometraje?")
        
        obs = st.text_area("📝 Observación")
        if st.form_submit_button("✅ GUARDAR CAMBIOS", use_container_width=True):
            datos = {
                "servbus": viaje['servbus'], "bus_prog": viaje['bus_prog'], 
                "bus_real": bus_r.split(" | ")[0] if " | " in bus_r else bus_r,
                "motivo_movil": mot_m, "ope_prog": viaje['ope_prog'],
                "ope_real": ope_r, "motivo_ope": mot_o,
                "eliminar_km": "SI" if elim_k else "NO", "obs_final": obs
            }
            if processor.aplicar_gestion_servicio(datos, st.session_state.user_info['nombre']):
                st.success("¡Hecho!"); st.rerun()

# --- APP LAYOUT ---
st.markdown('<div class="main-header"><h1>NexOp | Green Móvil</h1></div>', unsafe_allow_html=True)
df = processor.cargar_datos_pantalla()
u_info = st.session_state.user_info
is_admin = (u_info.get('correo') == ADMIN_EMAIL or str(u_info.get('rol')).lower() == 'admin')

tabs = st.tabs(["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO", "⚙️ CONFIG"] if is_admin else ["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO"])

st.sidebar.markdown(f"👤 **{u_info.get('nombre', 'Usuario')}**")

if not df.empty:
    st.sidebar.subheader("🔍 Filtros")
    f_sel = st.sidebar.selectbox("📅 Día Operativo:", sorted(df['fecha'].unique().tolist()))
    df_f = df[df['fecha'] == f_sel].copy()
    
    # Filtro Turno
    df_f['temp_hora'] = pd.to_datetime(df_f['timeOrigin']).dt.hour
    turno = st.sidebar.radio("⏱️ Turno:", ["Completo", "Mañana (06:00-14:00)", "Tarde (14:00-22:00)"])
    if "Mañana" in turno: df_f = df_f[(df_f['temp_hora'] >= 6) & (df_f['temp_hora'] < 14)]
    elif "Tarde" in turno: df_f = df_f[(df_f['temp_hora'] >= 14) & (df_f['temp_hora'] < 22)]

    with tabs[0]: # ESTADÍSTICAS
        c1, c2, c3 = st.columns(3)
        c1.metric("Servicios", len(df_f))
        c2.metric("Buses Únicos", len(df_f['bus_prog'].unique()))
        c3.metric("Rutas Activas", len(df_f['ruta'].unique()))
        
        st.divider()
        with st.expander("🔍 CONSULTAR LISTADO DE BUSES POR RUTA Y TABLA"):
            df_flota = df_f.groupby(['ruta', 'tabla'])['bus_prog'].first().reset_index()
            st.dataframe(df_flota.rename(columns={'ruta': 'RUTA', 'tabla': 'TABLA', 'bus_prog': 'VEHÍCULO'}), use_container_width=True, hide_index=True)
        
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='Cant'), x='ruta', y='Cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: # GESTIÓN PIR
        cols_v = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'empresa', 'servbus']
        sel = st.dataframe(df_f[cols_v], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows:
            ventana_gestion(df_f.iloc[sel.selection.rows[0]])

    with tabs[2]: # SEGUIMIENTO
        st.dataframe(df_f.drop(columns=['temp_hora']), use_container_width=True, hide_index=True)

if is_admin:
    with tabs[-1]: # CONFIG
        st.subheader("⚙️ Configuración")
        with st.form("descarga_form"):
            c1, c2 = st.columns(2)
            f_ini = c1.date_input("Fecha Inicio")
            f_fin = c2.date_input("Fecha Fin")
            if st.form_submit_button("🚀 SINCRONIZAR RIGEL"):
                success, msg = processor.sincronizar_semana_por_dias(str(f_ini), str(f_fin))
                if success: st.success(msg); st.balloons(); st.rerun()
                else: st.error(msg)

if st.sidebar.button("Cerrar Sesión"): st.session_state.auth = False; st.rerun()
