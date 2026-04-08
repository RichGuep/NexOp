import streamlit as st
import pandas as pd
from pulp import *

st.set_page_config(page_title="Programador Pro - Por Cargo", layout="wide")

st.title("🗓️ Programación Modular por Cargo")

# --- 1. CARGA DE DATOS ---
try:
    df_empleados = pd.read_excel("empleados.xlsx")
    df_empleados.columns = df_empleados.columns.str.strip().str.lower()
    
    col_nombre = next((c for c in df_empleados.columns if 'nombre' in c or 'empleado' in c), None)
    col_cargo = next((c for c in df_empleados.columns if 'cargo' in c), None)
    col_descanso = next((c for c in df_empleados.columns if 'descanso' in c), None)

    df_empleados[col_nombre] = df_empleados[col_nombre].astype(str).str.strip()
    df_empleados[col_cargo] = df_empleados[col_cargo].astype(str).str.strip()
    df_empleados[col_descanso] = df_empleados[col_descanso].astype(str).str.strip().str.lower()
except Exception as e:
    st.error(f"Error al leer Excel: {e}")
    st.stop()

# --- 2. SELECCIÓN DE CARGO ---
with st.sidebar:
    st.header("🔍 Filtro de Programación")
    cargos_disponibles = sorted(df_empleados[col_cargo].unique())
    cargo_seleccionado = st.selectbox("Seleccione el Cargo a programar", cargos_disponibles)
    
    st.divider()
    st.header("⚙️ Cupos para este Cargo")
    cupo_objetivo = st.number_input(f"Cupo diario para {cargo_seleccionado}", value=2 if "master" in cargo_seleccionado.lower() else 7)
    
    st.info(f"Personal disponible para este cargo: {len(df_empleados[df_empleados[col_cargo] == cargo_seleccionado])}")

# --- 3. MOTOR DE OPTIMIZACIÓN (SOLO PARA EL CARGO SELECCIONADO) ---
if st.button(f"🚀 Generar Malla para {cargo_seleccionado}"):
    # Filtrar empleados
    df_filtrado = df_empleados[df_empleados[col_cargo] == cargo_seleccionado]
    
    semanas = [1, 2, 3, 4]
    dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    turnos = ["AM", "PM", "Noche"]
    
    prob = LpProblem("Planificacion_Modular", LpMaximize)
    asig = LpVariable.dicts("Asig", (df_filtrado[col_nombre], semanas, dias, turnos), cat='Binary')

    # OBJETIVO: Maximizar cobertura
    prob += lpSum([asig[e][s][d][t] for e in df_filtrado[col_nombre] for s in semanas for d in dias for t in turnos])

    # RESTRICCIONES
    for s in semanas:
        for d in dias:
            for t in turnos:
                # Cupo estricto por turno
                prob += lpSum([asig[e][s][d][t] for e in df_filtrado[col_nombre]]) <= cupo_objetivo

    for _, row in df_filtrado.iterrows():
        e = row[col_nombre]
        tipo_c = row[col_descanso]
        dia_fijo = "Sabado" if "sabado" in tipo_c else "Domingo"
        
        for s in semanas:
            # 1 turno al día
            for d in dias:
                prob += lpSum([asig[e][s][d][t] for t in turnos]) <= 1
            
            # Jornada de 5 días (2 descansos/dispo)
            prob += lpSum([asig[e][s][d][t] for d in dias for t in turnos]) == 5

        # Regla de los 2 fines de semana libres al mes
        prob += lpSum([asig[e][s][dia_fijo][t] for s in semanas for t in turnos]) <= 2

    prob.solve(PULP_CBC_CMD(msg=0))

    if LpStatus[prob.status] == 'Optimal':
        st.success(f"✅ Malla de {cargo_seleccionado} generada.")
        
        res = []
        for s in semanas:
            for d in dias:
                for e in df_filtrado[col_nombre]:
                    turno = "DESCANSO"
                    for t in turnos:
                        if value(asig[e][s][d][t]) == 1:
                            turno = t
                    res.append({"Semana": s, "Dia": d, "Empleado": e, "Turno": turno})

        df_res = pd.DataFrame(res)
        tabs = st.tabs([f"Semana {s}" for s in semanas])
        for i, s in enumerate(semanas):
            with tabs[i]:
                malla = df_res[df_res['Semana']==s].pivot(index='Empleado', columns='Dia', values='Turno')
                
                # Lógica de DISPO: Si tiene más de 2 descansos, el resto es DISPO
                def marcar_dispo(row):
                    d_idx = [j for j, val in enumerate(row) if val == "DESCANSO"]
                    if len(d_idx) > 2:
                        for idx in d_idx[2:]:
                            row.iloc[idx] = "DISPO"
                    return row
                
                malla_visual = malla.apply(marcar_dispo, axis=1)
                st.dataframe(malla_visual.reindex(columns=dias), use_container_width=True)
    else:
        st.error(f"❌ Imposible balancear el cargo {cargo_seleccionado}. Verifica si el personal disponible ({len(df_filtrado)}) alcanza para cubrir cupos de {cupo_objetivo*3} personas diarias con las reglas de descanso.")
