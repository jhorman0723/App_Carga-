import streamlit as st

# Configuración de página para vista móvil
st.set_page_config(
    page_title="Calculadora BYD Yuan Up",
    page_icon="⚡",
    layout="centered"
)

# Estilos visuales
st.title("⚡ BYD Yuan Up - Cargador Feyree")
st.caption("Calculadora interactiva de carga basada en datos de app Feyree (32A / ~125V)")

st.markdown("---")

# 1. PARÁMETROS CONFIGURABLES EN SIDEBAR / DESPLEGABLE
with st.expander("⚙️ Configuración del Vehículo y Carga", expanded=False):
    capacidad_bateria = st.number_input("Capacidad Batería (kWh)", value=45.1, step=0.1)
    amperaje = st.number_input("Amperaje (A)", value=32, step=1)
    voltaje = st.number_input("Voltaje Promedio (V)", value=125, step=1)
    eficiencia = st.slider("Eficiencia de Carga (%)", min_value=80, max_value=100, value=92) / 100.0
    rendimiento = st.number_input("Rendimiento (km/kWh)", value=8.33, step=0.1, help="~12 kWh por cada 100 km")
    tarifa_kwh = st.number_input("Tarifa Energía ($/kWh)", value=850, step=10)

# Potencia real calculada
potencia_kw = (amperaje * voltaje) / 1000.0

st.info(f"🔌 **Potencia Real de Carga:** {potencia_kw:.2f} kW ({amperaje}A @ {voltaje}V)")

# 2. ESTADO INICIAL
soc_inicial = st.slider("🔋 Estado de Batería Actual (SOC Inicial)", min_value=0, max_value=100, value=20, step=5) / 100.0

st.markdown("---")

# 3. SELECCIÓN DE MODO DE CÁLCULO
modo = st.radio(
    "🎯 **Selecciona qué parámetro quieres ingresar:**",
    ["Porcentaje Objetivo (%)", "Tiempo Disponible (Horas)", "Kilómetros a Cargar (km)"],
    index=0
)

st.markdown("### 📊 Resultados Proyectados")

if modo == "Porcentaje Objetivo (%)":
    soc_objetivo = st.slider("Target % (SOC Final)", min_value=int(soc_inicial*100)+5, max_value=100, value=80, step=5) / 100.0
    
    energia_req = capacidad_bateria * (soc_objetivo - soc_inicial)
    tiempo_horas = energia_req / (potencia_kw * eficiencia)
    km_ganados = energia_req * rendimiento
    costo_total = energia_req * tarifa_kwh
    
    col1, col2 = st.columns(2)
    col1.metric("⏱️ Tiempo Requerido", f"{int(tiempo_horas)}h {int((tiempo_horas%1)*60)}m")
    col2.metric("🔋 Energía Necesaria", f"{energia_req:.2f} kWh")
    
    col3, col4 = st.columns(2)
    col3.metric("🚗 Autonomía Ganada", f"{km_ganados:.0f} km")
    col4.metric("💰 Costo Estimado", f"${costo_total:,.0f} COP")

elif modo == "Tiempo Disponible (Horas)":
    horas_disp = st.number_input("Horas disponibles para cargar", min_value=0.5, max_value=24.0, value=4.5, step=0.5)
    
    energia_recargada = horas_disp * potencia_kw * eficiencia
    soc_ganado = energia_recargada / capacidad_bateria
    soc_final = min(1.0, soc_inicial + soc_ganado)
    km_ganados = energia_recargada * rendimiento
    costo_total = energia_recargada * tarifa_kwh
    
    col1, col2 = st.columns(2)
    col1.metric("🔋 SOC Final Alcanzado", f"{int(soc_final*100)}%")
    col2.metric("📈 Incremento de Batería", f"+{int(soc_ganado*100)}%")
    
    col3, col4 = st.columns(2)
    col3.metric("🚗 Autonomía Ganada", f"{km_ganados:.0f} km")
    col4.metric("💰 Costo Estimado", f"${costo_total:,.0f} COP")

elif modo == "Kilómetros a Cargar (km)":
    km_deseados = st.number_input("Kilómetros que necesitas recargar", min_value=10, max_value=400, value=200, step=10)
    
    energia_req = km_deseados / rendimiento
    tiempo_horas = energia_req / (potencia_kw * eficiencia)
    soc_ganado = energia_req / capacidad_bateria
    soc_final = min(1.0, soc_inicial + soc_ganado)
    costo_total = energia_req * tarifa_kwh
    
    col1, col2 = st.columns(2)
    col1.metric("⏱️ Tiempo Requerido", f"{int(tiempo_horas)}h {int((tiempo_horas%1)*60)}m")
    col2.metric("🔋 SOC Final Estimado", f"{int(soc_final*100)}% (+{int(soc_ganado*100)}%)")
    
    col3, col4 = st.columns(2)
    col3.metric("⚡ Energía Requerida", f"{energia_req:.2f} kWh")
    col4.metric("💰 Costo Estimado", f"${costo_total:,.0f} COP")

st.markdown("---")
st.caption("💡 *Nota: Mantén las cargas diarias entre 20% y 80% para maximizar la vida útil de la batería Blade.*")
