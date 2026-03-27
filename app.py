import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. ESTÉTICA "DARK LOGÍSTICA"
st.set_page_config(page_title="Expreso Diemar - Flota Pro", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetricValue"] { color: #2e7d32 !important; font-weight: bold; }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DE DATOS (TTL bajado a 60 segundos para actualización rápida)
@st.cache_data(ttl=60)
def get_all_data():
    base_url = "https://docs.google.com/spreadsheets/d/1u7cckay0IJ60bfoKk2OZo-TjCvTbH9O1wKxNFdSKDCQ/export?format=csv"
    gid_tel = "1044040871" # Pestaña Telemetría
    gid_uni = "882343299"  # Pestaña Datos Unidades
    
    df_tel = pd.read_csv(f"{base_url}&gid={gid_tel}")
    df_uni = pd.read_csv(f"{base_url}&gid={gid_uni}")
    
    # Limpieza de nombres y fechas
    for d in [df_tel, df_uni]:
        d.columns = d.columns.str.strip().str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')
            d['MES_AÑO'] = d['FECHA_DT'].dt.strftime('%b %Y') # Ej: Jan 2026
            d['ORDEN_MES'] = d['FECHA_DT'].dt.to_period('M')

    # Unión por Dominio y Mes/Año
    df = pd.merge(df_tel, df_uni, on=["DOMINIO", "MES_AÑO"], suffixes=('', '_DROP'))
    return df.loc[:,~df.columns.str.contains('_DROP')]

try:
    df_raw = get_all_data()
except Exception as e:
    st.error(f"Error: {e}"); st.stop()

# 3. SIDEBAR: FILTROS DINÁMICOS
with st.sidebar:
    st.title("🚛 Panel de Control")
    # Filtro de Mes
    lista_meses = sorted(df_raw['MES_AÑO'].unique(), reverse=True)
    mes_sel = st.selectbox("Seleccionar Mes", lista_meses)
    
    # Filtro de Marca
    marcas = ["Todas"] + sorted(df_raw['MARCA'].unique().tolist())
    marca_sel = st.selectbox("Marca de Camión", marcas)

# Filtrado de datos
df_filtrado = df_raw[df_raw['MES_AÑO'] == mes_sel]
if marca_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado['MARCA'] == marca_sel]

# 4. DASHBOARD: MÉTRICAS DE IMPACTO
st.title(f"📊 Reporte de Operación — {mes_sel}")

# Cálculos rápidos
kms_tot = df_filtrado['DISTANCIA RECORRIDA TELEMETRIA'].sum()
co2_tot = df_filtrado['EMISIONES (KG CO2)'].sum()
lts_ral = df_filtrado['RALENTI (LTS)'].sum()
# Supongamos un costo de combustible promedio (puedes ajustarlo)
costo_estimado = (co2_tot / 2.68) * 1250 # 1L Diesel approx 2.68kg CO2

c1, c2, c3, c4 = st.columns(4)
c1.metric("Kms Recorridos", f"{kms_tot:,.0f} km")
c2.metric("CO₂ Emitido", f"{co2_tot:,.0f} kg")
c3.metric("Lts en Ralentí", f"{lts_ral:,.0f} L")
c4.metric("Gasto Comb. Est.", f"$ {costo_estimado:,.0f}")

st.divider()

# 5. ANÁLISIS POR UNIDAD
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("🌲 Compensación Ambiental")
    arboles = int(co2_tot / 20)
    st.info(f"Para compensar este mes se necesitan **{arboles} árboles** creciendo por un año.")
    
    # Gráfico de barras de emisiones por patente
    fig_emisiones = px.bar(df_filtrado, x='DOMINIO', y='EMISIONES (KG CO2)', 
                           color='EMISIONES (KG CO2)', color_continuous_scale='Greens',
                           template="plotly_dark", title="Ranking de Huella por Patente")
    st.plotly_chart(fig_emisiones, use_container_width=True)

with col_b:
    st.subheader("📉 Eficiencia de Ralentí")
    # Gráfico de dispersión: Distancia vs Ralentí
    fig_scatter = px.scatter(df_filtrado, x='DISTANCIA RECORRIDA TELEMETRIA', y='RALENTI (LTS)',
                             hover_name='DOMINIO', size='EMISIONES (KG CO2)', color='MARCA',
                             template="plotly_dark", title="Distancia vs Ralentí (Tamaño = CO2)")
    st.plotly_chart(fig_scatter, use_container_width=True)

# 6. TABLA DETALLADA
st.subheader("📋 Auditoría de Unidades")
st.dataframe(df_filtrado[['DOMINIO', 'MARCA', 'FECHA', 'DISTANCIA RECORRIDA TELEMETRIA', 'EMISIONES (KG CO2)', 'RALENTI (LTS)']], 
             use_container_width=True)

st.caption("Los datos se sincronizan con Google Sheets cada 60 segundos.")
