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
    
    # Tabla de cargas históricas
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
    
    # Tabla de configuración global (Tarifas y Vehículo)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            capacidad_bateria REAL,
            amperaje REAL,
            voltaje REAL,
            eficiencia REAL,
            rendimiento REAL,
            tarifa_lenta REAL,
            tarifa_rapida REAL
        )
    """)
    
    # Insertar configuración por defecto si no existe
    cursor.execute("""
        INSERT OR IGNORE INTO configuracion (id, capacidad_bateria, amperaje, voltaje, eficiencia, rendimiento, tarifa_lenta, tarifa_rapida)
        VALUES (1, 45.1, 32, 125, 0.92, 8.33, 850.0, 1250.0)
    """)
    
    conn.commit()
    conn.close()

init_db()

# Funciones de configuración
def obtener_config():
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("SELECT capacidad_bateria, amperaje, voltaje, eficiencia, rendimiento, tarifa_lenta, tarifa_rapida FROM configuracion WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    return {
        "capacidad_bateria": row[0],
        "amperaje": row[1],
        "voltaje": row[2],
        "eficiencia": row[3],
        "rendimiento": row[4],
        "tarifa_lenta": row[5],
        "tarifa_rapida": row[6]
    }

def actualizar_config(cap, amp, volt, ef, rend, t_lenta, t_rapida):
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE configuracion 
        SET capacidad_bateria=?, amperaje=?, voltaje=?, eficiencia=?, rendimiento=?, tarifa_lenta=?, tarifa_rapida=?
        WHERE id=1
    """, (cap, amp, volt, ef, rend, t_lenta, t_rapida))
    conn.commit()
    conn.close()

# Funciones de cargas
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

# Obtener configuración actual de la BD
config = obtener_config()

# --- 2. INTERFAZ DE USUARIO ---
st.title("⚡ BYD Yuan Up - Gestor Inteligente")
st.caption("Calculadora, control de costos automatizado y base de datos con configuración persistente")

# Menú de navegación en pestañas
pestanas = st.tabs(["🧮 Calculadora", "⚙️ Configuración", "📝 Registrar / Editar", "📊 Historial y Gráficos"])

with pestanas[0]:
    st.subheader("Simulador y Calculadora de Carga")
    
    text_info = f"⚙️ Parámetros activos en BD: Batería: {config['capacidad_bateria']} kWh - Lenta: ${config['tarifa_lenta']:,.0f}/kWh - Rápida: ${config['tarifa_rapida']:,.0f}/kWh"
    st.info(text_info)

    tipo_sim = st.radio("⚡ Tipo de Carga a Simular:", ["Carga Lenta (AC / Casa)", "Carga Rápida (DC / Estación)"], key="tipo_s")
    tarifa_activa = config['tarifa_lenta'] if "Lenta" in tipo_sim else config['tarifa_rapida']
    
    potencia_kw = (config['amperaje'] * config['voltaje']) / 1000.0 if "Lenta" in tipo_sim else 40.0
    st.write(f"🔌 Potencia Real de Transferencia: **{potencia_kw:.2f} kW** - Tarifa Aplicada: **${tarifa_activa:,.0f} / kWh**")

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
        energia_req = config['capacidad_bateria'] * (soc_objetivo - soc_inicial_sim)
        tiempo_horas = energia_req / (potencia_kw * config['eficiencia'])
        km_ganados = energia_req * config['rendimiento']
        costo_total = energia_req * tarifa_activa
        soc_final = soc_objetivo

    elif modo == "Tiempo Disponible (Horas)":
        horas_disp = st.number_input("Horas disponibles", 0.5, 24.0, 4.0, 0.5, key="c10")
        energia_req = horas_disp * potencia_kw * config['eficiencia']
        soc_ganado = energia_req / config['capacidad_bateria']
        soc_final = min(1.0, soc_inicial_sim + soc_ganado)
        tiempo_horas = horas_disp
        km_ganados = energia_req * config['rendimiento']
        costo_total = energia_req * tarifa_activa

    elif modo == "Kilómetros Deseados (km)":
        km_deseados = st.number_input("Kilómetros necesarios", 10, 400, 150, 10, key="c11")
        energia_req = km_deseados / config['rendimiento']
        tiempo_horas = energia_req / (potencia_kw * config['eficiencia'])
        soc_ganado = energia_req / config['capacidad_bateria']
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
    st.subheader("⚙️ Gestión de Configuración y Tarifas en Base de Datos")
    st.caption("Modifica y actualiza los parámetros generales del vehículo y las tarifas de energía.")
    
    with st.form("form_config"):
        new_cap = st.number_input("Capacidad Batería (kWh)", value=float(config['capacidad_bateria']), step=0.1)
        new_amp = st.number_input("Amperaje Cargador Lento (A)", value=float(config['amperaje']), step=1.0)
        new_volt = st.number_input("Voltaje Promedio Red (V)", value=float(config['voltaje']), step=1.0)
        new_ef = st.slider("Eficiencia de Carga (%)", 80, 100, int(config['eficiencia'] * 100)) / 100.0
        new_rend = st.number_input("Rendimiento (km/kWh)", value=float(config['rendimiento']), step=0.01)
        
        st.markdown("---")
        new_tlenta = st.number_input("Tarifa Carga Lenta ($/kWh - Casa)", value=float(config['tarifa_lenta']), step=10.0)
        new_trapida = st.number_input("Tarifa Carga Rápida ($/kWh - Estación)", value=float(config['tarifa_rapida']), step=10.0)
        
        save_config_btn = st.form_submit_button("💾 Guardar y Actualizar Configuración")
        if save_config_btn:
            actualizar_config(new_cap, new_amp, new_volt, new_ef, new_rend, new_tlenta, new_trapida)
            st.success("¡Configuración actualizada en la base de datos con éxito! Recarga la página o cambia de pestaña para aplicar los cambios.")

