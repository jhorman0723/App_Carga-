import streamlit as st
import datetime
import pandas as pd
import sqlite3
import io

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
    cursor.execute("PRAGMA table_info(cargas);")
    columnas = [col[1] for col in cursor.fetchall()]
    if "tipo_carga" not in columnas:
        cursor.execute("ALTER TABLE cargas ADD COLUMN tipo_carga TEXT DEFAULT 'Carga Lenta (AC)'")

    # Tabla de configuración global con potencias personalizadas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            capacidad_bateria REAL,
            amperaje REAL,
            voltaje REAL,
            eficiencia REAL,
            consumo_100km REAL,
            tarifa_lenta REAL,
            tarifa_rapida REAL,
            autonomia_100_actual REAL,
            precio_galon_gasolina REAL,
            costo_cargador_feyree REAL,
            potencia_lenta_kw REAL,
            potencia_rapida_kw REAL
        )
    """)
    cursor.execute("PRAGMA table_info(configuracion);")
    config_cols = [col[1] for col in cursor.fetchall()]
    
    if "autonomia_100_actual" not in config_cols:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN autonomia_100_actual REAL DEFAULT 380.0")
    if "rendimiento" in config_cols and "consumo_100km" not in config_cols:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN consumo_100km REAL DEFAULT 12.0")
    if "precio_galon_gasolina" not in config_cols:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN precio_galon_gasolina REAL DEFAULT 15500.0")
    if "costo_cargador_feyree" not in config_cols:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN costo_cargador_feyree REAL DEFAULT 1200000.0")
    if "potencia_lenta_kw" not in config_cols:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN potencia_lenta_kw REAL DEFAULT 4.0")
    if "potencia_rapida_kw" not in config_cols:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN potencia_rapida_kw REAL DEFAULT 40.0")
    
    cursor.execute("""
        INSERT OR IGNORE INTO configuracion (
            id, capacidad_bateria, amperaje, voltaje, eficiencia, consumo_100km, 
            tarifa_lenta, tarifa_rapida, autonomia_100_actual, precio_galon_gasolina, 
            costo_cargador_feyree, potencia_lenta_kw, potencia_rapida_kw
        )
        VALUES (1, 45.1, 32, 125, 0.92, 12.0, 850.0, 1250.0, 380.0, 15500.0, 1200000.0, 4.0, 40.0)
    """)
    conn.commit()
    conn.close()

init_db()

def obtener_config():
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT capacidad_bateria, amperaje, voltaje, eficiencia, consumo_100km, 
               tarifa_lenta, tarifa_rapida, autonomia_100_actual, precio_galon_gasolina, 
               costo_cargador_feyree, potencia_lenta_kw, potencia_rapida_kw 
        FROM configuracion WHERE id=1
    """)
    row = cursor.fetchone()
    conn.close()
    
    consumo_100 = row[4] if row[4] and row[4] > 0 else 12.0
    rendimiento_calculado = 100.0 / consumo_100
    auto_100 = row[7] if row[7] else 380.0
    p_gas = row[8] if row[8] else 15500.0
    c_feyree = row[9] if row[9] else 1200000.0
    p_lenta = row[10] if row[10] else 4.0
    p_rapida = row[11] if row[11] else 40.0
    
    return {
        "capacidad_bateria": row[0],
        "amperaje": row[1],
        "voltaje": row[2],
        "eficiencia": row[3],
        "consumo_100km": consumo_100,
        "rendimiento": rendimiento_calculado,
        "tarifa_lenta": row[5],
        "tarifa_rapida": row[6],
        "autonomia_100_actual": auto_100,
        "precio_galon_gasolina": p_gas,
        "costo_cargador_feyree": c_feyree,
        "potencia_lenta_kw": p_lenta,
        "potencia_rapida_kw": p_rapida
    }

