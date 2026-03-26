import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import io

# 1. CONFIGURACIÓN Y ESTÉTICA "ECO-DARK"
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

# 2. CARGA DE DATOS
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
    
    for d in [df_tel, df_con]:
        d.columns = d.columns.str.strip().str.replace('í', 'i').str.replace('á', 'a')
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')
            d['MES_VAL'] = d['FECHA_DT'].dt.to_period('M')

    df = pd.merge(df_tel, df_con, on="DOMINIO", suffixes=('_tel', '_con'))
    return df

try:
    df_full = get_data()
except Exception as e:
    st.error(f"❌ Error: {e}"); st.stop()

# 3. SIDEBAR
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    st.title("🌿 Carbon Control")
    st.divider()
    meses_disponibles = sorted(df_full["MES_VAL_tel"].unique().tolist())
    mes_sel = st.selectbox("📅 Seleccionar Mes de Análisis", meses_disponibles)
    marca_sel = st.selectbox("🏭 Marca", ["Todas"] + sorted(df_full["MARCA"].unique().tolist()))

# 4. LÓGICA DE COMPARACIÓN (MES ACTUAL VS ANTERIOR)
mes_actual = df_full[df_full["MES_VAL_tel"] == mes_sel]
mes_previo = df_full[df_full["MES_VAL_tel"] == (mes_sel - 1)]

if marca_sel != "Todas":
    mes_actual = mes_actual[mes_actual["MARCA"] == marca_sel]
    mes_previo = mes_previo[mes_previo["MARCA"] == marca_sel]

# 5. DASHBOARD DE EMISIONES
st.title(f"🌿 Dashboard de Sustentabilidad — {mes_sel}")
st.caption("Análisis de huella de carbono y eficiencia energética de la flota.")

if mes_actual.empty:
    st.warning("No hay datos para el mes seleccionado.")
else:
    # --- MÉTRICAS DE IMPACTO ---
    c1, c2, c3, c4 = st.columns(4)
    
    # Cálculo CO2 Total
    co2_now = mes_actual['Emisiones (KG CO2)'].sum()
    co2_prev = mes_previo['Emisiones (KG CO2)'].sum()
    delta_co2 = ((co2_now - co2_prev) / co2_prev * 100) if co2_prev > 0 else 0
    c1.metric("CO₂ TOTAL EMITIDO", f"{co2_now:,.0f} kg", delta=f"{delta_co2:.1f}%" if co2_prev > 0 else None, delta_color="inverse")

    # Intensidad (g/km)
    km_now = mes_actual['DISTANCIA RECORRIDA TELEMETRIA'].sum()
    int_now = (co2_now / km_now * 1000) if km_now > 0 else 0
    c2.metric("INTENSIDAD DE CARBONO", f"{int_now:.1f} g/km", help="Gramos de CO2 emitidos por cada kilómetro recorrido.")

    # Ahorro potencial (Ralentí a 0)
    ahorro_co2 = mes_actual['Ralenti (Lts)'].sum() * 2.68 # Coeficiente diésel
    c3.metric("CO₂ POR RALENTÍ", f"{ahorro_co2:,.1f} kg", delta="Evitable", delta_color="off")

    # Árboles necesarios para compensar (Cálculo estimado: 1 árbol absorbe 20kg/año)
    arboles = co2_now / 20
    c4.metric("COMPENSACIÓN", f"{int(arboles)} Árboles", help="Árboles necesarios por un año para absorber este mes de emisiones.")

    st.divider()

    # --- GRÁFICOS ---
    col_l, col_r = st.columns([1.5, 1])

    with col_l:
        st.subheader("📊 Huella de Carbono por Unidad (kg CO2)")
        df_rank = mes_actual.sort_values("Emisiones (KG CO2)", ascending=False)
        fig_bar = px.bar(df_rank, x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         color_continuous_scale="RdYlGn_r", template="plotly_dark")
        fig_bar.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        st.subheader("📉 Distribución por Marca")
        fig_pie = px.pie(mes_actual, values='Emisiones (KG CO2)', names='MARCA', 
                         hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- TABLA DE LIDERAZGO ---
    st.subheader("📋 Ranking de Eficiencia Ambiental")
    mes_actual['g_CO2_km'] = (mes_actual['Emisiones (KG CO2)'] / mes_actual['DISTANCIA RECORRIDA TELEMETRIA']) * 1000
    df_table = mes_actual[['DOMINIO', 'MARCA', 'DISTANCIA RECORRIDA TELEMETRIA', 'Emisiones (KG CO2)', 'g_CO2_km']].sort_values('g_CO2_km')
    
    st.dataframe(df_table.style.format({'g_CO2_km': '{:.1f}', 'Emisiones (KG CO2)': '{:,.0f}'}), use_container_width=True)

# 6. FOOTER
st.divider()
st.caption(f"Exclusivo Sustentabilidad - Expreso Diemar | Datos: {len(mes_actual)} registros activos.")