with pestanas[2]:
    st.subheader("📝 Registrar, Actualizar o Eliminar Cargas")
    
    accion = st.radio("Selecciona una acción:", ["➕ Registrar Nueva Carga", "✏️ Actualizar Registro Existente", "🗑️ Eliminar Registro"], horizontal=True)
    
    if accion == "➕ Registrar Nueva Carga":
        with st.form("form_db_carga"):
            f_fecha = st.date_input("Fecha de la carga", value=datetime.date.today())
            f_tipo = st.selectbox("Tipo de Carga", ["Carga Lenta (AC)", "Carga Rápida (DC)"])
            f_soc_i = st.slider("SOC Inicial (%)", 0, 99, 20, 1)
            f_soc_f = st.slider("SOC Final (%)", 1, 100, 80, 1)
            f_kwh = st.number_input("Energía entregada (kWh según app o estación)", value=35.0, step=0.1)
            f_tiempo = st.number_input("Tiempo total (Horas)", value=8.5, step=0.1)
            
            # Cálculo automático del costo según la tarifa guardada en la base de datos
            tarifa_aplicada = config['tarifa_lenta'] if "Lenta" in f_tipo else config['tarifa_rapida']
            costo_calculado = f_kwh * tarifa_aplicada
            
            st.info(f"💰 Costo calculado automáticamente según tarifa configurada (${tarifa_aplicada:,.0f}/kWh): **${costo_calculado:,.0f} COP**")
            
            f_temp = st.number_input("Temperatura máxima (°C)", value=51.5, step=0.5)
            
            submitted = st.form_submit_button("💾 Guardar en Base de Datos")
            if submitted:
                estado_t = "Normal" if f_temp <= 55 else "Revisar Calor"
                guardar_carga(str(f_fecha), f_tipo, f_soc_i, f_soc_f, f_kwh, f_tiempo, costo_calculado, f_temp, estado_t)
                st.success("¡Carga guardada exitosamente con costo calculado automáticamente!")

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
                
                # Recalcular automáticamente costo sugerido
                t_ap = config['tarifa_lenta'] if "Lenta" in u_tipo else config['tarifa_rapida']
                u_costo = st.number_input("Costo (COP) [Sugerido: kWh x Tarifa]", value=float(u_kwh * t_ap))
                
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

with pestanas[3]:
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
