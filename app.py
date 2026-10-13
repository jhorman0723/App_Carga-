import streamlit as st
import datetime
import pandas as pd
import sqlite3

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="BYD Yuan Up | Smart Charge",
    page_icon="⚡",
    layout="centered"
)

# --- BASE DE DATOS SQLITE ---
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
    cursor.execute("PRAGMA table_info(cargas);")
    columnas = [col[1] for col in cursor.fetchall()]
    if "tipo_carga" not in columnas:
        cursor.execute("ALTER TABLE cargas ADD COLUMN tipo_carga TEXT DEFAULT 'Carga Lenta (AC)'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            capacidad_bateria REAL,
            amperaje REAL,
            voltaje REAL,
            eficiencia REAL,
            consumo_100km REAL,
            tarifa_lenta REAL,
            tarifa_rapida REAL
        )
    """)
    cursor.execute("PRAGMA table_info(configuracion);")
    config_cols = [col[1] for col in cursor.fetchall()]
    if "rendimiento" in config_cols and "consumo_100km" not in config_cols:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN consumo_100km REAL DEFAULT 12.0")
    
    cursor.execute("""
        INSERT OR IGNORE INTO configuracion (id, capacidad_bateria, amperaje, voltaje, eficiencia, consumo_100km, tarifa_lenta, tarifa_rapida)
        VALUES (1, 45.1, 32, 125, 0.92, 12.0, 850.0, 1250.0)
    """)
    conn.commit()
    conn.close()

init_db()

def obtener_config():
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("SELECT capacidad_bateria, amperaje, voltaje, eficiencia, consumo_100km, tarifa_lenta, tarifa_rapida FROM configuracion WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    consumo_100 = row[4] if row[4] and row[4] > 0 else 12.0
    rendimiento_calculado = 100.0 / consumo_100
    return {
        "capacidad_bateria": row[0],
        "amperaje": row[1],
        "voltaje": row[2],
        "eficiencia": row[3],
        "consumo_100km": consumo_100,
        "rendimiento": rendimiento_calculado,
        "tarifa_lenta": row[5],
        "tarifa_rapida": row[6]
    }

def actualizar_config(cap, amp, volt, ef, consumo_100, t_lenta, t_rapida):
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE configuracion 
        SET capacidad_bateria=?, amperaje=?, voltaje=?, eficiencia=?, consumo_100km=?, tarifa_lenta=?, tarifa_rapida=?
        WHERE id=1
    """, (cap, amp, volt, ef, consumo_100, t_lenta, t_rapida))
    conn.commit()
    conn.close()

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

config = obtener_config()

# --- ENCABEZADO NATIVO Y LIMPIO ---
st.title("⚡ BYD Yuan Up")
st.caption("Gestor Inteligente de Carga y Consumo de Energía")

pestanas = st.tabs(["🧮 Calculadora", "📝 Registrar Carga", "📊 Historial y Métricas", "⚙️ Configuración"])

