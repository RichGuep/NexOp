import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import processor

st.set_page_config(page_title="NexOp | Green Móvil", layout="wide", page_icon="⚡")

# --- CSS PERSONALIZADO (Century Gothic & Colores Green Móvil) ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/century-gothic');
    
    * { font-family: 'Century Gothic', sans-serif !important; }
    
    /* Fondo y contenedores */
    .stApp { background-color: #f8f9fa; }
    
    /* Header Principal */
    .main-header {
        background: linear-gradient(90deg, #1a531f 0%, #2e7d32 100%);
        padding: 25px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    /* Tarjetas de Métricas */
    [data-testid="stMetricValue"] { color: #1a531f !important; font-weight: bold; }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1a531f;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        border: 1px solid #e0e0e0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1a531f !important;
        color: white !important;
        border: 1px solid #1a531f !important;
    }
    
    /* Botones */
    .stButton>button {
        background-color: #1a531f;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 10px 25px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #2e7d32;
        border: none;
        color: white;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

if "auth" not in st.session_state: st.session_state.auth = False

# --- PANTALLA LOGIN ---
if not st.session_state.auth:
    st.markdown('<div style="margin-top:100px;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        st.markdown('<div class="main-header"><h1>NexOp | Ingreso</h1></div>', unsafe_allow_html=True)
        with st.container(border=True):
            u = st.text_input("Usuario (Correo)")
            p = st.text_input("Contraseña", type="password")
            if st.button("ACCEDER", use_container_width=True):
                users = processor.obtener_usuarios()
                if u.lower().strip() in users and str(users[u.lower().strip()]["pw"]) == p:
                    st.session_state.auth = True
                    st.session_state.user_info = users[u.lower().strip()]
                    st.rerun()
                else: st.error("Acceso denegado")
    st.stop()

# --- APP LAYOUT ---
st.markdown('<div class="main-header"><h1>NexOp | Green Móvil</h1></div>', unsafe_allow_html=True)

st.sidebar.markdown(f"### ⚡ Operaciones")
st.sidebar.write(f"Bienvenido, **{st.session_state.user_info['nombre']}**")

df = processor.cargar_datos_pantalla()
t1, t2, t3, t4 = st.tabs(["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO", "⚙️ CONFIG"])

if df is not None and not df.empty and 'fecha' in df.columns:
    # Filtros Sidebar con estilo
    st.sidebar.divider()
    f_list = sorted(df['fecha'].unique().tolist())
    f_sel = st.sidebar.selectbox("📅 Seleccione Día:", f_list)
    p_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    
    df_f = df[df['fecha'] == f_sel].copy()
    if p_sel != "Todas": df_f = df_f[df_f['punto_pir'] == p_sel]

    with t1: # DASHBOARD
        st.markdown(f"### Resumen de Operación - {f_sel}")
        m1, m2, m3 = st.columns(3)
        with m1: st.metric("Total Servicios", len(df_f))
        with m2: st.metric("Rutas en Turno", len(df_f['ruta'].unique()))
        with m3: st.metric("Tablas", len(df_f['tabla'].unique()))
        
        fig = px.bar(df_f.groupby('ruta').size().reset_index(name='Servicios'), 
                     x='ruta', y='Servicios', color_discrete_sequence=['#1a531f'],
                     template="plotly_white", title="Distribución por Ruta")
        st.plotly_chart(fig, use_container_width=True)

    with t2: # PIR
        st.markdown(f"### Despacho Vehicular")
        st.dataframe(df_f[['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog']], 
                     use_container_width=True, hide_index=True)

    with t3: # CONTROL
        st.markdown(f"### Base de Datos Completa")
        st.dataframe(df_f, use_container_width=True, hide_index=True)
else:
    for t in [t1, t2, t3]:
        with t: st.info("ℹ️ No hay datos. Realice una sincronización en la pestaña CONFIG.")

with t4: # ADMIN
    st.subheader("Panel Administrativo")
    with st.expander("Sincronización con Rigel", expanded=True):
        c1, c2 = st.columns(2)
        fi = c1.date_input("Inicio de semana")
        ff = c2.date_input("Fin de semana")
        if st.button("SINCRONIZAR AHORA"):
            if processor.sincronizar_semana_por_dias(str(fi), str(ff)):
                st.success("¡Operación cargada exitosamente!"); st.rerun()

    st.divider()
    st.subheader("Control de Usuarios")
    u_db = processor.obtener_usuarios()
    df_u = pd.DataFrame.from_dict(u_db, orient='index').reset_index()
    if not df_u.empty:
        cols_u = [c for c in ['index', 'nombre', 'cargo'] if c in df_u.columns]
        st.dataframe(df_u[cols_u], use_container_width=True, hide_index=True)
    
    with st.form("new_u"):
        st.write("**Nuevo Registro**")
        nc, nn, np = st.columns(3)
        mail = nc.text_input("Correo")
        nom = nn.text_input("Nombre")
        pas = np.text_input("Clave", type="password")
        if st.form_submit_button("REGISTRAR"):
            if processor.guardar_usuario(mail, nom, "Auxiliar", pas):
                st.success("Usuario Creado"); st.rerun()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False; st.rerun()
