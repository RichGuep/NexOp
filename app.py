import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time, timedelta
import processor

APP_NAME = "NexOp | Green Móvil"
st.set_page_config(page_title=APP_NAME, layout="wide", page_icon="⚡")

# Intentar inicializar conexión con Google Sheets
try:
    processor.inicializar_gsheet()
except Exception as e:
    st.error(f"Error al conectar con Google Sheets: {e}")

# --- ESTILO CENTURY GOTHIC ---
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
    st.markdown(f"### Servicio: {s_data['timeOrigin']} | {s_data['ruta']} | Tabla: {s_data['tabla']}")
    with st.form("f_gestion"):
        c1, c2 = st.columns(2)
        # Mostramos lo programado originalmente
        c1.info(f"**Programado**\n\nBus: {s_data['bus_prog']}\n\nOpe: {s_data['ope_prog']}")
        with c2:
            bn = st.text_input("Bus Real:", value=s_data['bus_prog'])
            on = st.text_input("Ope Real:", value=s_data['ope_prog'])
        st.divider()
        c_soc, c_tipo, c_f = st.columns(3)
        with c_soc: soc = st.number_input("SOC%", 0, 100, 100)
        with c_tipo: tip = st.radio("Acción:", ["Normal", "RETOMA"], horizontal=True)
        with c_f: fail = st.selectbox("Incumplimiento:", ["NO", "Falta Bus", "Falta Ope", "Varado", "Congestión"])
        
        if st.form_submit_button("✅ GUARDAR REGISTRO EN NUBE", use_container_width=True):
            u_nom = st.session_state.user_info["nombre"]
            estado = "ELIMINADO" if fail != "NO" else ("RETOMA" if tip == "RETOMA" else "DESPACHO")
            
            # Guardamos en Google Sheets
            datos_nuevos = {
                "servbus": s_data['servbus'],
                "bus_real": bn,
                "ope_real": on,
                "soc": f"{soc}%",
                "estado": estado
            }
            processor.registrar_ejecucion_gsheet(datos_nuevos, u_nom)
            st.success("Registro guardado en NexOp_DB")
            st.rerun()

# --- SIDEBAR & FILTROS ---
st.sidebar.markdown(f"<h2 style='color:#1a531f; text-align:center;'>Green Móvil</h2>", unsafe_allow_html=True)
st.sidebar.write(f"👤 **{st.session_state.user_info['nombre']}**")
if st.sidebar.button("Cerrar Sesión", use_container_width=True):
    st.session_state.auth = False
    st.rerun()

# --- CARGA DE DATOS DESDE GOOGLE SHEETS ---
df = processor.cargar_datos_pantalla()

if not df.empty:
    st.sidebar.divider()
    st.sidebar.markdown("🔍 **Búsqueda Avanzada**")
    
    pir_s = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    rutas_op = ["Todas"] + (sorted(df['ruta'].unique().tolist()) if pir_s == "Todas" else processor.MAPEO_PIR[pir_s])
    ruta_s = st.sidebar.selectbox("🎯 Ruta:", rutas_op)
    
    tabla_s = st.sidebar.text_input("📋 Nro Tabla:", placeholder="Ej: 15")
    bus_s = st.sidebar.text_input("🚌 Bus (Móvil):", placeholder="Ej: Z63-4115")

    # --- LÓGICA DE FILTRADO ---
    df_f = df.copy()
    if pir_s != "Todas": df_f = df_f[df_f['punto_pir'] == pir_s]
    if ruta_s != "Todas": df_f = df_f[df_f['ruta'] == ruta_s]
    if tabla_s: df_f = df_f[df_f['tabla'].astype(str).str.contains(tabla_s)]
    if bus_s: df_f = df_f[df_f['bus_prog'].astype(str).str.contains(bus_s, case=False)]

    # --- TABS ---
    cargo = st.session_state.user_info['cargo']
    tabs_nombres = ["📊 DASHBOARD", "🚀 PIR", "📋 CONTROL", "👤 ADMIN"]
    tabs = st.tabs(tabs_nombres)

    for i, t_name in enumerate(tabs_nombres):
        with tabs[i]:
            if t_name == "📊 DASHBOARD":
                st.markdown("<h3 style='color:#1a531f;'>Métricas de Operación</h3>", unsafe_allow_html=True)
                m1, m2 = st.columns(2)
                m1.metric("TOTAL SERVICIOS", len(df_f))
                m2.metric("PUNTOS PIR", len(df_f['punto_pir'].unique()))
                st.plotly_chart(px.bar(df_f.groupby('ruta').size().reset_index(name='servicios'), x='ruta', y='servicios', title="Servicios por Ruta", color_discrete_sequence=['#1a531f']), use_container_width=True)

            elif t_name == "🚀 PIR":
                st.markdown("<h3 style='color:#1a531f;'>Gestión Operativa</h3>", unsafe_allow_html=True)
                cols_pir = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog']
                t_p = st.dataframe(df_f[cols_pir], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
                if t_p.selection.rows: ventana_gestion(df_f.iloc[t_p.selection.rows[0]])

            elif t_name == "📋 CONTROL":
                st.markdown("<h3 style='color:#1a531f;'>Reporte General</h3>", unsafe_allow_html=True)
                st.dataframe(df_f, use_container_width=True, hide_index=True)

            elif t_name == "👤 ADMIN":
                st.header("⚙️ Panel de Administración")
                
                # SECCIÓN DE SINCRONIZACIÓN SEMANAL
                with st.expander("📅 Carga de Programación desde Rigel (Semanas completas)", expanded=True):
                    st.warning("Esta acción descargará los datos de Rigel y los guardará permanentemente en Google Sheets.")
                    c1, c2 = st.columns(2)
                    f_inicio = c1.date_input("Desde:", datetime.now())
                    f_fin = c2.date_input("Hasta:", datetime.now() + timedelta(days=7))
                    
                    if st.button("🚀 INICIAR DESCARGA A NUBE", use_container_width=True):
                        with st.spinner("Conectando con Rigel..."):
                            exito = processor.sincronizar_rango_rigel(str(f_inicio), str(f_fin))
                            if exito:
                                st.success("Sincronización Completa. Datos guardados en NexOp_DB")
                                st.rerun()
                            else:
                                st.error("Error. Revisa que el Túnel Ngrok y la VPN estén activos.")

                st.divider()
                with st.form("adm_user"):
                    st.subheader("Crear Nuevo Usuario")
                    c1, c2 = st.columns(2)
                    m = c1.text_input("Correo")
                    n = c2.text_input("Nombre Completo")
                    car = c1.selectbox("Cargo", ["Auxiliar", "Tecnico", "Profesional", "Administrador"])
                    p = c2.text_input("Contraseña", type="password")
                    if st.form_submit_button("CREAR USUARIO", use_container_width=True):
                        processor.guardar_usuario(m,n,car,p)
                        st.success("Usuario creado exitosamente")
else:
    st.info("👋 ¡Bienvenido! No hay datos cargados para hoy. Ve a la pestaña ADMIN para sincronizar con Rigel.")
