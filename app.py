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
    [data-testid="stSidebar"] { background-color: rgba(10, 15, 10, 0.98); }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px; border-radius: 10px; border-top: 4px solid #2e7d32;
    }
    h1, h2, h3, h4, span, p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DESDE GOOGLE SHEETS
@st.cache_data(ttl=300) # Actualiza cada 5 minutos
def get_sheets_data():
    # URL Base del documento (Modo exportar CSV)
    base_url = "https://docs.google.com/spreadsheets/d/1u7cckay0IJ60bfoKk2OZo-TjCvTbH9O1wKxNFdSKDCQ/export?format=csv"
    
    # GIDs específicos de tus pestañas
    gid_telemetria = "1044040871"
    gid_unidades = "882343299"
    
    # Descarga de hojas
    df_tel = pd.read_csv(f"{base_url}&gid={gid_telemetria}")
    df_con = pd.read_csv(f"{base_url}&gid={gid_unidades}")
    
    # Limpieza de nombres y formatos
    for d in [df_tel, df_con]:
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')
            d['KEY_TIEMPO'] = d['FECHA_DT'].dt.strftime('%Y-%m')

    # UNIÓN: Pegamos las dos hojas por Patente y Mes
    df = pd.merge(df_tel, df_con, on=["DOMINIO", "KEY_TIEMPO"], suffixes=('_tel', '_con'))
    return df

try:
    df_master = get_sheets_data()
except Exception as e:
    st.error(f"❌ Error al leer Google Sheets: {e}")
    st.info("Asegúrate de que el Google Sheet sea 'Público' o tenga el acceso compartido por enlace.")
    st.stop()

# 3. SIDEBAR Y FILTROS
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/logo_diemar4.png", width=200) # Cambié a URL por si no tenés el archivo local
    st.divider()
    meses_cruzados = sorted(df_master["KEY_TIEMPO"].unique().tolist())
    mes_sel = st.selectbox("📅 Período de Análisis", meses_cruzados)
    marcas = ["Todas"] + sorted(df_master["MARCA"].unique().tolist())
    marca_sel = st.selectbox("🏭 Filtrar Marca", marcas)

df_actual = df_master[df_master["KEY_TIEMPO"] == mes_sel]
idx_actual = meses_cruzados.index(mes_sel)
df_previo = df_master[df_master["KEY_TIEMPO"] == meses_cruzados[idx_actual-1]] if idx_actual > 0 else pd.DataFrame()

if marca_sel != "Todas":
    df_actual = df_actual[df_actual["MARCA"] == marca_sel]
    df_previo = df_previo[df_previo["MARCA"] == marca_sel]

# 4. DASHBOARD
st.title(f"🌿 Centro de Sustentabilidad — {mes_sel}")

if df_actual.empty:
    st.warning("No hay datos que coincidan para este período y marca.")
else:
    # MÉTRICAS
    c1, c2, c3, c4 = st.columns(4)
    
    co2_now = df_actual['Emisiones (KG CO2)'].sum()
    co2_prev = df_previo['Emisiones (KG CO2)'].sum() if not df_previo.empty else 0
    delta_co2 = ((co2_now - co2_prev) / co2_prev * 100) if co2_prev > 0 else 0
    
    c1.metric("CO₂ EMITIDO", f"{co2_now:,.0f} kg", delta=f"{delta_co2:.1f}%" if co2_prev > 0 else None, delta_color="inverse")
    
    kms = df_actual['DISTANCIA RECORRIDA TELEMETRIA'].sum()
    c2.metric("KM RECORRIDOS", f"{kms:,.0f} km")
    
    lts_ral = df_actual['Ralenti (Lts)'].sum()
    c3.metric("LTS EN RALENTÍ", f"{lts_ral:,.1f} L", delta="Reducible", delta_color="off")
    
    arboles = int(co2_now / 20)
    c4.metric("COMPENSACIÓN", f"{arboles} Árboles", help="Basado en 20kg CO2/año por árbol.")

    st.divider()

    # GRÁFICOS
    col_l, col_r = st.columns([1.5, 1])
    with col_l:
        st.subheader("📊 Emisiones por Patente")
        fig_bar = px.bar(df_actual.sort_values("Emisiones (KG CO2)", ascending=False), 
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         color_continuous_scale="Greens", template="plotly_dark")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.subheader("📉 CO₂ por Marca")
        fig_pie = px.pie(df_actual, values='Emisiones (KG CO2)', names='MARCA', hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("📋 Auditoría de Datos")
    st.dataframe(df_actual[['DOMINIO', 'MARCA', 'FECHA_DT', 'DISTANCIA RECORRIDA TELEMETRIA', 'Emisiones (KG CO2)']], use_container_width=True)

st.caption("Conectado a Google Sheets | Actualización automática activa")
