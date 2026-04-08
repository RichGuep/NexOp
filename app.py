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

# --- LOGIN ---
if not st.session_state.auth:
    st.markdown('<div style="margin-top:100px;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,1.2,1])
    with c2:
        st.markdown('<div class="main-header"><h1>NexOp Access</h1></div>', unsafe_allow_html=True)
        with st.container(border=True):
            u = st.text_input("Usuario (Correo)")
            p = st.text_input("Contraseña", type="password")
            if st.button("INGRESAR", use_container_width=True):
                users = processor.obtener_usuarios()
                user_key = u.lower().strip()
                if user_key in users and str(users[user_key]["pw"]) == p:
                    st.session_state.auth = True
                    st.session_state.user_info = users[user_key]
                    st.rerun()
                else: st.error("Acceso Denegado. Verifique correo y clave.")
    st.stop()

# --- POP-UP GESTIÓN ---
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
st.sidebar.caption(f"Cargo: {st.session_state.user_info['cargo']}")

# Filtros Globales
df = processor.cargar_datos_pantalla()
user_rol = st.session_state.user_info.get('rol', 'user')

# Definir pestañas según ROL
lista_tabs = ["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO"]
if user_rol == "admin": lista_tabs.append("⚙️ CONFIG")
tabs = st.tabs(lista_tabs)

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
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='Cant'), x='ruta', y='Cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: # PIR
        st.info("💡 Haz clic en una fila para gestionar cambios.")
        sel = st.dataframe(df_f[['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'servbus']], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows: ventana_gestion(df_f.iloc[sel.selection.rows[0]])

    with tabs[2]: # SEGUIMIENTO
        st.dataframe(df_f, use_container_width=True, hide_index=True)

else:
    for i in range(len(tabs)):
        if i < 3: # Solo las primeras 3 pestañas muestran el error de datos
            with tabs[i]: st.warning("⚠️ No hay programación cargada en el sistema.")

# PESTAÑA CONFIG (SOLO ADMINS)
if user_rol == "admin":
    with tabs[-1]:
        st.subheader("Administración de Sistema")
        with st.expander("🚀 Sincronizar Rigel (Semanal)"):
            c1, c2 = st.columns(2)
            fi, ff = c1.date_input("Inicio"), c2.date_input("Fin")
            if st.button("DESCARGAR SEMANA"):
                if processor.sincronizar_semana_por_dias(str(fi), str(ff)):
                    st.success("¡Hecho!"); st.rerun()
        
        st.divider()
        with st.expander("👥 Registro de Personal", expanded=True):
            with st.form("reg_u", clear_on_submit=True):
                n1, n2 = st.columns(2)
                nom, cor = n1.text_input("Nombre"), n2.text_input("Correo")
                car = st.selectbox("Cargo:", ["Auxiliar de Ejecución de la operación", "Tecnico de ejecución de la operación", "Profesional de Ejecución de la Operacion", "Supervisor Logistico", "Coordinador de Ejecución de la operación"])
                pas = st.text_input("Clave")
                if st.form_submit_button("REGISTRAR USUARIO"):
                    if processor.guardar_usuario(cor, nom, car, pas):
                        st.success("Usuario Guardado"); st.rerun()

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False; st.rerun()
