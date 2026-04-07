import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time, timedelta
import processor

APP_NAME = "NexOp | Green Móvil"
st.set_page_config(page_title=APP_NAME, layout="wide", page_icon="⚡")

# Intentar inicializar la conexión con Google Sheets
try:
    processor.inicializar_gsheet()
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    @import url('https://fonts.cdnfonts.com/css/century-gothic');
    html, body, [class*="css"], .stMarkdown, .stText, h1, h2, h3, h4, h5, h6, p, a, span, div { 
        font-family: 'Century Gothic', sans-serif !important; 
    }
    .stApp { background-color: #f4f7f6; }
    .main-header { background-color: #1a531f; padding: 20px; border-radius: 12px; color: white; text-align: center; margin-bottom: 2rem; }
    [data-testid="stMetric"] { background-color: white; border-radius: 12px; border-top: 4px solid #15803d; }
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
    st.markdown(f"### Servicio: {s_data['timeOrigin']} | {s_data['ruta']} | Tabla: {s_data['tabla']}")
    with st.form("f_gestion"):
        c1, c2 = st.columns(2)
        c1.info(f"**Programado Rigel**\n\nBus: {s_data['bus_prog']}\n\nOpe: {s_data['ope_prog']}")
        with c2:
            bn = st.text_input("Bus Real:", value=s_data['bus_prog'])
            on = st.text_input("Ope Real:", value=s_data['ope_prog'])
        
        st.divider()
        c_soc, c_tipo, c_f = st.columns(3)
        with c_soc: soc = st.number_input("SOC%", 0, 100, 100)
        with c_tipo: tip = st.radio("Acción:", ["Normal", "RETOMA"], horizontal=True)
        with c_f: fail = st.selectbox("Incumplimiento:", ["NO", "Falta Bus", "Falta Ope", "Varado", "Congestión"])
        
        if st.form_submit_button("✅ GUARDAR CAMBIOS EN LA NUBE", use_container_width=True):
            u_nom = st.session_state.user_info["nombre"]
            estado = "ELIMINADO" if fail != "NO" else ("RETOMA" if tip == "RETOMA" else "DESPACHO")
            
            datos_nuevos = {
                "servbus": s_data['servbus'],
                "bus_real": bn,
                "ope_real": on,
                "soc": f"{soc}%",
                "estado": estado
            }
            if processor.registrar_ejecucion_gsheet(datos_nuevos, u_nom):
                st.success("¡Datos guardados!")
                st.rerun()
            else:
                st.error("Error al guardar en Google Sheets")

# --- BARRA LATERAL ---
st.sidebar.markdown(f"<h2 style='color:#1a531f; text-align:center;'>Green Móvil</h2>", unsafe_allow_html=True)
st.sidebar.write(f"👤 **Usuario:** {st.session_state.user_info['nombre']}")
if st.sidebar.button("Cerrar Sesión", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

# --- CARGA DE DATOS ---
df = processor.cargar_datos_pantalla()

# --- PESTAÑAS (TODAS VISIBLES PARA CONFIGURAR) ---
tabs_nombres = ["📊 DASHBOARD", "🚀 PIR", "📋 CONTROL", "👤 ADMIN"]
tabs = st.tabs(tabs_nombres)

if df is not None and not df.empty:
    # Filtros SideBar
    st.sidebar.divider()
    pir_s = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    rutas_op = ["Todas"] + (sorted(df['ruta'].unique().tolist()) if pir_s == "Todas" else processor.MAPEO_PIR[pir_s])
    ruta_s = st.sidebar.selectbox("🎯 Ruta:", rutas_op)
    tabla_s = st.sidebar.text_input("📋 Nro Tabla:")
    
    # Lógica de filtrado
    df_f = df.copy()
    if pir_s != "Todas": df_f = df_f[df_f['punto_pir'] == pir_s]
    if ruta_s != "Todas": df_f = df_f[df_f['ruta'] == ruta_s]
    if tabla_s: df_f = df_f[df_f['tabla'].astype(str).str.contains(tabla_s)]

    # --- CONTENIDO DE PESTAÑAS ---
    with tabs[0]: # DASHBOARD
        st.markdown("<h3 style='color:#1a531f;'>Métricas Generales</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.metric("SERVICIOS EN PRG", len(df_f))
        c2.metric("RUTAS ACTIVAS", len(df_f['ruta'].unique()))
        st.plotly_chart(px.bar(df_f.groupby('punto_pir').size().reset_index(name='cuenta'), x='punto_pir', y='cuenta', color_discrete_sequence=['#1a531f']), use_container_width=True)

    with tabs[1]: # PIR
        st.markdown("<h3 style='color:#1a531f;'>Gestión Operativa</h3>", unsafe_allow_html=True)
        cols_mostrar = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog']
        t_p = st.dataframe(df_f[cols_mostrar], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if t_p.selection.rows:
            ventana_gestion(df_f.iloc[t_p.selection.rows[0]])

    with tabs[2]: # CONTROL
        st.markdown("<h3 style='color:#1a531f;'>Reporte Maestro</h3>", unsafe_allow_html=True)
        st.dataframe(df_f, use_container_width=True, hide_index=True)

else:
    # Mensaje si el Excel está vacío
    for i in range(3):
        with tabs[i]: st.info("👋 ¡Bienvenido! No hay datos en el sistema. Por favor ve a la pestaña **ADMIN** y sincroniza con Rigel para empezar.")

# --- PESTAÑA ADMIN (SIEMPRE AL FINAL) ---
with tabs[3]:
    st.header("⚙️ Panel de Control Administrador")
    
    # SECCIÓN DE SINCRONIZACIÓN
    with st.expander("📅 Sincronización Masiva desde Rigel", expanded=True):
        st.info("Trae la programación semanal desde Rigel hacia Google Sheets.")
        col1, col2 = st.columns(2)
        f_ini = col1.date_input("Fecha Inicio", datetime.now())
        f_fin = col2.date_input("Fecha Fin", datetime.now() + timedelta(days=7))
        
        if st.button("🚀 INICIAR DESCARGA A NUBE", use_container_width=True):
            with st.spinner("Conectando con Rigel..."):
                exito = processor.sincronizar_rango_rigel(str(f_ini), str(f_fin))
                if exito:
                    st.success("¡Programación cargada con éxito en Google Sheets!")
                    st.rerun()
                else:
                    st.error("Error al sincronizar. Revisa VPN y Túnel Ngrok.")

    st.divider()
    # SECCIÓN DE USUARIOS
    with st.form("nuevo_usuario"):
        st.subheader("Registro de Usuarios")
        c1, c2 = st.columns(2)
        corr = c1.text_input("Correo electrónico")
        nom = c2.text_input("Nombre completo")
        puesto = c1.selectbox("Cargo", ["Administrador", "Profesional", "Tecnico", "Auxiliar"])
        clave = c2.text_input("Contraseña provisional", type="password")
        if st.form_submit_button("CREAR USUARIO"):
            processor.guardar_usuario(corr, nom, puesto, clave)
            st.success("Usuario registrado exitosamente.")
