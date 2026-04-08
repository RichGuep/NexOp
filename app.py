import streamlit as st
import pandas as pd
from datetime import datetime
import processor

st.set_page_config(page_title="NexOp | Green Móvil", layout="wide", page_icon="⚡")

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    # (Lógica de login Richard Guevara...)
    st.stop()

# --- CARGAR VEHÍCULOS ---
df_buses_raw = processor.obtener_listado_buses_drive()

@st.dialog("🛠️ Gestión Operativa (PIR)", width="large")
def ventana_gestion(viaje):
    # Determinar prefijo de flota según concesión
    concesion = viaje.get('concesion', 'ZMO V')
    prefijo = "Z63-" if concesion == "ZMO III" else "Z67-"
    
    # Filtrar listado de buses para Judith
    if not df_buses_raw.empty:
        df_filtrado = df_buses_raw[df_buses_raw['Código'].astype(str).str.startswith(prefijo)]
        lista_opciones = ["N/A"] + df_filtrado['label'].tolist()
    else:
        lista_opciones = ["N/A"]

    st.markdown(f"### Servicio: `{viaje['servbus']}` | Concesión: **{concesion}**")
    st.caption(f"Solo se muestran buses con prefijo {prefijo}")

    with st.form("form_gestion"):
        c1, c2 = st.columns(2)
        with c1:
            st.write("🚌 **Flota**")
            bus_p = c1.selectbox("Bus Principal:", options=lista_opciones, 
                                index=next((i for i, x in enumerate(lista_opciones) if str(viaje['bus_prog']) in x), 0))
            bus_a = c1.selectbox("Bus Adicional:", options=lista_opciones)
            mot_b = c1.selectbox("Motivo Bus:", ["Normal", "Falta movil", "Varado", "Accidente", "Vandalismo"])

        with c2:
            st.write("👤 **Operador**")
            ope_r = c2.text_input("Operador Real", value=viaje['ope_prog'])
            mot_o = c2.selectbox("Motivo Operador:", ["Normal", "Falta operador", "Enfermo", "No llegó"])
            elim_k = c2.toggle("Eliminar Kilometraje")

        obs_f = st.text_area("📝 Observación Final")
        
        if st.form_submit_button("🚀 GUARDAR GESTIÓN", use_container_width=True):
            datos = {
                "servbus": viaje['servbus'], "bus_final": bus_p.split(" | ")[0], 
                "bus_adic": bus_a.split(" | ")[0] if bus_a != "N/A" else "",
                "motivo_bus": mot_b, "ope_final": ope_r, "motivo_ope": mot_o,
                "eliminar_km": "SI" if elim_k else "NO", "obs_final": obs_f
            }
            if processor.registrar_gestion_viaje(datos, st.session_state.user_info['nombre']):
                st.success("¡Cambios registrados!"); st.rerun()

# --- APP LAYOUT ---
df = processor.cargar_datos_pantalla()
# (Lógica de filtros Sidebar: Día, Turno, PIR, Ruta...)

with tabs[1]: # GESTIÓN PIR
    st.info(f"Consola de despacho Green Móvil")
    # Limpiar visualmente valores nulos
    df_f['bus_prog'] = df_f['bus_prog'].fillna("⚠️ SIN ASIGNAR")
    
    sel = st.dataframe(
        df_f[['timeOrigin', 'ruta', 'tabla', 'bus_prog', 'ope_prog', 'concesion', 'servbus']], 
        use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row"
    )
    
    if sel.selection.rows:
        ventana_gestion(df_f.iloc[sel.selection.rows[0]])
