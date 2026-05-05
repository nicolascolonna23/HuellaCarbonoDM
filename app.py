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
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stHeader"] { background: transparent; }
.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(76, 175, 80, 0.2);
    border-radius: 16px;
    padding: 24px 20px;
    backdrop-filter: blur(12px);
    transition: all .25s ease;
    margin-bottom: 12px;
}
.kpi-hero {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(76, 175, 80, 0.25);
    border-radius: 18px;
    padding: 22px 20px 18px;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.kpi-hero::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #2e7d32, #66bb6a);
    border-radius: 18px 18px 0 0;
}
.kpi-icon  { font-size: 1.6rem; margin-bottom: 6px; display: block; }
.kpi-label { font-size: .72rem; color: #6b9e70; font-weight: 600; text-transform: uppercase; letter-spacing: .8px; margin-bottom: 6px; }
.kpi-value { font-size: 1.9rem; font-weight: 800; color: #f0fdf4; line-height: 1; }
.kpi-delta { font-size: .74rem; margin-top: 6px; font-weight: 600; }
.delta-up   { color: #ef4444; }
.delta-down { color: #4ade80; }
.delta-flat { color: #94a3b8; }
.equiv-card {
    background: rgba(46,125,50,0.12);
    border: 1px solid rgba(76,175,80,0.3);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
}
.equiv-icon  { font-size: 2.4rem; display: block; margin-bottom: 10px; }
.equiv-num   { font-size: 2rem; font-weight: 800; color: #86efac; line-height: 1; }
.equiv-label { font-size: .75rem; color: #6b9e70; margin-top: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
.sec-title {
    font-size: 1rem; font-weight: 700; color: #a7f3d0;
    text-transform: uppercase; letter-spacing: .8px;
    border-left: 3px solid #2e7d32; padding-left: 10px;
    margin: 20px 0 14px;
}
.rank-row { display:flex; align-items:center; padding:9px 0; border-bottom:1px solid rgba(76,175,80,0.1); }
.rank-num  { width:26px; font-size:.85rem; font-weight:700; color:#6b9e70; }
.rank-dom  { width:90px; font-size:.85rem; font-weight:700; color:#e2e8f0; }
.rank-bg   { flex:1; height:8px; background:rgba(255,255,255,0.06); border-radius:4px; margin:0 10px; overflow:hidden; }
.rank-fill { height:8px; border-radius:4px; }
.rank-val  { font-size:.82rem; font-weight:700; width:80px; text-align:right; }
.alerta-box { background: rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.35); border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; }
.ok-box { background: rgba(74,222,128,0.08); border:1px solid rgba(74,222,128,0.3); border-radius: 12px; padding: 14px 18px; margin-bottom: 10px; }
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

    def norm(df):
        df.columns = (df.columns.str.strip().str.upper()
                      .str.replace('Í','I').str.replace('Á','A')
                      .str.replace('É','E').str.replace('Ó','O'))
        m = {}
        for c in df.columns:
            if "DOMINIO" in c: m[c] = "DOMINIO"
            elif "FECHA" in c: m[c] = "FECHA"
            elif ("KM" in c or "KILOM" in c or "DISTANCIA" in c) and "CO2" not in c: m[c] = "KMS"
            elif "CO2" in c or "EMISION" in c: m[c] = "CO2"
            elif "RALENTI" in c: m[c] = "RALENTI"
            elif "MARCA" in c: m[c] = "MARCA"
        df = df.rename(columns=m)

        for nc in ["KMS","CO2","RALENTI"]:
            if nc in df.columns:
                df[nc] = pd.to_numeric(
                    df[nc].astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),
                    errors='coerce').fillna(0)

        if 'DOMINIO' in df.columns:
            df['DOMINIO'] = df['DOMINIO'].astype(str).str.strip().str.replace(' ','').str.upper()

        # --- ARREGLO PARA MARZO/ABRIL ---
        if 'FECHA' in df.columns:
            # Forzamos conversión a datetime y luego a string YYYY-MM
            # Esto ignora si en el Excel dice "01/03/2026" o "marzo-26"
            dt_series = pd.to_datetime(df['FECHA'], dayfirst=True, errors='coerce')
            df['MES'] = dt_series.dt.strftime('%Y-%m')
            # Si falló (ej: celdas ya formateadas como YYYY-MM), rescatamos el valor original
            df.loc[df['MES'].isna(), 'MES'] = df['FECHA'].astype(str).str.strip().str.slice(0,7)
        
        return df

    df_emi = norm(df_emi)
    df_kms = norm(df_kms)

    # Quitamos la MARCA de df_emi si existe para que no se duplique en el merge
    if 'MARCA' in df_emi.columns and 'MARCA' in df_kms.columns:
        df_emi = df_emi.drop(columns=['MARCA'])

    # Merge por Dominio y Mes (Aseguramos que ambas tablas tengan MES limpio)
    df = df_emi.merge(df_kms[['DOMINIO', 'MES', 'KMS', 'MARCA']], 
                      on=['DOMINIO', 'MES'], 
                      how='left')
    
    # Rellenamos nulos por si alguna unidad no tiene km o marca reportada
    df['KMS'] = df['KMS'].fillna(0)
    df['MARCA'] = df['MARCA'].fillna("Sin Marca")

    df['CO2_RALENTI'] = df['RALENTI'] * FACTOR_CO2 if 'RALENTI' in df.columns else 0
    df['CO2_DIRECTO'] = np.maximum(df['CO2'] - df['CO2_RALENTI'], 0)
    df['INTENSIDAD']  = np.where(df['KMS'] > 0, df['CO2'] / df['KMS'] * 1000, 0)

    return df

# ── Carga ──────────────────────────────────────────────────────────────────────
try:
    df_master = get_data()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/HuellaCarbonoDM/main/logo_diemar4.png", width=180)
    st.markdown("---")
    meses_disp = sorted(df_master['MES'].dropna().unique().tolist())
    mes_desde  = st.selectbox("Desde", meses_disp, index=0)
    mes_hasta  = st.selectbox("Hasta", meses_disp, index=len(meses_disp) - 1)
    if mes_desde > mes_hasta: mes_desde, mes_hasta = mes_hasta, mes_desde
    marcas_disp = ["Todas"] + sorted(df_master['MARCA'].unique().tolist())
    marca_sel = st.selectbox("🚛 Marca", marcas_disp)

# ── Filtro ─────────────────────────────────────────────────────────────────────
df = df_master[(df_master['MES'] >= mes_desde) & (df_master['MES'] <= mes_hasta)].copy()
if marca_sel != "Todas":
    df = df[df['MARCA'] == marca_sel]

# Cálculo Período Anterior (Deltas)
idx_d = meses_disp.index(mes_desde)
n_r = len(df['MES'].unique())
if idx_d >= n_r:
    df_ant = df_master[(df_master['MES'] >= meses_disp[idx_d - n_r]) & (df_master['MES'] < mes_desde)].copy()
    if marca_sel != "Todas": df_ant = df_ant[df_ant['MARCA'] == marca_sel]
else:
    df_ant = pd.DataFrame()

# ── Renderizado ───────────────────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)
periodo_label = f"{mes_desde} → {mes_hasta}"

st.markdown(f"""
<div style="margin-bottom:24px;">
  <div style="font-size:1.7rem;font-weight:800;color:#f0fdf4;">🌿 Carbon Tracker — {periodo_label}</div>
  <div style="font-size:.88rem;color:#6b9e70;">Flota Expreso Diemar · {df['DOMINIO'].nunique()} unidades activas</div>
</div>
""", unsafe_allow_html=True)

def delta_h(curr, prev, inv=False):
    if prev == 0 or pd.isna(prev): return "—"
    pct = (curr - prev) / prev * 100
    c = "delta-up" if (pct > 0 and not inv) or (pct < 0 and inv) else "delta-down"
    return f'<span class="{c}">{"▲" if pct > 0 else "▼"} {abs(pct):.1f}% vs anterior</span>'

c_t = df['CO2'].sum()
k_t = df['KMS'].sum()
r_t = df['RALENTI'].sum()
i_t = (c_t / k_t * 1000) if k_t > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="kpi-hero"><div class="kpi-label">CO2 Total</div><div class="kpi-value">{c_t:,.0f} kg</div><div class="kpi-delta">{delta_h(c_t, df_ant["CO2"].sum() if not df_ant.empty else 0, True)}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-hero"><div class="kpi-label">Distancia</div><div class="kpi-value">{k_t:,.0f} km</div><div class="kpi-delta">{delta_h(k_t, df_ant["KMS"].sum() if not df_ant.empty else 0)}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-hero"><div class="kpi-label">Intensidad</div><div class="kpi-value">{i_t:.1f} g/km</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="kpi-hero"><div class="kpi-label">Ralentí</div><div class="kpi-value">{r_t:,.0f} L</div></div>', unsafe_allow_html=True)

# Equivalencias
st.markdown('<div class="sec-title">Equivalencias ambientales</div>', unsafe_allow_html=True)
e1, e2, e3, e4 = st.columns(4)
e1.markdown(f'<div class="equiv-card"><span class="equiv-icon">🌳</span><div class="equiv-num">{c_t/ARBOL_KG_AÑO:,.0f}</div><div class="equiv-label">Árboles para compensar</div></div>', unsafe_allow_html=True)
e2.markdown(f'<div class="equiv-card"><span class="equiv-icon">✈️</span><div class="equiv-num">{c_t/KG_VUELO:,.0f}</div><div class="equiv-label">Vuelos BsAs-Cba</div></div>', unsafe_allow_html=True)
e3.markdown(f'<div class="equiv-card"><span class="equiv-icon">🚗</span><div class="equiv-num">{c_t/KG_AUTO_KM/1000:,.0f}k</div><div class="equiv-label">KM auto promedio</div></div>', unsafe_allow_html=True)
e4.markdown(f'<div class="equiv-card"><span class="equiv-icon">🌿</span><div class="equiv-num">{r_t*FACTOR_CO2:,.0f} kg</div><div class="equiv-label">CO2 Evitable (Idle)</div></div>', unsafe_allow_html=True)

# Ranking
st.markdown('<div class="sec-title">Ranking por Unidad</div>', unsafe_allow_html=True)
rank = df.groupby('DOMINIO').agg({'CO2':'sum', 'KMS':'sum'}).reset_index().sort_values('CO2', ascending=False)
rank['INT'] = np.where(rank['KMS']>0, rank['CO2']/rank['KMS']*1000, 0)
st.dataframe(rank, use_container_width=True, hide_index=True)

# Gráfico Tendencia
st.markdown('<div class="sec-title">Tendencia histórica</div>', unsafe_allow_html=True)
hist = df_master.groupby('MES').agg({'CO2':'sum', 'KMS':'sum'}).reset_index()
fig = px.line(hist, x='MES', y='CO2', title='Emisiones Mensuales (kg CO2)')
fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e2e8f0'))
st.plotly_chart(fig, use_container_width=True)
