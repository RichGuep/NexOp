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

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
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
                else: st.error("Acceso Denegado")
    st.stop()

# --- VENTANA EMERGENTE (POP-UP) ---
@st.dialog("🛠️ Gestión de Contingencia")
def ventana_gestion(viaje):
    st.markdown(f"**Servicio:** `{viaje['servbus']}` | **Tabla:** {viaje['tabla']}")
    with st.form("form_ajuste"):
        c1, c2 = st.columns(2)
        bus_r = c1.text_input("Bus Real", value=viaje['bus_prog'])
        ope_r = c2.text_input("Operador Real", value=viaje['ope_prog'])
        
        motivo = st.selectbox("Motivo de Incumplimiento / Cambio:", [
            "Operación Normal", "Falta de movil", "Falta de operador", 
            "Bus varado", "Accidente", "Falla SIRCI y/o ITS", 
            "operador Enfermo", "vandalismo"
        ])
        
        elim_km = st.checkbox("¿Eliminar Kilometraje?")
        obs = st.text_area("Observaciones del evento")
        
        if st.form_submit_button("✅ GUARDAR CAMBIOS", use_container_width=True):
            if processor.registrar_gestion_viaje({
                "servbus": viaje['servbus'], "bus_final": bus_r, "ope_final": ope_r,
                "motivo": motivo, "eliminar_km": "SÍ" if elim_km else "NO", "obs": obs
            }, st.session_state.user_info['nombre']):
                st.success("¡Registrado!"); st.rerun()

# --- APP ---
st.markdown('<div class="main-header"><h1>NexOp | Green Móvil</h1></div>', unsafe_allow_html=True)
st.sidebar.markdown(f"👤 **{st.session_state.user_info['nombre']}**")
st.sidebar.caption(f"Cargo: {st.session_state.user_info['cargo']}")

user_rol = st.session_state.user_info.get('rol', 'user')
lista_tabs = ["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO"]
if user_rol == "admin": lista_tabs.append("⚙️ CONFIG")
tabs = st.tabs(lista_tabs)

df = processor.cargar_datos_pantalla()

if df is not None and not df.empty and 'fecha' in df.columns:
    st.sidebar.divider()
    f_sel = st.sidebar.selectbox("📅 Día Operativo:", sorted(df['fecha'].unique().tolist()))
    p_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    df_f = df[df['fecha'] == f_sel].copy()
    if p_sel != "Todas": df_f = df_f[df_f['punto_pir'] == p_sel]

    with tabs[0]: # ESTADISTICAS
        m1, m2, m3 = st.columns(3)
        m1.metric("Servicios", len(df_f))
        m2.metric("Rutas", len(df_f['ruta'].unique()))
        m3.metric("Tablas", len(df_f['tabla'].unique()))
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='Cant'), x='ruta', y='Cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: # GESTIÓN PIR
        st.info("💡 Haz clic en una fila para gestionar el cambio de bus, operador o novedad.")
        cols_v = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'servbus']
        sel = st.dataframe(df_f[cols_v], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows:
            ventana_gestion(df_f.iloc[sel.selection.rows[0]])

    with tabs[2]: # SEGUIMIENTO
        st.dataframe(df_f, use_container_width=True, hide_index=True)

if user_rol == "admin":
    with tabs[3]: # CONFIG
        with st.expander("🚀 Sincronizar Rigel"):
            c1, c2 = st.columns(2)
            if st.button("DESCARGAR"):
                if processor.sincronizar_semana_por_dias(str(c1.date_input("Inicio")), str(c2.date_input("Fin"))):
                    st.success("Sincronizado"); st.rerun()
        st.divider()
        with st.form("reg_u"):
            st.subheader("Registrar Personal")
            n_nom, n_cor = st.text_input("Nombre"), st.text_input("Correo")
            n_car = st.selectbox("Cargo:", ["Auxiliar de Ejecución de la operación", "Tecnico de ejecución de la operación", "Profesional de Ejecución de la Operacion", "Supervisor Logistico", "Coordinador de Ejecución de la operación"])
            n_pas = st.text_input("Clave")
            if st.form_submit_button("REGISTRAR"):
                if processor.guardar_usuario(n_cor, n_nom, n_car, n_pas):
                    st.success("Usuario Creado"); st.rerun()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False; st.rerun()