# TAB 1: CALCULADORA Y SIMULADOR
with pestanas[0]:
    st.subheader("Simulador de Carga")
    
    tipo_sim = st.radio("Tipo de Carga:", ["Carga Lenta (AC / Casa)", "Carga Rápida (DC / Estación)"], horizontal=True, key="tipo_s")
    tarifa_activa = config['tarifa_lenta'] if "Lenta" in tipo_sim else config['tarifa_rapida']
    potencia_kw = (config['amperaje'] * config['voltaje']) / 1000.0 if "Lenta" in tipo_sim else 40.0
    
    st.info(f"🔌 Potencia: **{potencia_kw:.2f} kW** | Tarifa: **${tarifa_activa:,.0f} / kWh**")

    soc_inicial_sim = st.slider("🔋 Estado de Batería Actual (SOC Inicial)", 0, 99, 20, 5, key="c7") / 100.0
    modo = st.selectbox("🎯 ¿Qué deseas calcular?", ["Porcentaje Objetivo (%)", "Tiempo Disponible (Horas)", "Kilómetros Deseados (km)"], key="c8")

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
        horas_disp = st.number_input("Horas disponibles para cargar", 0.5, 24.0, 4.0, 0.5, key="c10")
        energia_req = horas_disp * potencia_kw * config['eficiencia']
        soc_ganado = energia_req / config['capacidad_bateria']
        soc_final = min(1.0, soc_inicial_sim + soc_ganado)
        tiempo_horas = horas_disp
        km_ganados = energia_req * config['rendimiento']
        costo_total = energia_req * tarifa_activa

    elif modo == "Kilómetros Deseados (km)":
        km_deseados = st.number_input("Kilómetros que necesitas recargar", 10, 400, 150, 10, key="c11")
        energia_req = km_deseados / config['rendimiento']
        tiempo_horas = energia_req / (potencia_kw * config['eficiencia'])
        soc_ganado = energia_req / config['capacidad_bateria']
        soc_final = min(1.0, soc_inicial_sim + soc_ganado)
        km_ganados = km_deseados
        costo_total = energia_req * tarifa_activa

    st.write(f"**Progreso Estimado:** {int(soc_inicial_sim*100)}% ➡️ **{int(soc_final*100)}%**")
    st.progress(float(soc_final))

    st.markdown("---")
    
    # Métricas nativas de Streamlit con legibilidad perfecta
    m1, m2 = st.columns(2)
    m1.metric("⏱️ Tiempo Estimado", f"{int(tiempo_horas)}h {int((tiempo_horas%1)*60)}m")
    m2.metric("⚡ Energía Requerida", f"{energia_req:.1f} kWh")

    m3, m4 = st.columns(2)
    m3.metric("🚗 Autonomía Ganada", f"+{km_ganados:.0f} km")
    m4.metric("💰 Costo Estimado", f"${costo_total:,.0f} COP")

# TAB 2: REGISTRAR Y EDITAR CARGAS
with pestanas[1]:
    st.subheader("Registro de Sesiones de Carga")
    accion = st.radio("Acción:", ["➕ Registrar Nueva Carga", "✏️ Editar Registro", "🗑️ Eliminar Registro"], horizontal=True)
    
    if accion == "➕ Registrar Nueva Carga":
        with st.container(border=True):
            f_fecha = st.date_input("Fecha de la carga", value=datetime.date.today())
            f_tipo = st.selectbox("Tipo de Carga", ["Carga Lenta (AC)", "Carga Rápida (DC)"])
            
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                f_soc_i = st.slider("SOC Inicial (%)", 0, 99, 20, 1, key="reg_soci")
            with col_r2:
                f_soc_f = st.slider("SOC Final (%)", 1, 100, 80, 1, key="reg_socf")
                
            f_kwh = st.number_input("Energía Entregada (kWh)", value=35.0, step=0.1, key="reg_kwh")
            f_tiempo = st.number_input("Tiempo de Carga (Horas)", value=8.5, step=0.1, key="reg_tiempo")
            
            tarifa_aplicada = config['tarifa_lenta'] if "Lenta" in f_tipo else config['tarifa_rapida']
            costo_dinamico = f_kwh * tarifa_aplicada
            
            st.metric("💳 Costo Calculado Automáticamente", f"${costo_dinamico:,.0f} COP", help=f"{f_kwh} kWh x ${tarifa_aplicada:,.0f}/kWh")
            
            f_temp = st.number_input("Temperatura Máxima Dispositivo (°C)", value=51.5, step=0.5, key="reg_temp")
            
            if st.button("💾 Guardar Carga en Base de Datos", type="primary", use_container_width=True):
                estado_t = "Normal" if f_temp <= 55 else "Revisar Calor"
                guardar_carga(str(f_fecha), f_tipo, f_soc_i, f_soc_f, f_kwh, f_tiempo, costo_dinamico, f_temp, estado_t)
                st.success("¡Carga guardada exitosamente!")

    elif accion == "✏️ Editar Registro":
        df_edit = cargar_historial()
        if not df_edit.empty:
            id_sel = st.selectbox("Selecciona el ID a editar:", df_edit['id'].tolist())
            row_data = df_edit[df_edit['id'] == id_sel].iloc[0]
            
            with st.form("form_update"):
                u_fecha = st.date_input("Fecha", value=datetime.datetime.strptime(row_data['fecha'], "%Y-%m-%d").date())
                u_tipo = st.selectbox("Tipo de Carga", ["Carga Lenta (AC)", "Carga Rápida (DC)"], index=0 if "Lenta" in str(row_data['tipo_carga']) else 1)
                u_soc_i = st.slider("SOC Inicial (%)", 0, 99, int(row_data['soc_inicial']))
                u_soc_f = st.slider("SOC Final (%)", 1, 100, int(row_data['soc_final']))
                u_kwh = st.number_input("Energía (kWh)", value=float(row_data['energia_kwh']))
                u_tiempo = st.number_input("Tiempo (Horas)", value=float(row_data['tiempo_horas']))
                
                t_ap = config['tarifa_lenta'] if "Lenta" in u_tipo else config['tarifa_rapida']
                u_costo = st.number_input("Costo (COP)", value=float(u_kwh * t_ap))
                u_temp = st.number_input("Temperatura (°C)", value=float(row_data['temperatura']))
                
                if st.form_submit_button("🔄 Actualizar Registro", type="primary", use_container_width=True):
                    estado_t = "Normal" if u_temp <= 55 else "Revisar Calor"
                    actualizar_carga(id_sel, str(u_fecha), u_tipo, u_soc_i, u_soc_f, u_kwh, u_tiempo, u_costo, u_temp, estado_t)
                    st.success(f"¡Registro #{id_sel} actualizado correctamente!")
        else:
            st.info("No hay registros disponibles.")

    elif accion == "🗑️ Eliminar Registro":
        df_del = cargar_historial()
        if not df_del.empty:
            id_del = st.selectbox("Selecciona el ID a eliminar:", df_del['id'].tolist())
            if st.button("⚠️ Confirmar Borrado", type="primary", use_container_width=True):
                eliminar_carga(id_del)
                st.success(f"¡Registro #{id_del} eliminado con éxito!")
                st.rerun()

