import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import io

# 1. CONFIGURACIÓN Y ESTÉTICA
st.set_page_config(page_title="Expreso Diemar - Carbon Tracker", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.9)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/IMG_3101.jpg"); 
        background-size: cover; background-attachment: fixed;
    }
    .stMetric { background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border-top: 4px solid #2e7d32; }
    h1, h2, h3, h4, span, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA INTELIGENTE
@st.cache_data(ttl=60) 
def get_sheets_data():
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR35NkYPtJrOrdYHLGUH7GIW93s5cPAqQ0zEk5fP1c3gvErwbUW7HJ2OeWBYaBVsYKVmCf0yhLvs6eG/pub?output=csv"
    gid_tel = "1044040871"
    gid_uni = "882343299"
    
    df_tel = pd.read_csv(f"{base_url}&gid={gid_tel}")
    df_uni = pd.read_csv(f"{base_url}&gid={gid_uni}")
    
    # --- BUSCADOR AUTOMÁTICO DE COLUMNAS ---
    def normalizar(df):
        df.columns = df.columns.str.strip().str.upper().str.replace('Í', 'I').str.replace('Á', 'A')
        mapeo = {}
        for col in df.columns:
            if "DOMINIO" in col: mapeo[col] = "DOMINIO"
            if "FECHA" in col: mapeo[col] = "FECHA"
            if "DISTANCIA" in col or "KM" in col: mapeo[col] = "KMS"
            if "EMISIONES" in col or "CO2" in col: mapeo[col] = "CO2"
            if "RALENTI" in col: mapeo[col] = "RALENTI"
            if "MARCA" in col: mapeo[col] = "MARCA"
        return df.rename(columns=mapeo)

    df_tel = normalizar(df_tel)
    df_uni = normalizar(df_uni)

    # Limpieza de Dominio y Mes
    for d in [df_tel, df_uni]:
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')
            d['MES'] = d['FECHA_DT'].dt.strftime('%Y-%m')

    # Unión por Dominio y Mes
    df = pd.merge(df_tel, df_uni, on=["DOMINIO", "MES"], suffixes=('', '_DROP'))
    return df.loc[:,~df.columns.str.contains('_DROP')]

try:
    df_master = get_sheets_data()
except Exception as e:
    st.error(f"Error al cargar: {e}"); st.stop()

# 3. FILTROS
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/logo_diemar4.png", width=200)
    meses = sorted(df_master["MES"].unique().tolist(), reverse=True)
    mes_sel = st.selectbox("📅 Período", meses)
    marcas = ["Todas"] + sorted(df_master["MARCA"].unique().tolist())
    marca_sel = st.selectbox("🏭 Marca", marcas)

df_filtrado = df_master[df_master["MES"] == mes_sel]
if marca_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["MARCA"] == marca_sel]

# 4. DASHBOARD
st.title(f"🌿 Reporte Operativo — {mes_sel}")

if not df_filtrado.empty:
    c1, c2, c3, c4 = st.columns(4)
    
    # Usamos los nombres normalizados (KMS, CO2, RALENTI)
    v_co2 = df_filtrado['CO2'].sum() if 'CO2' in df_filtrado.columns else 0
    v_kms = df_filtrado['KMS'].sum() if 'KMS' in df_filtrado.columns else 0
    v_ral = df_filtrado['RALENTI'].sum() if 'RALENTI' in df_filtrado.columns else 0
    
    c1.metric("CO₂ TOTAL", f"{v_co2:,.0f} kg")
    c2.metric("KM TOTALES", f"{v_kms:,.0f} km")
    c3.metric("INTENSIDAD", f"{(v_co2/v_kms*1000) if v_kms > 0 else 0:.1f} g/km")
    c4.metric("RALENTÍ", f"{v_ral:,.0f} L")

    st.divider()
    
    col_a, col_b = st.columns([1.5, 1])
    with col_a:
        st.subheader("📊 Emisiones por Patente")
        st.bar_chart(df_filtrado.set_index("DOMINIO")["CO2"])
    with col_b:
        st.subheader("📉 Distribución por Marca")
        fig = px.pie(df_filtrado, values='CO2', names='MARCA', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Detalle de Unidades")
    st.dataframe(df_filtrado[['DOMINIO', 'MARCA', 'FECHA', 'KMS', 'CO2', 'RALENTI']], use_container_width=True)
else:
    st.warning("No hay datos para este mes.")

st.caption("Sincronización automática activa con Google Sheets.")
