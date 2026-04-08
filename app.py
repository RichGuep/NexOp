import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import processor

APP_NAME = "NexOp | Green Móvil"
st.set_page_config(page_title=APP_NAME, layout="wide", page_icon="⚡")

# Intentar inicializar la conexión con Google Sheets
try:
    processor.inicializar_gsheet()
except:
    pass

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/century-gothic');
    html, body, [class*="css"], .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, p, a, span, div { 
        font-family: 'Century Gothic', sans-serif !important; 
    }
    .stApp { background-color: #f4f7f6; }
    .main-header { background-color: #1a531f; padding: 20px; border-radius: 12px; color: white; text-align: center; margin-bottom: 2rem; }
    .stTabs [data-baseweb="tab"] { background-color: #e2e8f0; border-radius: 30px !important; padding: 10px 25px !important; }
    .stTabs [aria-selected="true"] { background-color: #1a531f !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

st.markdown(f'<div class="main-header"><h1>{APP_NAME}</h1></div>', unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            st.subheader("🔑 Inicio de Sesión")
            u_in = st.text_input("Correo").lower().strip()
            p_in = st.text_input("Contraseña", type="password")
            if st.button("INGRESAR", use_container_width=True):
                users = processor.obtener_usuarios()
                if u_in in users and users[u_in]["pw"] == p_in:
                    st.session_state.auth = True
                    st.session_state.user_info = users[u_in]
                    st.rerun()
                else: 
                    st.error("Credenciales incorrectas")
    st.stop()

# --- DIALOG GESTIÓN (PIR) ---
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
        fail = c_f.selectbox("Incumplimiento:", ["NO", "Falta Bus", "Falta Ope", "Varado", "Congestión"])
        
        if st.form_submit_button("✅ GUARDAR EN NUBE", use_container_width=True):
            estado = "ELIMINADO" if fail != "NO" else ("RETOMA" if tip == "RETOMA" else "DESPACHO")
            success = processor.registrar_ejecucion_gsheet({
                "servbus": s_data['servbus'], 
                "bus_real": bn, 
                "ope_real": on, 
                "soc": f"{soc}%", 
                "estado": estado
            }, st.session_state.user_info["nombre"])
            if success:
                st.success("¡Guardado correctamente!")
                st.rerun()

# --- BARRA LATERAL ---
st.sidebar.markdown(f"<h2 style='color:#1a531f; text-align:center;'>Green Móvil</h2>", unsafe_allow_html=True)
st.sidebar.write(f"👤 **{st.session_state.user_info['nombre']}**")
if st.sidebar.button("Cerrar Sesión", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

# --- CARGA DE DATOS Y PESTAÑAS ---
df = processor.cargar_datos_pantalla()
tabs_nombres = ["📊 DASHBOARD", "🚀 PIR", "📋 CONTROL", "👤 ADMIN"]
tabs = st.tabs(tabs_nombres)

# VALIDACIÓN DE COLUMNA 'FECHA' PARA EVITAR EL KEYERROR
if df is not None and not df.empty and 'fecha' in df.columns:
    st.sidebar.divider()
    # Selector de Fecha Semanal
    lista_fechas = sorted(df['fecha'].unique().tolist())
    fecha_sel = st.sidebar.selectbox("📅 Día de Operación:", lista_fechas)
    
    # Filtro Punto PIR
    pir_sel = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    
    # Aplicar Filtros en Cascada
    df_f = df[df['fecha'] == fecha_sel].copy()
    if pir_sel != "Todas":
        df_f = df_f[df_f['punto_pir'] == pir_sel]

    # --- CONTENIDO DE LAS PESTAÑAS ---
    with tabs[0]: # DASHBOARD
        st.markdown(f"### Operación del día: {fecha_sel}")
        m1, m2 = st.columns(2)
        m1.metric("Servicios Programados", len(df_f))
        m2.metric("Rutas Activas", len(df_f['ruta'].unique()))
        st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='cant'), x='ruta', y='cant', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: # PIR
        st.markdown(f"### Gestión PIR - {fecha_sel}")
        cols_visibles = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog']
        sel = st.dataframe(df_f[cols_visibles], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows:
            ventana_gestion(df_f.iloc[sel.selection.rows[0]])

    with tabs[2]: # CONTROL
        st.markdown(f"### Reporte Completo - {fecha_sel}")
        st.dataframe(df_f, use_container_width=True, hide_index=True)

else:
    # MENSAJE DE SEGURIDAD SI EL EXCEL NO TIENE EL FORMATO NUEVO
    for i in range(3):
        with tabs[i]:
            st.warning("⚠️ La base de datos está vacía o no tiene el formato de fecha actualizado.")
            st.info("Por favor, ve a la pestaña **👤 ADMIN** para realizar una descarga semanal desde Rigel.")

# --- PESTAÑA ADMIN (SIEMPRE DISPONIBLE) ---
with tabs[3]:
    st.header("⚙️ Panel Administrativo")
    
    with st.expander("📅 Carga Semanal desde Rigel", expanded=True):
        st.write("Conecta la VPN y Ngrok antes de iniciar.")
        c1, c2 = st.columns(2)
        f_i = c1.date_input("Fecha Inicio", datetime.now())
        f_f = c2.date_input("Fecha Fin", datetime.now() + timedelta(days=7))
        
        if st.button("🚀 INICIAR DESCARGA A GOOGLE SHEETS", use_container_width=True):
            with st.spinner("Descargando datos... esto puede tardar un minuto."):
                if processor.sincronizar_rango_rigel(str(f_i), str(f_f)):
                    st.success("¡Semana cargada con éxito! La App se actualizará ahora.")
                    st.rerun()
                else:
                    st.error("Error de conexión. Verifica que el Túnel Ngrok y la VPN estén activos.")

    st.divider()
    with st.form("crear_usuario"):
        st.subheader("Registrar Nuevo Personal")
        ca1, ca2 = st.columns(2)
        correo = ca1.text_input("Correo")
        nombre = ca2.text_input("Nombre")
        cargo = ca1.selectbox("Cargo", ["Administrador", "Profesional", "Tecnico", "Auxiliar"])
        pw = ca2.text_input("Contraseña", type="password")
        if st.form_submit_button("CREAR USUARIO", use_container_width=True):
            processor.guardar_usuario(correo, nombre, cargo, pw)
            st.success(f"Usuario {nombre} creado.")