def actualizar_config(cap, amp, volt, ef, consumo_100, t_lenta, t_rapida, auto_100, p_gas, c_feyree, p_lenta, p_rapida):
    conn = sqlite3.connect("cargas_byd.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE configuracion 
        SET capacidad_bateria=?, amperaje=?, voltaje=?, eficiencia=?, consumo_100km=?, 
            tarifa_lenta=?, tarifa_rapida=?, autonomia_100_actual=?, precio_galon_gasolina=?, 
            costo_cargador_feyree=?, potencia_lenta_kw=?, potencia_rapida_kw=?
        WHERE id=1
    """, (cap, amp, volt, ef, consumo_100, t_lenta, t_rapida, auto_100, p_gas, c_feyree, p_lenta, p_rapida))
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
    df = pd.read_sql_query("SELECT * FROM cargas ORDER BY fecha ASC, id ASC", conn)
    conn.close()
    
    if not df.empty:
        df['fecha_dt'] = pd.to_datetime(df['fecha'])
        df['dias_desde_anterior'] = df['fecha_dt'].diff().dt.days
        df['dias_desde_anterior'] = df['dias_desde_anterior'].apply(lambda x: f"{int(x)} días" if pd.notnull(x) else "Primera carga")
        df = df.sort_values(by=['fecha_dt', 'id'], ascending=[False, False])
        df = df.drop(columns=['fecha_dt'])
        
    return df

config = obtener_config()

# --- ENCABEZADO PRINCIPAL ---
st.title("⚡ BYD Yuan Up")
st.caption("Gestor Inteligente de Carga, Consumo y Salud de Batería")

pestanas = st.tabs(["🧮 Calculadora", "📝 Registrar Carga", "📊 Historial & Métricas", "💰 Ahorro & ROI", "🔋 Salud SOH", "📂 Reportes", "⚙️ Ajustes"])

# TAB 1: CALCULADORA Y SIMULADOR
with pestanas[0]:
    st.subheader("Simulador de Carga")
    
    tipo_sim = st.radio("Tipo de Carga:", ["Carga Lenta (AC / Casa)", "Carga Rápida (DC / Estación)"], horizontal=True, key="tipo_s")
    
    if "Lenta" in tipo_sim:
        tarifa_activa = config['tarifa_lenta']
        potencia_kw = config['potencia_lenta_kw']
        modo_texto = "AC (Lenta)"
    else:
        tarifa_activa = config['tarifa_rapida']
        potencia_kw = config['potencia_rapida_kw']
        modo_texto = "DC (Rápida)"
    
    st.info(f"🔌 Modo: **{modo_texto}** | Potencia Configurada: **{potencia_kw:.2f} kW** | Tarifa: **${tarifa_activa:,.0f} / kWh**")

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

# TAB 3: HISTORIAL, FRECUENCIA Y GRÁFICOS AVANZADOS
with pestanas[2]:
    st.subheader("📊 Historial, Frecuencia y Diagnóstico Térmico")
    df_graf = cargar_historial()
    
    if not df_graf.empty:
        total_kwh = df_graf['energia_kwh'].sum()
        total_costo = df_graf['costo_cop'].sum()
        prom_temp = df_graf['temperatura'].mean()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Energía Acumulada", f"{total_kwh:.1f} kWh")
        c2.metric("Gasto Acumulado", f"${total_costo:,.0f} COP")
        c3.metric("Temp. Prom. Feyree", f"{prom_temp:.1f} °C")
        
        st.markdown("---")
        st.subheader("📋 Tabla de Registros y Frecuencia de Carga")
        st.dataframe(df_graf, use_container_width=True)
        
        df_chart = df_graf.copy()
        df_chart['fecha_dt'] = pd.to_datetime(df_chart['fecha'])
        df_chart = df_chart.sort_values('fecha_dt')
        
        st.markdown("---")
        st.subheader("⚡ Consumo de Energía (kWh) y Costo ($ COP)")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.caption("Energía Inyectada por Carga (kWh)")
            st.line_chart(df_chart.set_index('fecha_dt')['energia_kwh'])
        with col_g2:
            st.caption("Costo por Carga ($ COP)")
            st.bar_chart(df_chart.set_index('fecha_dt')['costo_cop'])
            
        st.markdown("---")
        st.subheader("🌡️ Control Térmico del Dispositivo Feyree (°C)")
        st.caption("Supervisión de temperatura máxima de operación (Límite recomendado: 55°C)")
        st.line_chart(df_chart.set_index('fecha_dt')['temperatura'])
        
        st.markdown("---")
        st.subheader("🔋 Ventana de Carga (SOC Inicial vs. SOC Final)")
        st.caption("Seguimiento del rango de batería cargado en cada sesión")
        st.bar_chart(df_chart.set_index('fecha_dt')[['soc_inicial', 'soc_final']])

    else:
        st.info("Aún no hay historial de cargas registrado para generar gráficos.")

# TAB 4: MÓDULO DE ROI Y AHORRO FINANCIERO
with pestanas[3]:
    st.subheader("💰 Ahorro Financiero y ROI vs. Gasolina")
    df_roi = cargar_historial()
    
    if not df_roi.empty:
        total_kwh_ingresados = df_roi['energia_kwh'].sum()
        total_gasto_electrico = df_roi['costo_cop'].sum()
        
        km_equivalentes = total_kwh_ingresados * config['rendimiento']
        galones_gasolina_equiv = km_equivalentes / 40.0
        precio_galon = config['precio_galon_gasolina']
        costo_gasolina_equiv = galones_gasolina_equiv * precio_galon
        
        ahorro_neto = costo_gasolina_equiv - total_gasto_electrico
        costo_km_elec = total_gasto_electrico / km_equivalentes if km_equivalentes > 0 else 0
        costo_km_gas = costo_gasolina_equiv / km_equivalentes if km_equivalentes > 0 else 0
        
        costo_feyree = config['costo_cargador_feyree']
        pct_amortizado = (ahorro_neto / costo_feyree * 100.0) if costo_feyree > 0 else 0
        
        st.write("### 🍃 Balance de Ahorro Acumulado")
        r1, r2 = st.columns(2)
        r1.metric("💵 Ahorro Neto Estimado", f"${ahorro_neto:,.0f} COP")
        r2.metric("⛽ Gasto Gasolina Equiv.", f"${costo_gasolina_equiv:,.0f} COP")
        
        st.markdown("---")
        st.write("### 🚗 Comparativa Costo por Kilómetro Recorrido")
        ck1, ck2 = st.columns(2)
        ck1.metric("⚡ BYD Yuan Up", f"${costo_km_elec:,.1f} COP / km")
        ck2.metric("⛽ Carro a Gasolina", f"${costo_km_gas:,.1f} COP / km", delta=f"-${costo_km_gas - costo_km_elec:,.1f} COP / km", delta_color="normal")
        
        st.markdown("---")
        st.write("### 🔌 Amortización del Cargador Feyree")
        st.write(f"**Progreso de Pago del Cargador:** {min(100.0, pct_amortizado):.1f}% completado")
        st.progress(min(1.0, max(0.0, pct_amortizado / 100.0)))
        
        if pct_amortizado >= 100:
            st.success("🎉 ¡Tu cargador Feyree ya se pagó por completo solo con el ahorro en combustible!")
        else:
            saldo_pendiente = costo_feyree - ahorro_neto
            st.info(f"Falta un ahorro de **${saldo_pendiente:,.0f} COP** para recuperar la inversión inicial del cargador.")
    else:
        st.info("Registra sesiones de carga para calcular tu ahorro financiero frente a la gasolina.")

# TAB 5: MÓDULO SOH DE BATERÍA
with pestanas[4]:
    st.subheader("🔋 Diagnóstico y Salud de Batería (SOH)")
    df_soh = cargar_historial()
    
    if not df_soh.empty:
        kwh_ac = df_soh[df_soh['tipo_carga'].str.contains('Lenta', na=False)]['energia_kwh'].sum()
        kwh_dc = df_soh[df_soh['tipo_carga'].str.contains('Rápida', na=False)]['energia_kwh'].sum()
        total_soh_kwh = kwh_ac + kwh_dc
        
        pct_ac = (kwh_ac / total_soh_kwh * 100) if total_soh_kwh > 0 else 100.0
        pct_dc = (kwh_dc / total_soh_kwh * 100) if total_soh_kwh > 0 else 0.0
        
        st.write("### ⚖️ Proporción de Carga AC (Lenta) vs. DC (Rápida)")
        c_ac, c_dc = st.columns(2)
        c_ac.metric("Carga Lenta (AC)", f"{pct_ac:.1f}%", f"{kwh_ac:.1f} kWh")
        c_dc.metric("Carga Rápida (DC)", f"{pct_dc:.1f}%", f"{kwh_dc:.1f} kWh")
        
        if pct_ac >= 80:
            st.success("🟢 **Perfil Óptimo (80% AC / 20% DC):** Tu hábito de carga es ideal para prolongar la vida útil.")
        elif pct_ac >= 60:
            st.warning("🟡 **Perfil Aceptable:** Intenta priorizar cargas lentas en casa.")
        else:
            st.error("🔴 **Alerta:** Exceso de cargas rápidas DC.")
    else:
        st.info("Registra tus primeras cargas para calcular la proporción AC/DC.")

    st.markdown("---")
    st.write("### 📉 Estado de Capacidad Estimado (SOH)")
    auto_fabrica = 380.0
    auto_actual = float(config.get('autonomia_100_actual', 380.0))
    soh_estimado = (auto_actual / auto_fabrica) * 100.0
    
    m_soh1, m_soh2 = st.columns(2)
    m_soh1.metric("SOH Estimado", f"{soh_estimado:.1f}%")
    m_soh2.metric("Autonomía 100% Registrada", f"{auto_actual:.0f} km")
    st.progress(min(1.0, max(0.0, soh_estimado / 100.0)))

# TAB 6: MÓDULO DE EXPORTACIÓN Y REPORTES
with pestanas[5]:
    st.subheader("📂 Exportación de Reportes e Informes")
    df_exp = cargar_historial()
    
    if not df_exp.empty:
        csv_buffer = df_exp.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📄 Descargar Historial en Formato CSV",
            data=csv_buffer,
            file_name=f"historial_cargas_BYD_{datetime.date.today()}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df_exp.to_excel(writer, sheet_name='Historial Cargas', index=False)
            resumen_data = {
                "Métrica": ["Energía Total (kWh)", "Gasto Total (COP)", "Promedio Temp (°C)", "Total Cargas"],
                "Valor": [df_exp['energia_kwh'].sum(), df_exp['costo_cop'].sum(), df_exp['temperatura'].mean(), len(df_exp)]
            }
            pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen Métricas', index=False)
            
        excel_data = output_excel.getvalue()
        st.download_button(
            label="📊 Descargar Informe Completo en Excel (.xlsx)",
            data=excel_data,
            file_name=f"informe_cargas_BYD_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
    else:
        st.warning("No hay datos guardados para exportar.")

# TAB 7: AJUSTES Y CONFIGURACIÓN
with pestanas[6]:
    st.subheader("Configuración y Potencias en Base de Datos")
    with st.form("form_config"):
        new_cap = st.number_input("Capacidad Batería (kWh)", value=float(config['capacidad_bateria']), step=0.1)
        new_amp = st.number_input("Amperaje Lento Referencia (A)", value=float(config['amperaje']), step=1.0)
        new_volt = st.number_input("Voltaje Promedio (V)", value=float(config['voltaje']), step=1.0)
        new_ef = st.slider("Eficiencia de Carga (%)", 80, 100, int(config['eficiencia'] * 100)) / 100.0
        
        st.markdown("---")
        st.subheader("⚡ Potencias de Carga (kW)")
        new_pot_lenta = st.number_input("Potencia Carga Lenta - AC (kW) [Ej. Feyree ~4 kW]", value=float(config.get('potencia_lenta_kw', 4.0)), step=0.1)
        new_pot_rapida = st.number_input("Potencia Carga Rápida - DC (kW) [Ej. Estación pública]", value=float(config.get('potencia_rapida_kw', 40.0)), step=1.0)
        
        new_consumo_100 = st.number_input("Consumo Estándar (kWh por cada 100 km)", value=float(config['consumo_100km']), step=0.1)
        rend_auto = 100.0 / new_consumo_100 if new_consumo_100 > 0 else 8.33
        st.caption(f"Rendimiento equivalente calculated: **{rend_auto:.2f} km/kWh**")
        
        st.markdown("---")
        new_auto_100 = st.number_input("Autonomía actual estimada al 100% (km en pantalla)", value=float(config.get('autonomia_100_actual', 380.0)), step=1.0)
        
        st.markdown("---")
        st.subheader("Parámetros Financieros (ROI y Gasolina)")
        new_p_gas = st.number_input("Precio Galón de Gasolina ($ COP)", value=float(config.get('precio_galon_gasolina', 15500.0)), step=100.0)
        new_c_feyree = st.number_input("Inversión Cargador Feyree ($ COP)", value=float(config.get('costo_cargador_feyree', 1200000.0)), step=50000.0)
        
        st.markdown("---")
        new_tlenta = st.number_input("Tarifa Carga Lenta ($/kWh - Casa)", value=float(config['tarifa_lenta']), step=10.0)
        new_trapida = st.number_input("Tarifa Carga Rápida ($/kWh - Estación)", value=float(config['tarifa_rapida']), step=10.0)
        
        if st.form_submit_button("💾 Guardar Configuración", type="primary", use_container_width=True):
            actualizar_config(new_cap, new_amp, new_volt, new_ef, new_consumo_100, new_tlenta, new_trapida, new_auto_100, new_p_gas, new_c_feyree, new_pot_lenta, new_pot_rapida)
            st.success("¡Configuración y potencias actualizadas en la base de datos!")
