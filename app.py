import streamlit as st
import datetime
import pandas as pd
import sqlite3

# Configuración de página móvil
st.set_page_config(
    page_title="BYD Yuan Up - Smart Charge DB",
    page_icon="⚡",
    layout="centered"
)

# --- 1. CONFIGURACIÓN DE LA BASE DE DATOS SQLITE ---
def init_db():
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cargas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            tipo_carga TEXT,
            soc_inicial REAL,
            soc_final REAL,
            energia_kwh REAL,
            tiempo_horas REAL,
            costo_cop REAL,
            temperatura REAL,
            estado_termico TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Funciones de BD
def guardar_carga(fecha, tipo_carga, soc_i, soc_f, kwh, tiempo, costo, temp, estado):
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cargas (fecha, tipo_carga, soc_inicial, soc_final, energia_kwh, tiempo_horas, costo_cop, temperatura, estado_termico)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (fecha, tipo_carga, soc_i, soc_f, kwh, tiempo, costo, temp, estado))
    conn.commit()
    conn.close()

def actualizar_carga(id_carga, fecha, tipo_carga, soc_i, soc_f, kwh, tiempo, costo, temp, estado):
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE cargas SET fecha=?, tipo_carga=?, soc_inicial=?, soc_final=?, energia_kwh=?, tiempo_horas=?, costo_cop=?, temperatura=?, estado_termico=?
        WHERE id=?
    """, (fecha, tipo_carga, soc_i, soc_f, kwh, tiempo, costo, temp, estado, id_carga))
    conn.commit()
    conn.close()

def eliminar_carga(id_carga):
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cargas WHERE id=?", (id_carga,))
    conn.commit()
    conn.close()

def cargar_historial():
    conn = sqlite3.connect("cargas_byd.db")
    df = pd.read_sql_query("SELECT * FROM cargas ORDER BY fecha DESC, id DESC", conn)
    conn.close()
    return df

# --- 2. INTERFAZ DE USUARIO ---
st.title("⚡ BYD Yuan Up - Gestor Inteligente")
st.caption("Calculadora, control de costos por tipo de carga y base de datos histórica")

# Menú de navegación en pestañas
pestanas = st.tabs(["🧮 Calculadora", "📝 Registrar / Editar", "📊 Historial y Gráficos"])

with pestanas[0]:
    st.subheader("Simulador y Calculadora de Carga")
    
    with st.expander("⚙️ Configuración de Tarifas y Vehículo", expanded=False):
        capacidad_bateria = st.number_input("Capacidad Batería (kWh)", value=45.1, step=0.1, key="c1")
        amperaje = st.number_input("Amperaje Cargador Lento (A)", value=32, step=1, key="c2")
        voltaje = st.number_input("Voltaje Promedio Red (V)", value=125, step=1, key="c3")
        eficiencia = st.slider("Eficiencia de Carga (%)", 80, 100, 92, key="c4") / 100.0
        rendimiento = st.number_input("Rendimiento (km/kWh)", value=8.33, step=0.1, key="c5")
        
        st.markdown("---")
        st.markdown("**Tarifas de Energía (COP)**")
        tarifa_lenta = st.number_input("Tarifa Carga Lenta ($/kWh - Casa)", value=850, step=10, key="t_lenta")
        tarifa_rapida = st.number_input("Tarifa Carga Rápida ($/kWh - Electrolinera)", value=1250, step=10, key="t_rapida")

    tipo_sim = st.radio("⚡ Tipo de Carga a Simular:", ["Carga Lenta (AC / Casa)", "Carga Rápida (DC / Estación)"], key="tipo_s")
    tarifa_activa = tarifa_lenta if "Lenta" in tipo_sim else tarifa_rapida
    
    potencia_kw = (amperaje * voltaje) / 1000.0 if "Lenta" in tipo_sim else 40.0 # Estimado rápido DC
    st.info(f"🔌 **Modo Seleccionado:** {tipo_sim} | Tarifa Aplicada: **${tarifa_activa:,.0f} / kWh**")

    soc_inicial_sim = st.slider("🔋 Estado de Batería Actual (SOC Inicial)", 0, 99, 20, 5, key="c7") / 100.0
    
    modo = st.radio("🎯 ¿Qué deseas calcular?", ["Porcentaje Objetivo (%)", "Tiempo Disponible (Horas)", "Kilómetros Deseados (km)"], key="c8")

    energia_req = 0
    tiempo_horas = 0
    km_ganados = 0
    costo_total = 0
    soc_final = soc_inicial_sim

    if modo == "Porcentaje Objetivo (%)":
        target_pct = st.slider("Target % (SOC Final deseado)", int(soc_inicial_sim*100)+5, 100, 80, 5, key="c9")
        soc_objetivo = target_pct / 100.0
        energia_req = capacidad_bateria * (soc_objetivo - soc_inicial_sim)
        tiempo_horas = energia_req / (potencia_kw * eficiencia)
        km_ganados = energia_req * rendimiento
        costo_total = energia_req * tarifa_activa
        soc_final = soc_objetivo

    elif modo == "Tiempo Disponible (Horas)":
        horas_disp = st.number_input("Horas disponibles", 0.5, 24.0, 4.0, 0.5, key="c10")
        energia_req = horas_disp * potencia_kw * eficiencia
        soc_ganado = energia_req / capacidad_bateria
        soc_final = min(1.0, soc_inicial_sim + soc_ganado)
        tiempo_horas = horas_disp
        km_ganados = energia_req * rendimiento
        costo_total = energia_req * tarifa_activa

    elif modo == "Kilómetros Deseados (km)":
        km_deseados = st.number_input("Kilómetros necesarios", 10, 400, 150, 10, key="c11")
        energia_req = km_deseados / rendimiento
        tiempo_horas = energia_req / (potencia_kw * eficiencia)
        soc_ganado = energia_req / capacidad_bateria
        soc_final = min(1.0, soc_inicial_sim + soc_ganado)
        km_ganados = km_deseados
        costo_total = energia_req * tarifa_activa

    st.markdown(f"**Evolución:** `{int(soc_inicial_sim*100)}%` ➡️ `{int(soc_final*100)}%`")
    st.progress(float(soc_final))

    col1, col2 = st.columns(2)
    col1.metric("⏱️ Tiempo Estimado", f"{int(tiempo_horas)}h {int((tiempo_horas%1)*60)}m")
    col2.metric("⚡ Energía Requerida", f"{energia_req:.2f} kWh")

    col3, col4 = st.columns(2)
    col3.metric("🚗 Autonomía", f"{km_ganados:.0f} km")
    col4.metric("💰 Costo Estimado", f"${costo_total:,.0f} COP")

with pestanas[1]:
    st.subheader("📝 Registrar, Actualizar o Eliminar Cargas")
    
    # Selector de acción
    accion = st.radio("Selecciona una acción:", ["➕ Registrar Nueva Carga", "✏️ Actualizar Registro Existente", "🗑️ Eliminar Registro"], horizontal=True)
    
    if accion == "➕ Registrar Nueva Carga":
        with st.form("form_db_carga"):
            f_fecha = st.date_input("Fecha de la carga", value=datetime.date.today())
            f_tipo = st.selectbox("Tipo de Carga", ["Carga Lenta (AC)", "Carga Rápida (DC)"])
            f_soc_i = st.slider("SOC Inicial (%)", 0, 99, 20, 1)
            f_soc_f = st.slider("SOC Final (%)", 1, 100, 80, 1)
            f_kwh = st.number_input("Energía entregada (kWh)", value=35.0, step=0.1)
            f_tiempo = st.number_input("Tiempo total (Horas)", value=8.5, step=0.1)
            
            # Cálculo automático del costo según tipo de carga predeterminado
            tarifa_def = 850 if "Lenta" in f_tipo else 1250
            f_costo = st.number_input("Costo total automático (COP)", value=f_kwh * tarifa_def, step=500.0)
            
            f_temp = st.number_input("Temperatura máxima (°C)", value=51.5, step=0.5)
            
            submitted = st.form_submit_button("💾 Guardar en Base de Datos")
            if submitted:
                estado_t = "Normal" if f_temp <= 55 else "Revisar Calor"
                guardar_carga(str(f_fecha), f_tipo, f_soc_i, f_soc_f, f_kwh, f_tiempo, f_costo, f_temp, estado_t)
                st.success("¡Carga guardada exitosamente!")

    elif accion == "✏️ Actualizar Registro Existente":
        df_edit = cargar_historial()
        if not df_edit.empty:
            id_sel = st.selectbox("Selecciona el ID de la carga a editar:", df_edit['id'].tolist())
            row_data = df_edit[df_edit['id'] == id_sel].iloc[0]
            
            with st.form("form_update"):
                u_fecha = st.date_input("Fecha", value=datetime.datetime.strptime(row_data['fecha'], "%Y-%m-%d").date())
                u_tipo = st.selectbox("Tipo de Carga", ["Carga Lenta (AC)", "Carga Rápida (DC)"], index=0 if "Lenta" in row_data['tipo_carga'] else 1)
                u_soc_i = st.slider("SOC Inicial (%)", 0, 99, int(row_data['soc_inicial']))
                u_soc_f = st.slider("SOC Final (%)", 1, 100, int(row_data['soc_final']))
                u_kwh = st.number_input("Energía (kWh)", value=float(row_data['energia_kwh']))
                u_tiempo = st.number_input("Tiempo (Horas)", value=float(row_data['tiempo_horas']))
                u_costo = st.number_input("Costo (COP)", value=float(row_data['costo_cop']))
                u_temp = st.number_input("Temperatura (°C)", value=float(row_data['temperatura']))
                
                update_btn = st.form_submit_button("🔄 Actualizar Registro")
                if update_btn:
                    estado_t = "Normal" if u_temp <= 55 else "Revisar Calor"
                    actualizar_carga(id_sel, str(u_fecha), u_tipo, u_soc_i, u_soc_f, u_kwh, u_tiempo, u_costo, u_temp, estado_t)
                    st.success(f"¡Registro ID {id_sel} actualizado correctamente!")
        else:
            st.info("No hay registros para actualizar.")

    elif accion == "🗑️ Eliminar Registro":
        df_del = cargar_historial()
        if not df_del.empty:
            id_del = st.selectbox("Selecciona el ID de la carga a eliminar:", df_del['id'].tolist())
            if st.button("⚠️ Confirmar Eliminación"):
                eliminar_carga(id_del)
                st.success(f"¡Registro ID {id_del} eliminado con éxito!")
                st.rerun()
        else:
            st.info("No hay registros para eliminar.")

with pestanas[2]:
    st.subheader("📊 Historial y Gráficos de Consumo")
    df_graf = cargar_historial()
    
    if not df_graf.empty:
        st.dataframe(df_graf, use_container_width=True)
        
        df_graf['fecha'] = pd.to_datetime(df_graf['fecha'])
        df_graf = df_graf.sort_values('fecha')
        
        st.markdown("### ⚡ Consumo de Energía (kWh)")
        st.line_chart(df_graf.set_index('fecha')['energia_kwh'])
        
        st.markdown("### 💰 Costo Acumulado de Recargas (COP)")
        st.bar_chart(df_graf.set_index('fecha')['costo_cop'])
        
        st.markdown("---")
        total_kwh = df_graf['energia_kwh'].sum()
        total_costo = df_graf['costo_cop'].sum()
        
        m1, m2 = st.columns(2)
        m1.metric("Total kWh Inyectados", f"{total_kwh:.2f} kWh")
        m2.metric("Gasto Total Histórico", f"${total_costo:,.0f} COP")
    else:
        st.warning("⚠️ No hay datos registrados todavía.")
