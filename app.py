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
        background: linear-gradient(rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.9)), 
                    url("https://raw.githubusercontent.com/nicolascolonna23/DetectorDesvios/main/IMG_3101.jpg"); 
        background-size: cover;
        background-attachment: fixed;
    }
    [data-testid="stSidebar"] { background-color: rgba(10, 10, 10, 0.98); }
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #1565c0;
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
            d['MES'] = d['FECHA_DT'].dt.strftime('%B %Y')

    df = pd.merge(df_tel, df_con, on="DOMINIO", suffixes=('_tel', '_con'))
    return df

try:
    df_full = get_data()
except Exception as e:
    st.error(f"❌ Error crítico: {e}")
    st.stop()

# 3. SIDEBAR - NAVEGACIÓN Y FILTROS
with st.sidebar:
    st.image("logo_diemar4.png", use_container_width=True)
    st.divider()
    portal = st.radio("Sección:", ["📊 Desempeño", "⛽ Combustible", "🌿 Emisiones"])
    
    st.divider()
    if not df_full.empty:
        # Filtro de Mes
        meses = ["Todos"] + sorted(df_full["MES_tel"].dropna().unique().tolist())
        mes_sel = st.selectbox("📅 Filtrar Mes", meses)
        
        # Filtro de Patentes
        patentes = sorted(df_full["DOMINIO"].unique().tolist())
        sel_patentes = st.multiselect("🚚 Patentes", patentes)
        
        # Filtro de Marca
        marcas = ["Todas"] + sorted(df_full["MARCA"].dropna().unique().tolist())
        marca_sel = st.selectbox("🏭 Marca", marcas)

# Aplicar filtros
df = df_full.copy()
if mes_sel != "Todos":
    df = df[df["MES_tel"] == mes_sel]
if sel_patentes:
    df = df[df["DOMINIO"].isin(sel_patentes)]
if marca_sel != "Todas":
    df = df[df["MARCA"] == marca_sel]

# 4. VISTAS
if df.empty:
    st.warning("⚠️ Sin datos para los filtros seleccionados.")
else:
    # --- PESTAÑA 1: DESEMPEÑO ---
    if portal == "📊 Desempeño":
        st.title(f"📊 Desempeño de Flota - {mes_sel if mes_sel != 'Todos' else 'General'}")
        
        # Métricas principales
        c1, c2, c3, c4 = st.columns(4)
        prom_flota = df['Consumo c/ 100km TELEMETRIA'].mean()
        c1.metric("Km Totales", f"{df['DISTANCIA RECORRIDA TELEMETRIA'].sum():,.0f}")
        c2.metric("L/100km Prom. Flota", f"{prom_flota:.2f}")
        c3.metric("Litros Totales", f"{df['LITROS CONSUMIDOS'].sum():,.0f}")
        c4.metric("Unidades Activas", len(df['DOMINIO'].unique()))

        st.divider()
        
        # Fila de Gráficos de Eficiencia
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Ranking Consumo L/100km por Patente")
            # Ordenamos para ver quién gasta más
            df_cons = df.groupby('DOMINIO')['Consumo c/ 100km TELEMETRIA'].mean().reset_index().sort_values('Consumo c/ 100km TELEMETRIA', ascending=False)
            fig_cons = px.bar(df_cons, x='DOMINIO', y='Consumo c/ 100km TELEMETRIA', 
                              color='Consumo c/ 100km TELEMETRIA', color_continuous_scale='RdYlGn_r',
                              template="plotly_dark")
            # Línea promedio de flota
            fig_cons.add_hline(y=prom_flota, line_dash="dash", line_color="white", 
                               annotation_text=f"Promedio: {prom_flota:.2f}", annotation_position="top left")
            fig_cons.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_cons, use_container_width=True)

        with col2:
            st.subheader("🛣️ Kilómetros recorridos por Unidad")
            df_km = df.groupby('DOMINIO')['DISTANCIA RECORRIDA TELEMETRIA'].sum().reset_index().sort_values('DISTANCIA RECORRIDA TELEMETRIA', ascending=False)
            fig_km = px.bar(df_km, x='DISTANCIA RECORRIDA TELEMETRIA', y='DOMINIO', orientation='h',
                            color='DISTANCIA RECORRIDA TELEMETRIA', color_continuous_scale='Blues',
                            template="plotly_dark")
            fig_km.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_km, use_container_width=True)

        st.divider()
        st.subheader("📍 Mapa de Dispersión: Consumo vs Distancia")
        df_plot = df.copy()
        df_plot['size_burbuja'] = df_plot['Ralenti (Lts)'].fillna(0).clip(lower=0) + 5
        fig_scat = px.scatter(df_plot, x="DISTANCIA RECORRIDA TELEMETRIA", y="LITROS CONSUMIDOS", 
                             color="DOMINIO", size="size_burbuja", hover_name="DOMINIO",
                             template="plotly_dark")
        fig_scat.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_scat, use_container_width=True)

    # --- PESTAÑA 2: COMBUSTIBLE ---
    elif portal == "⛽ Combustible":
        st.title("⛽ Control de Combustible")
        m1, m2, m3 = st.columns(3)
        lts_tot = df['LITROS CONSUMIDOS'].sum()
        ral_tot = df['Ralenti (Lts)'].sum()
        m1.metric("Consumo Total (Lts)", f"{lts_tot:,.0f}")
        m2.metric("Ralentí Total (Lts)", f"{ral_tot:,.0f}")
        m3.metric("Kms Promedio/Mes", f"{(df['DISTANCIA RECORRIDA TELEMETRIA'].sum()/1000):.1f} mil")

        # Gráfico evolutivo por mes si se selecciona "Todos"
        if mes_sel == "Todos":
            st.subheader("Evolución Mensual de Consumo")
            df_line = df.groupby('MES_tel').agg({'Consumo c/ 100km TELEMETRIA':'mean', 'DISTANCIA RECORRIDA TELEMETRIA':'sum'}).reset_index()
            fig_line = px.line(df_line, x='MES_tel', y='Consumo c/ 100km TELEMETRIA', markers=True, template="plotly_dark")
            fig_line.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_line, use_container_width=True)

    # --- PESTAÑA 3: EMISIONES ---
    elif portal == "🌿 Emisiones":
        st.title("🌿 Portal de Sustentabilidad")
        e1, e2, e3 = st.columns(3)
        total_co2 = df['Emisiones (KG CO2)'].sum()
        km_tot = df['DISTANCIA RECORRIDA TELEMETRIA'].sum()
        e1.metric("CO2 Total (kg)", f"{total_co2:,.0f}")
        e2.metric("Eficiencia (gCO2/km)", f"{(total_co2/km_tot*1000):.1f}" if km_tot > 0 else "0")
        e3.metric("Unidades", len(df['DOMINIO'].unique()))

        fig_co2 = px.bar(df.sort_values("Emisiones (KG CO2)", ascending=False),
                         x="DOMINIO", y="Emisiones (KG CO2)", color="Emisiones (KG CO2)",
                         template="plotly_dark", color_continuous_scale="Reds")
        fig_co2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_co2, use_container_width=True)

# 5. FOOTER
st.divider()
st.caption(f"Fleet Analytics Expreso Diemar | Mostrando datos de: {mes_sel}")
