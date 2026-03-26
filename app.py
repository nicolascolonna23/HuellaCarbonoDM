import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# 1. CONFIGURACIÓN Y ESTÉTICA DARK
st.set_page_config(
    page_title="Expreso Diemar - Fleet Analytics",
    page_icon="🚛",
    layout="wide",
)

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/IMG_3101.jpg"); 
        background-size: cover;
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] {
        background-color: rgba(15, 15, 15, 0.95);
    }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    h1, h2, h3, h4, span, p {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA Y CRUCE FLEXIBLE
@st.cache_data(ttl=600)
def get_data():
    u1 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQCCJG7r9T2JTb0eAdpQU1ggAcTn9ZELfjq58Xk9-eqj58o?download=1"
    u2 = "https://expresodiemar-my.sharepoint.com/:x:/g/personal/nicolascolonna_expresodiemar_onmicrosoft_com/IQAWlrsay0HVT622_ANLB-bWAfMlRi4IHHFMH6DJBzVW3BU?download=1"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    def download(url):
        r = requests.get(url, headers=headers)
        return pd.read_excel(io.BytesIO(r.content))

    df_tel = download(u1)
    df_con = download(u2)
    
    # Limpieza de Dominios y Nombres
    for d in [df_tel, df_con]:
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')

    # UNIÓN FLEXIBLE: Primero por Dominio
    # Usamos "how='inner'" para quedarnos solo con lo que está en ambos archivos
    df = pd.merge(df_tel, df_con, on="DOMINIO", suffixes=('_tel', '_con'))
    
    # Filtro de Año 2026 sobre el resultado
    if not df.empty and 'FECHA_DT_tel' in df.columns:
        df = df[df['FECHA_DT_tel'].dt.year == 2026].copy()

    if not df.empty:
        # Cálculo de CO2
        dist = df['DISTANCIA RECORRIDA TELEMETRIA']
        emi = df['Emisiones (KG CO2)']
        df['g_co2_km'] = (emi / dist * 1000) if dist.sum() > 0 else 0
    
    return df

# Ejecutar carga
try:
    df_full = get_data()
except Exception as e:
    st.error(f"❌ Error crítico: {e}")
    st.stop()

# 3. SIDEBAR
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    st.divider()
    portal = st.radio("Sección:", ["📊 Desempeño de Flota", "🌿 Portal de Emisiones CO2"])
    
    st.divider()
    if not df_full.empty:
        marcas = ["Todas"] + sorted(df_full["MARCA"].dropna().unique().tolist())
        marca_sel = st.selectbox("🏭 Filtrar por Marca", marcas)
    else:
        marca_sel = "Todas"

# Filtrado dinámico
df = df_full.copy()
if marca_sel != "Todas":
    df = df[df["MARCA"] == marca_sel]

# 4. VISTAS
if df.empty:
    st.warning("⚠️ Sin datos coincidentes para 2026.")
    st.info("Esto sucede si las patentes del archivo de 19 filas no están presentes en el de 290 filas.")
else:
    if portal == "📊 Desempeño de Flota":
        st.title("🚛 Fleet Analytics 2026")
        c1, c2, c3 = st.columns(3)
        c1.metric("🛣️ Km Totales", f"{df['DISTANCIA RECORRIDA TELEMETRIA'].sum():,.0f}")
        c2.metric("📊 L/100km Prom.", f"{df['Consumo c/ 100km TELEMETRIA'].mean():.2f}")
        c3.metric("⛽ Litros Totales", f"{df['LITROS CONSUMIDOS'].sum():,.0f}")

        st.plotly_chart(px.scatter(df, x="DISTANCIA RECORRIDA TELEMETRIA", y="LITROS CONSUMIDOS", 
                                   color="DOMINIO", size="Ralenti (Lts)", hover_name="DOMINIO",
                                   template="plotly_dark"), use_container_width=True)

    elif portal == "🌿 Portal de Emisiones CO2":
        st.title("🌿 Sustentabilidad 2026")
        total_co2 = df['Emisiones (KG CO2)'].sum()
        st.metric("Huella de Carbono Total", f"{total_co2:,.0f} kg CO2")
        
        fig_co2 = px.bar(df.sort_values("Emisiones (KG CO2)", ascending=False),
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         template="plotly_dark", color_continuous_scale="Reds")
        st.plotly_chart(fig_co2, use_container_width=True)

# 5. FOOTER
st.divider()
st.caption(f"Registros procesados: {len(df)}")
