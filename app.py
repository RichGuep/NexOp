import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time
import processor

APP_NAME = "NexOp | Green Móvil"
st.set_page_config(page_title=APP_NAME, layout="wide", page_icon="⚡")

try: processor.inicializar_sistema()
except: pass

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
            if st.button("INGRESAR", width='stretch'):
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
    st.markdown(f"### Servicio: {s_data['timeOrigin']} | {s_data['rutaLimpia']} | Tabla: {s_data['tabla']}")
    with st.form("f_gestion"):
        c1, c2 = st.columns(2)
        with c1: st.info(f"**Rigel**\n\nBus: {s_data['codigoBus']}\n\nOpe: {s_data['nombre']}")
        with c2:
            bn = st.text_input("Bus Real:", value=s_data['bus_real'])
            on = st.text_input("Ope Real:", value=s_data['ope_real'])
        st.divider()
        c_soc, c_tipo, c_f = st.columns(3)
        with c_soc: soc = st.number_input("SOC%", 0, 100, 100)
        with c_tipo: tip = st.radio("Acción:", ["Normal", "RETOMA"], horizontal=True)
        with c_f: fail = st.selectbox("Incumplimiento:", ["NO", "Falta Bus", "Falta Ope", "Varado", "Congestión"])
        if st.form_submit_button("✅ GUARDAR REGISTRO", width='stretch'):
            u_nom = st.session_state.user_info["nombre"]
            if fail != "NO": processor.registrar_novedad("ELIMINACION", {"servbus": s_data['servbus'], "motivo": fail}, u_nom)
            else:
                ev = "RETOMA" if tip == "RETOMA" else "DESPACHO"
                processor.registrar_novedad(ev, {"servbus": s_data['servbus'], "bus_nue": bn, "ope_nue": on, "soc": f"{soc}%"}, u_nom)
            st.rerun()

# --- SIDEBAR & FILTROS ---
st.sidebar.markdown(f"<h2 style='color:#1a531f; text-align:center;'>Green Móvil</h2>", unsafe_allow_html=True)
st.sidebar.write(f"👤 **{st.session_state.user_info['nombre']}**")
if st.sidebar.button("Cerrar Sesión", width='stretch'):
    st.session_state.auth = False
    st.rerun()

df = processor.cargar_datos_api()

if df is not None:
    st.sidebar.divider()
    st.sidebar.markdown("🔍 **Búsqueda Avanzada**")
    
    pir_s = st.sidebar.selectbox("🏠 Punto PIR:", ["Todas"] + list(processor.MAPEO_PIR.keys()))
    
    rutas_op = ["Todas"] + (sorted(df['rutaLimpia'].unique().tolist()) if pir_s == "Todas" else processor.MAPEO_PIR[pir_s])
    ruta_s = st.sidebar.selectbox("🎯 Ruta:", rutas_op)
    
    tabla_s = st.sidebar.text_input("📋 Nro Tabla:", placeholder="Ej: 15")
    tm_s = st.sidebar.text_input("🔢 Código TM:", placeholder="Ej: 631400")
    bus_s = st.sidebar.text_input("🚌 Bus (Móvil):", placeholder="Ej: Z63-4115")
    turno = st.sidebar.radio("⏰ Turno:", ["Todas", "06:00-14:00", "14:00-22:00"], horizontal=True)

    # --- LÓGICA DE FILTRADO ---
    df_f = df.copy()
    if pir_s != "Todas": df_f = df_f[df_f['punto_pir'] == pir_s]
    if ruta_s != "Todas": df_f = df_f[df_f['rutaLimpia'] == ruta_s]
    if tabla_s: df_f = df_f[df_f['tabla'].astype(str).str.contains(tabla_s)]
    if tm_s: df_f = df_f[df_f['codigoTm'].astype(str).str.contains(tm_s)]
    if bus_s: df_f = df_f[df_f['bus_real'].astype(str).str.contains(bus_s, case=False) | df_f['codigoBus'].astype(str).str.contains(bus_s, case=False)]
    if turno != "Todas":
        h_i, h_f = (time(6,0), time(14,0)) if "06" in turno else (time(14,0), time(22,0))
        df_f = df_f[(df_f['hora_dt'] >= h_i) & (df_f['hora_dt'] <= h_f)]

    # --- TABS ---
    cargo = st.session_state.user_info['cargo']
    rol = st.session_state.user_info.get('rol', 'auxiliar')
    
    tabs_nombres = ["📊 DASHBOARD"]
    if any(x in cargo for x in ["Auxiliar", "Profesional", "Administrador"]): tabs_nombres.append("🚀 PIR")
    if any(x in cargo for x in ["Tecnico", "Profesional", "Administrador"]): tabs_nombres.append("📋 CONTROL")
    if any(x in cargo for x in ["Profesional", "Administrador"]): tabs_nombres.append("👤 ADMIN")
    
    tabs = st.tabs(tabs_nombres)

    for i, t_name in enumerate(tabs_nombres):
        with tabs[i]:
            if t_name == "📊 DASHBOARD":
                st.markdown("<h3 style='color:#1a531f;'>Métricas de Operación</h3>", unsafe_allow_html=True)
                m1, m2, m3 = st.columns(3)
                kp, ke = df_f['km'].sum(), df_f['km_ejecutado'].sum()
                m1.metric("ICK", f"{(ke/kp*100 if kp>0 else 0):.1f}%")
                m2.metric("SERVICIOS", f"{len(df_f[df_f['estado_gestion'].str.contains('✅', na=False)])} / {len(df_f)}")
                m3.metric("SOC PROMEDIO", f"{df_f[df_f['soc_num'] > 0]['soc_num'].mean():.1f}%")
                st.plotly_chart(px.bar(df_f.groupby('punto_pir').agg({'km':'sum','km_ejecutado':'sum'}).reset_index(), x='punto_pir', y='km', text_auto=True), width='stretch')

            elif t_name == "🚀 PIR":
                st.markdown("<h3 style='color:#1a531f;'>Gestión Operativa</h3>", unsafe_allow_html=True)
                cols_pir = ['timeOrigin', 'bus_real', 'ope_real', 'codigoTm', 'tabla', 'estado_gestion']
                t_p = st.dataframe(df_f[cols_pir], width='stretch', hide_index=True, on_select="rerun", selection_mode="single-row")
                if t_p.selection.rows: ventana_gestion(df_f.iloc[t_p.selection.rows[0]])

            elif t_name == "📋 CONTROL":
                cols_control = ['timeOrigin', 'rutaLimpia', 'codigoBus', 'tabla', 'bus_real', 'nombre', 'ope_real', 'estado_gestion', 'soc_salida']
                st.dataframe(df_f[cols_control], width='stretch', hide_index=True)

            elif t_name == "👤 ADMIN":
                with st.form("adm"):
                    c1, c2 = st.columns(2); m, n = c1.text_input("Correo"), c2.text_input("Nombre")
                    car = c1.selectbox("Cargo", ["Auxiliar de Ejecucion de la Operacion", "Tecnicos de Ejecución de la operación", "Profesional de Ejecución de la operacion", "Administrador de Operaciones"])
                    p = c2.text_input("Contraseña")
                    if st.form_submit_button("CREAR", width='stretch'): processor.guardar_usuario(m,n,car,p); st.success("Creado")
else:
    st.error("⚠️ Sin conexión a Rigel.")