# TAB 3: HISTORIAL Y GRÁFICOS
with pestanas[2]:
    st.subheader("Historial de Cargas y Consumos")
    df_graf = cargar_historial()
    
    if not df_graf.empty:
        total_kwh = df_graf['energia_kwh'].sum()
        total_costo = df_graf['costo_cop'].sum()
        
        c_kwh, c_cop = st.columns(2)
        c_kwh.metric("Energía Acumulada", f"{total_kwh:.1f} kWh")
        c_cop.metric("Gasto Total Acumulado", f"${total_costo:,.0f} COP")
        
        st.markdown("---")
        st.subheader("Tabla de Registros")
        st.dataframe(df_graf, use_container_width=True)
        
        df_graf['fecha'] = pd.to_datetime(df_graf['fecha'])
        df_graf = df_graf.sort_values('fecha')
        
        st.subheader("⚡ Consumo de Energía por Carga (kWh)")
        st.line_chart(df_graf.set_index('fecha')['energia_kwh'])
        
        st.subheader("💰 Costo por Carga ($ COP)")
        st.bar_chart(df_graf.set_index('fecha')['costo_cop'])
    else:
        st.info("Aún no hay historial de cargas registrado.")

# TAB 4: AJUSTES Y CONFIGURACIÓN
with pestanas[3]:
    st.subheader("Configuración y Tarifas en Base de Datos")
    with st.form("form_config"):
        new_cap = st.number_input("Capacidad Batería (kWh)", value=float(config['capacidad_bateria']), step=0.1)
        new_amp = st.number_input("Amperaje Lento Feyree (A)", value=float(config['amperaje']), step=1.0)
        new_volt = st.number_input("Voltaje Promedio (V)", value=float(config['voltaje']), step=1.0)
        new_ef = st.slider("Eficiencia de Carga (%)", 80, 100, int(config['eficiencia'] * 100)) / 100.0
        
        new_consumo_100 = st.number_input("Consumo Estándar (kWh por cada 100 km)", value=float(config['consumo_100km']), step=0.1)
        rend_auto = 100.0 / new_consumo_100 if new_consumo_100 > 0 else 8.33
        st.caption(f"Rendimiento equivalente calculado: **{rend_auto:.2f} km/kWh**")
        
        st.markdown("---")
        new_tlenta = st.number_input("Tarifa Carga Lenta ($/kWh - Casa)", value=float(config['tarifa_lenta']), step=10.0)
        new_trapida = st.number_input("Tarifa Carga Rápida ($/kWh - Estación)", value=float(config['tarifa_rapida']), step=10.0)
        
        if st.form_submit_button("💾 Guardar Configuración", type="primary", use_container_width=True):
            actualizar_config(new_cap, new_amp, new_volt, new_ef, new_consumo_100, new_tlenta, new_trapida)
            st.success("¡Configuración actualizada en la base de datos!")
