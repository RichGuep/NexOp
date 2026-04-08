import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import processor

APP_NAME = "NexOp | Green Móvil"
st.set_page_config(page_title=APP_NAME, layout="wide", page_icon="⚡")

try: processor.inicializar_gsheet()
except: pass

# --- ESTILO VISUAL ---
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

# --- LOGIN ---
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

# --- DIALOG GESTIÓN ---
@st.dialog("🛠️ Gestión de Servicio")
def ventana_gestion(s_data):
    st.markdown(f"### Servicio: {s_data['timeOrigin']} | Tabla: {s_data['tabla']}")
    with st.form("f_gestion"):
        c1, c2 = st.columns(2)
        c1.info(f"**Programado**\n\nBus: {s_data['bus_prog']}\n\nOpe: {s_data['ope_prog']}")
        bn = c2.text_input("Bus Real:", value=s_data['bus_prog'])
        on = c2.text_input("Ope Real:", value=s_data['ope_prog'])
        st.divider()
        c_soc, c_tipo, c_f = st.columns(3)
        soc = c_soc.number_input("SOC%", 0, 100, 100)
        tip = c_tipo.radio("Acción:", ["Normal", "RETOMA"])
        fail = c_f.selectbox("Incumplimiento:", ["NO", "Falta Bus", "Falta Ope", "Varado"])
        
        if st.form_submit_button("✅ GUARDAR EN NUBE", use_container_width=True):
            estado = "ELIMINADO" if fail != "NO" else ("RETOMA" if tip == "RETOMA" else "DESPACHO")
            success = processor.registrar_ejecucion_gsheet({
                "servbus": s_data['servbus'], "bus_real": bn, "ope_real": on, "soc": f"{soc}%", "estado": estado
            }, st.session_state.user_info["nombre"])
            if success: st.success("Guardado!"); st.rerun()

# --- SIDEBAR & CARGA ---
st.sidebar.markdown(f"<h2 style='color:#1a531f; text-align:center;'>Green Móvil</h2>", unsafe_allow_html=True)
st.sidebar.write(f"👤 **{st.session_state.user_info['nombre']}**")

df = processor.cargar_datos_pantalla()
tabs = st.tabs(["📊 DASHBOARD", "🚀 PIR", "📋 CONTROL", "👤 ADMIN"])

# LÓGICA DE FILTRADO SEMANAL
if df is not None and not df.empty and 'fecha' in df.columns:
    st.sidebar.divider()
    # Selector de día basado en la carga semanal
    lista_fechas = sorted(df['fecha'].unique().tolist())
    fecha_sel = st.sidebar.selectbox("📅 Seleccione Fecha de Operación:", lista_fechas)
    
    pir_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    
    # Filtro maestro
    df_f = df[df['fecha'] == fecha_sel].copy()
    if pir_sel != "Todas": df_f = df_f[df_f['punto_pir'] == pir_sel]

    with tabs[0]: # DASHBOARD
        st.subheader(f"Resumen del {fecha_sel}")
        st.metric("Total Servicios del Día", len(df_f))
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='cant'), x='ruta', y='cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: # PIR
        st.subheader(f"Gestión de Salidas - {fecha_sel}")
        cols = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog']
        sel = st.dataframe(df_f[cols], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows: ventana_gestion(df_f.iloc[sel.selection.rows[0]])

    with tabs[2]: # CONTROL
        st.subheader(f"Vista General - {fecha_sel}")
        st.dataframe(df_f, use_container_width=True, hide_index=True)

else:
    for i in range(3):
        with tabs[i]: 
            st.warning("⚠️ Base de datos vacía o desactualizada.")
            st.info("Ve a la pestaña **ADMIN** y descarga la programación semanal.")

# --- ADMIN ---
with tabs[3]:
    st.header("⚙️ Configuración")
    with st.expander("📅 Carga Semanal Masiva (Rigel)", expanded=True):
        c1, c2 = st.columns(2)
        f_i = c1.date_input("Desde", datetime.now())
        f_f = c2.date_input("Hasta", datetime.now() + timedelta(days=7))
        if st.button("🚀 DESCARGAR SEMANA COMPLETA", use_container_width=True):
            with st.spinner("Sincronizando con Rigel..."):
                if processor.sincronizar_rango_rigel(str(f_i), str(f_f)):
                    st.success("¡Datos guardados en la nube!"); st.rerun()
                else: st.error("Fallo de conexión. Verifique Ngrok/VPN.")

    if st.sidebar.button("Cerrar Sesión", use_container_width=True):
        st.session_state.auth = False; st.rerun()
