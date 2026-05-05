import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Expreso Diemar — Carbon Tracker",
    page_icon="🌿",
    layout="wide"
)

FACTOR_CO2   = 2.68   # kg CO2 por litro de gasoil
ARBOL_KG_AÑO = 21.0  # kg CO2 que absorbe un árbol por año
KG_VUELO     = 150.0  # kg CO2 vuelo BsAs-Córdoba (ida)
KG_AUTO_KM   = 0.12   # kg CO2 por km en auto promedio

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #020c05 0%, #051a0a 50%, #020c05 100%);
    min-height: 100vh;
}
[data-testid="stSidebar"] {
    background: rgba(5, 26, 10, 0.95);
    border-right: 1px solid rgba(46, 125, 50, 0.3);
}
.kpi-hero {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(76, 175, 80, 0.25);
    border-radius: 18px;
    padding: 22px 20px 18px;
    text-align: center;
}
.kpi-value { font-size: 1.9rem; font-weight: 800; color: #f0fdf4; }
.sec-title {
    font-size: 1rem; font-weight: 700; color: #a7f3d0;
    text-transform: uppercase; border-left: 3px solid #2e7d32; padding-left: 10px;
    margin: 20px 0 14px;
}
.equiv-card {
    background: rgba(46,125,50,0.12);
    border: 1px solid rgba(76,175,80,0.3);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
}
footer { display: none !important; }
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
#  DATOS
# ══════════════════════════════════════════════════════════════════════════════
SHEET_ID = "1u7cckay0IJ60bfoKk2OZo-TjCvTbH9O1wKxNFdSKDCQ"
BASE_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=120)
def get_data():
    df_emi = pd.read_csv(f"{BASE_URL}&gid=882343299")
    df_kms = pd.read_csv(f"{BASE_URL}&gid=1044040871")

    def process_sheet(df):
        # Normalizar nombres de columnas (quitar espacios, tildes y a mayúsculas)
        df.columns = (df.columns.str.strip().str.upper()
                      .str.replace('Í','I').str.replace('Á','A')
                      .str.replace('É','E').str.replace('Ó','O').str.replace('Ú','U'))
        
        # Mapeo inteligente
        m = {}
        for c in df.columns:
            if "DOMINIO" in c: m[c] = "DOMINIO"
            elif "FECHA" in c: m[c] = "FECHA"
            elif "MARCA" in c: m[c] = "MARCA"
            elif "RALENTI" in c or "IDLE" in c: m[c] = "RALENTI"
            elif ("KM" in c or "DISTANCIA" in c) and "CO2" not in c: m[c] = "KMS"
            elif "CO2" in c or "EMISION" in c: m[c] = "CO2"
        df = df.rename(columns=m)

        # Asegurar columnas mínimas para que no explote
        for col in ["KMS", "CO2", "RALENTI"]:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        if 'DOMINIO' in df.columns:
            df['DOMINIO'] = df['DOMINIO'].astype(str).str.strip().str.upper()
        
        if 'FECHA' in df.columns:
            df['FECHA_DT'] = pd.to_datetime(df['FECHA'], dayfirst=True, errors='coerce')
            df['MES'] = df['FECHA_DT'].dt.strftime('%Y-%m')
            # Fallback por si la fecha ya viene como texto YYYY-MM
            df['MES'] = df['MES'].fillna(df['FECHA'].astype(str).str.strip().str.slice(0, 7))
        
        return df

    df_emi = process_sheet(df_emi)
    df_kms = process_sheet(df_kms)

    # Merge por Dominio y Mes
    # Usamos solo las columnas de KMS que necesitamos para la unión
    df_kms_red = df_kms[['DOMINIO', 'MES', 'KMS', 'MARCA']].drop_duplicates(subset=['DOMINIO', 'MES'])
    
    df = df_emi.merge(df_kms_red, on=['DOMINIO', 'MES'], how='left', suffixes=('', '_KMS_REF'))
    
    # Consolidar Kilómetros y Marca tras el merge
    if 'KMS_KMS_REF' in df.columns:
        df['KMS'] = df['KMS_KMS_REF'].fillna(df['KMS'])
        df.drop(columns=['KMS_KMS_REF'], inplace=True)
    if 'MARCA_KMS_REF' in df.columns:
        df['MARCA'] = df['MARCA'].fillna(df['MARCA_KMS_REF'])
        df.drop(columns=['MARCA_KMS_REF'], inplace=True)

    # Cálculos finales
    df['CO2_RALENTI'] = df['RALENTI'] * FACTOR_CO2
    df['INTENSIDAD']  = np.where(df['KMS'] > 0, (df['CO2'] / df['KMS']) * 1000, 0)
    
    return df

