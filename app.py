import streamlit as st
import datetime
import pandas as pd

# Configuración de página móvil
st.set_page_config(
    page_title="BYD Yuan Up - Smart Charge",
    page_icon="⚡",
    layout="centered"
)

# Título principal
st.title("⚡ BYD Yuan Up - Smart Calculator")
st.caption("Panel de control y auditoría de carga (Inspirado en App Feyree)")

# Inicializar historial en memoria de sesión si no existe
if "historial" not in st.session_state:
    st.session_state.historial = [
        {"Fecha": "2026-08-20", "Energía (kWh)": 37.7, "Temp (°C)": 51.3, "Estado": "Normal"},
        {"Fecha": "2026-08-21", "Energía (kWh)": 37.6, "Temp (°C)": 50.4, "Estado": "Normal"},
        {"Fecha": "2026-08-22", "Energía (kWh)": 44.4, "Temp (°C)": 52.8, "Estado": "Normal"},
    ]

# 1. PARÁMETROS GENERALES
with st.expander("⚙️ Configuración del Vehículo y Red", expanded=False):
    capacidad_bateria = st.number_input("Capacidad Batería (kWh)", value=45.1, step=0.1)
    amperaje = st.number_input("Amperaje (A)", value=32, step=1)
    voltaje = st.number_input("Voltaje Promedio (V)", value=125, step=1)
    eficiencia = st.slider("Eficiencia de Carga (%)", min_value=80, max_value=100, value=92) / 100.0
    rendimiento = st.number_input("Rendimiento (km/kWh)", value=8.33, step=0.1)
    tarifa_kwh = st.number_input("Tarifa Energía ($/kWh)", value=850, step=10)

potencia_kw = (amperaje * voltaje) / 1000.0

st.info(f"🔌 **Potencia Real de Transferencia:** {potencia_kw:.2f} kW ({amperaje}A @ {voltaje}V)")

# 2. ESTADO ACTUAL DE LA BATERÍA
soc_inicial = st.slider("🔋 Estado de Batería Actual (SOC Inicial)", min_value=0, max_value=99, value=20, step=5) / 100.0

st.markdown("---")

# 3. SELECCIÓN DE MODO
modo = st.radio(
    "🎯 **¿Cómo deseas calcular tu carga?**",
    ["Porcentaje Objetivo (%)", "Tiempo Disponible (Horas)", "Kilómetros Deseados (km)"],
    index=0
)

st.markdown("### 📊 Resultados y Proyecciones")

# Variables globales para resultados
energia_req = 0
tiempo_horas = 0
km_ganados = 0
costo_total = 0
soc_final = soc_inicial

if modo == "Porcentaje Objetivo (%)":
    target_pct = st.slider("Target % (SOC Final deseado)", min_value=int(soc_inicial*100)+5, max_value=100, value=80, step=5)
    soc_objetivo = target_pct / 100.0
    
    energia_req = capacidad_bateria * (soc_objetivo - soc_inicial)
    tiempo_horas = energia_req / (potencia_kw * eficiencia)
    km_ganados = energia_req * rendimiento
    costo_total = energia_req * tarifa_kwh
    soc_final = soc_objetivo

elif modo == "Tiempo Disponible (Horas)":
    horas_disp = st.number_input("Horas disponibles conectado", min_value=0.5, max_value=24.0, value=4.0, step=0.5)
    
    energia_req = horas_disp * potencia_kw * eficiencia
    soc_ganado = energia_req / capacidad_bateria
    soc_final = min(1.0, soc_inicial + soc_ganado)
    tiempo_horas = horas_disp
    km_ganados = energia_req * rendimiento
    costo_total = energia_req * tarifa_kwh

elif modo == "Kilómetros Deseados (km)":
    km_deseados = st.number_input("Kilómetros que necesitas recorrer", min_value=10, max_value=400, value=150, step=10)
    
    energia_req = km_deseados / rendimiento
    tiempo_horas = energia_req / (potencia_kw * eficiencia)
    soc_ganado = energia_req / capacidad_bateria
    soc_final = min(1.0, soc_inicial + soc_ganado)
    km_ganados = km_deseados
    costo_total = energia_req * tarifa_kwh

# Visualizador de Progreso (Barra de batería estimada)
st.markdown(f"**Evolución del SOC:** `{int(soc_inicial*100)}%` ➡️ `{int(soc_final*100)}%`")
st.progress(float(soc_final))

# Métricas principales en columnas
col1, col2 = st.columns(2)
col1.metric("⏱️ Tiempo Estimado", f"{int(tiempo_horas)}h {int((tiempo_horas%1)*60)}m")
col2.metric("⚡ Energía Requerida", f"{energia_req:.2f} kWh")

col3, col4 = st.columns(2)
col3.metric("🚗 Autonomía Ganada", f"{km_ganados:.0f} km")
col4.metric("💰 Costo Estimado", f"${costo_total:,.0f} COP")

# Cálculo de hora de finalización
hora_fin = datetime.datetime.now() + datetime.timedelta(hours=tiempo_horas)
st.success(f"⏰ Si conectas el carro ahora, terminará de cargar aproximadamente a las **{hora_fin.strftime('%I:%M %p')}**")

st.markdown("---")

# 4. MÓDULO DE AUDITORÍA TÉRMICA Y BITÁCORA
with st.expander("🌡️ Auditoría Térmica y Registro de Carga"):
    st.subheader("Control de Temperatura (Feyree)")
    temp_actual = st.slider("Temperatura registrada en el dispositivo (°C)", min_value=30.0, max_value=70.0, value=51.5, step=0.5)
    
    if temp_actual < 50:
        st.success("🟢 Temperatura Óptima: El equipo opera en condiciones normales y seguras.")
    elif temp_actual <= 55:
        st.warning("🟡 Temperatura Moderada: Rango habitual para cargas largas a 32A. Vigilar ventilación.")
    else:
        st.error("🔴 ¡Alerta de Temperatura Alta! Supera los 55°C. Se recomienda revisar la toma de corriente y evitar el calor directo.")
    
    st.markdown("---")
    st.subheader("Registrar Sesión en el Historial")
    with st.form("form_historial"):
        f_fecha = st.date_input("Fecha de carga")
        f_kwh = st.number_input("kWh entregados según app", value=round(energia_req, 2))
        f_temp = st.number_input("Temperatura máxima (°C)", value=temp_actual)
        submitted = st.form_submit_button("Guardar en Bitácora")
        
        if submitted:
            estado_t = "Normal" if f_temp <= 55 else "Revisar Calor"
            st.session_state.historial.append({
                "Fecha": str(f_fecha),
                "Energía (kWh)": f_kwh,
                "Temp (°C)": f_temp,
                "Estado": estado_t
            })
            st.success("¡Sesión guardada exitosamente en el historial!")

    st.markdown("### 📋 Historial de Cargas Registradas")
    df_hist = pd.DataFrame(st.session_state.historial)
    st.dataframe(df_hist, use_container_width=True)

st.markdown("---")
st.caption("💡 **Consejo BYD:** Mantén el uso diario de la batería Blade entre el 20% y el 80% para maximizar su vida útil a largo plazo.")
