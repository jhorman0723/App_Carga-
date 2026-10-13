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
def guardar_carga(fecha, soc_i, soc_f, kwh, tiempo, costo, temp, estado):
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO cargas (fecha, soc_inicial, soc_final, energia_kwh, tiempo_horas, costo_cop, temperatura, estado_termico)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (fecha, soc_i, soc_f, kwh, tiempo, costo, temp, estado))
    conn.commit()
    conn.close()

def cargar_historial():
    conn = sqlite3.connect("cargas_byd.db")
    df = pd.read_sql_query("SELECT * FROM cargas ORDER BY fecha DESC, id DESC", conn)
    conn.close()
    return df

# --- 2. INTERFAZ DE USUARIO ---
st.title("⚡ BYD Yuan Up - Registro y Base de Datos")
st.caption("Calculadora inteligente y almacenamiento histórico de cargas (App Feyree)")

# Menú de navegación en pestañas
pestanas = st.tabs(["🧮 Calculadora", "📝 Registrar Sesión", "📊 Gráficos y Estadísticas"])

with pestanas[0]:
    st.subheader("Simulador y Calculadora de Carga")
    
    with st.expander("⚙️ Parámetros del Vehículo y Red", expanded=False):
        capacidad_bateria = st.number_input("Capacidad Batería (kWh)", value=45.1, step=0.1, key="c1")
        amperaje = st.number_input("Amperaje (A)", value=32, step=1, key="c2")
        voltaje = st.number_input("Voltaje Promedio (V)", value=125, step=1, key="c3")
        eficiencia = st.slider("Eficiencia de Carga (%)", 80, 100, 92, key="c4") / 100.0
        rendimiento = st.number_input("Rendimiento (km/kWh)", value=8.33, step=0.1, key="c5")
        tarifa_kwh = st.number_input("Tarifa Energía ($/kWh)", value=850, step=10, key="c6")

    potencia_kw = (amperaje * voltaje) / 1000.0
    st.info(f"🔌 **Potencia Real:** {potencia_kw:.2f} kW ({amperaje}A @ {voltaje}V)")

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
        costo_total = energia_req * tarifa_kwh
        soc_final = soc_objetivo

    elif modo == "Tiempo Disponible (Horas)":
        horas_disp = st.number_input("Horas disponibles", 0.5, 24.0, 4.0, 0.5, key="c10")
        energia_req = horas_disp * potencia_kw * eficiencia
        soc_ganado = energia_req / capacidad_bateria
        soc_final = min(1.0, soc_inicial_sim + soc_ganado)
        tiempo_horas = horas_disp
        km_ganados = energia_req * rendimiento
        costo_total = energia_req * tarifa_kwh

    elif modo == "Kilómetros Deseados (km)":
        km_deseados = st.number_input("Kilómetros necesarios", 10, 400, 150, 10, key="c11")
        energia_req = km_deseados / rendimiento
        tiempo_horas = energia_req / (potencia_kw * eficiencia)
        soc_ganado = energia_req / capacidad_bateria
        soc_final = min(1.0, soc_inicial_sim + soc_ganado)
        km_ganados = km_deseados
        costo_total = energia_req * tarifa_kwh

    st.markdown(f"**Evolución:** `{int(soc_inicial_sim*100)}%` ➡️ `{int(soc_final*100)}%`")
    st.progress(float(soc_final))

    col1, col2 = st.columns(2)
    col1.metric("⏱️ Tiempo Estimado", f"{int(tiempo_horas)}h {int((tiempo_horas%1)*60)}m")
    col2.metric("⚡ Energía Requerida", f"{energia_req:.2f} kWh")

    col3, col4 = st.columns(2)
    col3.metric("🚗 Autonomía", f"{km_ganados:.0f} km")
    col4.metric("💰 Costo", f"${costo_total:,.0f} COP")

with pestanas[1]:
    st.subheader("📝 Registrar Nueva Carga Realizada")
    st.caption("Guarda los datos de tu cargador Feyree directamente en la base de datos.")
    
    with st.form("form_db_carga"):
        f_fecha = st.date_input("Fecha de la carga", value=datetime.date.today())
        f_soc_i = st.slider("SOC Inicial (%)", 0, 99, 20, 1)
        f_soc_f = st.slider("SOC Final (%)", 1, 100, 80, 1)
        f_kwh = st.number_input("Energía total entregada (kWh según app Feyree)", value=35.0, step=0.1)
        f_tiempo = st.number_input("Tiempo total de carga (Horas)", value=8.5, step=0.1)
        f_costo = st.number_input("Costo total de la recarga (COP)", value=29750.0, step=500.0)
        f_temp = st.number_input("Temperatura máxima del dispositivo (°C)", value=51.5, step=0.5)
        
        submitted = st.form_submit_button("💾 Guardar en Base de Datos")
        
        if submitted:
            estado_t = "Normal" if f_temp <= 55 else "Revisar Calor"
            guardar_carga(str(f_fecha), f_soc_i, f_soc_f, f_kwh, f_tiempo, f_costo, f_temp, estado_t)
            st.success("¡Carga registrada y almacenada en la base de datos con éxito!")

    st.markdown("---")
    st.subheader("📋 Historial Completo Almacenado")
    df_logs = cargar_historial()
    if not df_logs.empty:
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("Aún no hay registros guardados. Usa el formulario de arriba para agregar cargas.")

with pestanas[2]:
    st.subheader("📊 Gráficos de Consumo y Tendencias")
    df_graf = cargar_historial()
    
    if not df_graf.empty and len(df_graf) > 0:
        # Convertir fecha a datetime para ordenar si es necesario
        df_graf['fecha'] = pd.to_datetime(df_graf['fecha'])
        df_graf = df_graf.sort_values('fecha')
        
        st.markdown("### ⚡ Consumo de Energía (kWh por Carga)")
        st.line_chart(df_graf.set_index('fecha')['energia_kwh'])
        
        st.markdown("### 💰 Costo Acumulado de Recargas (COP)")
        st.bar_chart(df_graf.set_index('fecha')['costo_cop'])
        
        st.markdown("### 🌡️ Comportamiento Térmico del Cargador (°C)")
        st.line_chart(df_graf.set_index('fecha')['temperatura'])
        
        # Resumen de estadísticas
        st.markdown("---")
        st.subheader("📈 Métricas Generales")
        total_kwh = df_graf['energia_kwh'].sum()
        total_costo = df_graf['costo_cop'].sum()
        prom_temp = df_graf['temperatura'].mean()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Energía Acumulada", f"{total_kwh:.2f} kWh")
        m2.metric("Gasto Total", f"${total_costo:,.0f} COP")
        m3.metric("Temp. Promedio", f"{prom_temp:.1f} °C")
    else:
        st.warning("⚠️ No hay suficientes datos en la base de datos para generar los gráficos. Registra al menos una carga en la pestaña anterior.")
