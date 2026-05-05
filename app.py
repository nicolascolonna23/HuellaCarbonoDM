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

# Mantenemos tu CSS original
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
    position: relative;
}
.kpi-value { font-size: 1.9rem; font-weight: 800; color: #f0fdf4; }
.equiv-card {
    background: rgba(46,125,50,0.12);
    border: 1px solid rgba(76,175,80,0.3);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
}
.sec-title {
    font-size: 1rem; font-weight: 700; color: #a7f3d0;
    text-transform: uppercase; border-left: 3px solid #2e7d32; padding-left: 10px;
    margin: 20px 0 14px;
}
.delta-up { color: #ef4444; }
.delta-down { color: #4ade80; }
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

    def clean_df(df):
        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.upper().str.replace('[ÍÁÉÓÚ]', 'X', regex=True)
        
        # Diccionario de mapeo manual para evitar errores
        cols = df.columns
        m = {}
        for c in cols:
            if "DOMINIO" in c: m[c] = "DOMINIO"
            elif "FECHA" in c: m[c] = "FECHA"
            elif "MARCA" in c: m[c] = "MARCA"
            elif "RALENTI" in c: m[c] = "RALENTI"
            elif ("KM" in c or "DISTANCIA" in c) and "CO2" not in c: m[c] = "KMS"
            elif "CO2" in c or "EMISION" in c: m[c] = "CO2"
        
        df = df.rename(columns=m)

        # Limpiar numéricos
        for col in ["KMS", "CO2", "RALENTI"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)

        # Limpiar Dominio y Fecha
        if 'DOMINIO' in df.columns:
            df['DOMINIO'] = df['DOMINIO'].astype(str).str.strip().str.upper()
        
        if 'FECHA' in df.columns:
            # Convertir a datetime y crear columna MES como YYYY-MM
            df['FECHA_DT'] = pd.to_datetime(df['FECHA'], dayfirst=True, errors='coerce')
            df['MES'] = df['FECHA_DT'].dt.strftime('%Y-%m')
            # Si falla, intentar tomar los primeros 7 caracteres (ej: 2026-03)
            df['MES'] = df['MES'].fillna(df['FECHA'].astype(str).str.strip().str.slice(0, 7))
        
        return df

    df_emi = clean_df(df_emi)
    df_kms = clean_df(df_kms)

    # El corazón del problema: El Merge. 
    # Solo nos quedamos con las columnas necesarias de KMS para unir a EMI
    df_kms_subset = df_kms[['DOMINIO', 'MES', 'KMS', 'MARCA']].drop_duplicates(subset=['DOMINIO', 'MES'])

    # Unimos kms a la tabla de emisiones
    df = df_emi.merge(df_kms_subset, on=['DOMINIO', 'MES'], how='left', suffixes=('', '_KMS'))
    
    # Consolidar columnas si se duplicaron
    if 'KMS_KMS' in df.columns:
        df['KMS'] = df['KMS_KMS'].fillna(df['KMS'])
        df = df.drop(columns=['KMS_KMS'])
    if 'MARCA_KMS' in df.columns:
        df['MARCA'] = df['MARCA'].fillna(df['MARCA_KMS'])
        df = df.drop(columns=['MARCA_KMS'])

    df['CO2_RALENTI'] = df['RALENTI'] * FACTOR_CO2
    df['INTENSIDAD']  = np.where(df['KMS'] > 0, (df['CO2'] / df['KMS']) * 1000, 0)

    return df

try:
    df_master = get_data()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/HuellaCarbonoDM/main/logo_diemar4.png", width=180)
    meses_disp = sorted(df_master['MES'].dropna().unique().tolist())
    mes_desde = st.selectbox("Desde", meses_disp, index=0)
    mes_hasta = st.selectbox("Hasta", meses_disp, index=len(meses_disp)-1)
    
    marcas = ["Todas"] + sorted(df_master['MARCA'].dropna().unique().tolist())
    marca_sel = st.selectbox("🚛 Marca", marcas)

# ── Filtros y Cálculos ──────────────────────────────────────────────────────────
df = df_master[(df_master['MES'] >= mes_desde) & (df_master['MES'] <= mes_hasta)].copy()
if marca_sel != "Todas":
    df = df[df['MARCA'] == marca_sel]

# Período anterior para deltas
idx = meses_disp.index(mes_desde)
if idx > 0:
    ant_mes = meses_disp[idx-1]
    df_ant = df_master[df_master['MES'] == ant_mes]
else:
    df_ant = pd.DataFrame()

# ── Render ─────────────────────────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

# Encabezado
st.markdown(f'<div style="font-size:1.7rem;font-weight:800;color:#f0fdf4;">🌿 Carbon Tracker — {mes_desde} a {mes_hasta}</div>', unsafe_allow_html=True)

# Métricas Principales
m1, m2, m3, m4 = st.columns(4)
co2_t = df['CO2'].sum()
kms_t = df['KMS'].sum()
int_t = (co2_t / kms_t * 1000) if kms_t > 0 else 0

m1.markdown(f'<div class="kpi-hero"><div style="color:#6b9e70;font-size:.8rem;">CO2 TOTAL</div><div class="kpi-value">{co2_t:,.0f} kg</div></div>', unsafe_allow_html=True)
m2.markdown(f'<div class="kpi-hero"><div style="color:#6b9e70;font-size:.8rem;">KM RECORRIDOS</div><div class="kpi-value">{kms_t:,.0f} km</div></div>', unsafe_allow_html=True)
m3.markdown(f'<div class="kpi-hero"><div style="color:#6b9e70;font-size:.8rem;">INTENSIDAD</div><div class="kpi-value">{int_t:.1f} g/km</div></div>', unsafe_allow_html=True)
m4.markdown(f'<div class="kpi-hero"><div style="color:#6b9e70;font-size:.8rem;">RALENTÍ</div><div class="kpi-value">{df["RALENTI"].sum():,.0f} L</div></div>', unsafe_allow_html=True)

# Equivalencias
st.markdown('<div class="sec-title">Equivalencias ambientales</div>', unsafe_allow_html=True)
e1, e2, e3, e4 = st.columns(4)
e1.markdown(f'<div class="equiv-card">🌳<br><span style="font-size:1.5rem;font-weight:800;">{co2_t/ARBOL_KG_AÑO:,.0f}</span><br>Árboles/año</div>', unsafe_allow_html=True)
e2.markdown(f'<div class="equiv-card">✈️<br><span style="font-size:1.5rem;font-weight:800;">{co2_t/KG_VUELO:,.0f}</span><br>Vuelos BsAs-Cba</div>', unsafe_allow_html=True)
e3.markdown(f'<div class="equiv-card">🚗<br><span style="font-size:1.5rem;font-weight:800;">{co2_t/KG_AUTO_KM/1000:,.0f}k</span><br>KM auto</div>', unsafe_allow_html=True)
e4.markdown(f'<div class="equiv-card">🌿<br><span style="font-size:1.5rem;font-weight:800;">{df["CO2_RALENTI"].sum():,.0f}kg</span><br>CO2 Evitable</div>', unsafe_allow_html=True)

# Tabla
st.markdown('<div class="sec-title">Detalle por Unidad</div>', unsafe_allow_html=True)
st.dataframe(df[['DOMINIO', 'MARCA', 'MES', 'KMS', 'CO2', 'INTENSIDAD']], use_container_width=True, hide_index=True)
