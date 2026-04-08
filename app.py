import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import processor

st.set_page_config(page_title="NexOp | Green Móvil", layout="wide", page_icon="⚡")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h2 style='text-align:center;'>🔐 NexOp Login</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Correo").lower().strip()
        p_in = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR", use_container_width=True):
            users = processor.obtener_usuarios()
            # Validamos contra el diccionario traído del Drive
            if u_in in users and str(users[u_in]["pw"]) == p_in:
                st.session_state.auth = True
                st.session_state.user_info = users[u_in]
                st.rerun()
            else: st.error("Correo o contraseña incorrectos")
    st.stop()

# --- INTERFAZ ---
st.sidebar.title("Green Móvil")
st.sidebar.write(f"👤 {st.session_state.user_info['nombre']}")

df = processor.cargar_datos_pantalla()
tabs = st.tabs(["📊 DASHBOARD", "🚀 PIR", "📋 CONTROL", "⚙️ ADMIN"])

# (Contenido de Dashboard, PIR y Control queda igual...)

# --- PESTAÑA ADMIN (RECONSTRUIDA) ---
with tabs[3]:
    st.header("⚙️ Administración General")
    
    # SECCIÓN 1: DESCARGA RIGEL
    with st.expander("🚀 Sincronización Rigel (Semanal)", expanded=False):
        c1, c2 = st.columns(2)
        f_i = c1.date_input("Inicio", datetime.now())
        f_f = c2.date_input("Fin", datetime.now() + timedelta(days=7))
        if st.button("DESCARGAR DATOS"):
            if processor.sincronizar_semana_por_dias(str(f_i), str(f_f)):
                st.success("¡Datos actualizados!"); st.rerun()

    st.divider()

    # SECCIÓN 2: GESTIÓN DE PERSONAL (NUEVO PANEL)
    st.subheader("👥 Gestión de Usuarios")
    col_u1, col_u2 = st.columns([1, 2])
    
    with col_u1:
        with st.form("nuevo_usuario", clear_on_submit=True):
            st.write("**Registrar Nuevo**")
            n_mail = st.text_input("Correo electrónico")
            n_nom = st.text_input("Nombre completo")
            n_car = st.selectbox("Cargo", ["Administrador", "Auxiliar PIR", "Técnico"])
            n_pass = st.text_input("Contraseña temporal")
            if st.form_submit_button("CREAR USUARIO"):
                if processor.guardar_usuario(n_mail, n_nom, n_car, n_pass):
                    st.success("Usuario guardado en Drive")
                    st.rerun()
    
    with col_u2:
        st.write("**Usuarios Activos en Drive**")
        usuarios_db = processor.obtener_usuarios()
        df_users = pd.DataFrame.from_dict(usuarios_db, orient='index').reset_index()
        st.dataframe(df_users[['index', 'nombre', 'cargo']], use_container_width=True, hide_index=True)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.auth = False
    st.rerun()
