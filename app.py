import streamlit as st
import pandas as pd
import processor
from datetime import datetime

ADMIN_EMAIL = "richard.guevara@greenmovil.com.co"
st.set_page_config(page_title="NexOp | Green Móvil", layout="wide", page_icon="⚡")

if "auth" not in st.session_state: st.session_state.auth = False

# --- LOGIN (Resumido) ---
if not st.session_state.auth:
    c2 = st.columns([1,1.2,1])[1]
    with c2:
        u = st.text_input("Usuario").lower().strip()
        p = st.text_input("Contraseña", type="password")
        if st.button("INGRESAR"):
            users = processor.obtener_usuarios()
            if u in users and str(users[u].get('pw')) == p:
                st.session_state.auth = True; st.session_state.user_info = users[u]; st.rerun()
    st.stop()

# --- POPUP MEJORADO ---
@st.dialog("🛠️ Gestión Operativa (PIR)", width="large")
def ventana_gestion(viaje):
    empresa = viaje.get('empresa', 'ZMO V')
    prefijo = "Z63-" if empresa == "ZMO III" else "Z67-"
    
    # Cargar y filtrar flota de la empresa correspondiente
    df_b = processor.obtener_listado_buses_drive()
    df_filtrado = df_b[df_b['Código'].astype(str).str.startswith(prefijo)] if not df_b.empty else pd.DataFrame()
    lista_opciones = ["N/A"] + df_filtrado['label'].tolist()
    
    # 🎯 Lógica para traer por defecto el bus programado en el selectbox
    bus_prog_str = str(viaje['bus_prog'])
    try:
        index_defecto = next(i for i, x in enumerate(lista_opciones) if bus_prog_str in x)
    except StopIteration:
        index_defecto = 0

    st.markdown(f"### Servicio: `{viaje['servbus']}` | Empresa: **{empresa}**")
    
    with st.form("form_gestion_final"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🚌 Vehículo")
            bus_real = c1.selectbox("Bus Real:", options=lista_opciones, index=index_defecto)
            motivo_m = c1.selectbox("Motivo:", ["Operación Normal", "RETOMA", "Falta movil", "Bus varado", "Accidente"])
        with c2:
            st.markdown("#### 👤 Operador")
            # 🎯 El nombre ya viene escrito por defecto
            ope_real = c2.text_input("Operador Real:", value=viaje['ope_prog'])
            motivo_o = c2.selectbox("Motivo:", ["Operación Normal", "Falta operador", "Enfermo", "No llegó"])
            elim_k = c2.toggle("Eliminar KM")
        
        st.divider()
        obs = st.text_area("Observaciones Finales")
        
        if st.form_submit_button("✅ GUARDAR CAMBIOS", use_container_width=True):
            datos = {
                "servbus": viaje['servbus'], "bus_prog": viaje['bus_prog'],
                "bus_real": bus_real.split(" | ")[0] if " | " in bus_real else bus_real,
                "motivo_movil": motivo_m, "ope_prog": viaje['ope_prog'],
                "ope_real": ope_real, "motivo_ope": motivo_o,
                "eliminar_km": "SI" if elim_k else "NO", "obs_final": obs
            }
            if processor.aplicar_gestion_servicio(datos, st.session_state.user_info['nombre']):
                st.success("Cambios Guardados"); st.rerun()

# --- APP ---
st.markdown("<h1 style='text-align:center;'>NexOp | Green Móvil</h1>", unsafe_allow_html=True)
df = processor.cargar_datos_pantalla()

u_info = st.session_state.user_info
is_admin = (u_info.get('correo') == ADMIN_EMAIL or str(u_info.get('rol')).lower() == 'admin')
tabs = st.tabs(["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO", "⚙️ CONFIG"] if is_admin else ["📊 ESTADÍSTICAS", "🚀 GESTIÓN PIR", "📋 SEGUIMIENTO"])

if not df.empty:
    # Filtros sidebar
    f_sel = st.sidebar.selectbox("📅 Día:", sorted(df['fecha'].unique().tolist()))
    df_f = df[df['fecha'] == f_sel].copy()
    
    with tabs[1]: # GESTIÓN PIR
        cols = ['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'empresa', 'servbus']
        sel = st.dataframe(df_f[cols], use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if sel.selection.rows:
            ventana_gestion(df_f.iloc[sel.selection.rows[0]])

if is_admin:
    with tabs[-1]:
        if st.button("SINCRONIZAR RIGEL"):
            processor.sincronizar_semana_por_dias(str(st.date_input("I")), str(st.date_input("F")))