try:
    df_master = get_data()
except Exception as e:
    st.error(f"Error procesando datos: {e}")
    st.stop()

# ── Sidebar y Filtros ──────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/HuellaCarbonoDM/main/logo_diemar4.png", width=180)
    meses = sorted(df_master['MES'].dropna().unique().tolist())
    mes_desde = st.selectbox("Desde", meses, index=0)
    mes_hasta = st.selectbox("Hasta", meses, index=len(meses)-1)
    
    marcas = ["Todas"] + sorted(df_master['MARCA'].dropna().unique().tolist())
    marca_sel = st.selectbox("🚛 Marca", marcas)

# Aplicar Filtros
df_sel = df_master[(df_master['MES'] >= mes_desde) & (df_master['MES'] <= mes_hasta)].copy()
if marca_sel != "Todas":
    df_sel = df_sel[df_sel['MARCA'] == marca_sel]

# ── Interfaz ──────────────────────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(f'<div style="font-size:1.7rem;font-weight:800;color:#f0fdf4;">🌿 Carbon Tracker — {mes_desde} a {mes_hasta}</div>', unsafe_allow_html=True)

# KPIs
co2_t = df_sel['CO2'].sum()
kms_t = df_sel['KMS'].sum()
ral_t = df_sel['RALENTI'].sum()
int_t = (co2_t / kms_t * 1000) if kms_t > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="kpi-hero"><div style="color:#6b9e70;font-size:.7rem;">CO2 TOTAL</div><div class="kpi-value">{co2_t:,.0f} kg</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-hero"><div style="color:#6b9e70;font-size:.7rem;">DISTANCIA</div><div class="kpi-value">{kms_t:,.0f} km</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-hero"><div style="color:#6b9e70;font-size:.7rem;">INTENSIDAD</div><div class="kpi-value">{int_t:.1f} g/km</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi-hero"><div style="color:#6b9e70;font-size:.7rem;">RALENTÍ</div><div class="kpi-value">{ral_t:,.0f} L</div></div>', unsafe_allow_html=True)

# Equivalencias
st.markdown('<div class="sec-title">Equivalencias ambientales</div>', unsafe_allow_html=True)
e1, e2, e3, e4 = st.columns(4)
e1.markdown(f'<div class="equiv-card">🌳<br><span style="font-size:1.5rem;font-weight:800;">{co2_t/ARBOL_KG_AÑO:,.0f}</span><br>Árboles/año</div>', unsafe_allow_html=True)
e2.markdown(f'<div class="equiv-card">✈️<br><span style="font-size:1.5rem;font-weight:800;">{co2_t/KG_VUELO:,.0f}</span><br>Vuelos BsAs-Cba</div>', unsafe_allow_html=True)
e3.markdown(f'<div class="equiv-card">🚗<br><span style="font-size:1.5rem;font-weight:800;">{co2_t/KG_AUTO_KM/1000:,.0f}k</span><br>KM auto</div>', unsafe_allow_html=True)
e4.markdown(f'<div class="equiv-card">🌿<br><span style="font-size:1.5rem;font-weight:800;">{df_sel["CO2_RALENTI"].sum():,.0f}kg</span><br>CO2 Evitable</div>', unsafe_allow_html=True)

# Tabla Detalle
st.markdown('<div class="sec-title">Detalle por Unidad</div>', unsafe_allow_html=True)
st.dataframe(df_sel[['DOMINIO', 'MARCA', 'MES', 'KMS', 'CO2', 'INTENSIDAD']].sort_values('CO2', ascending=False), use_container_width=True, hide_index=True)
