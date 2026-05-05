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

/* Ocultar header streamlit */
[data-testid="stHeader"] { background: transparent; }

/* Cards glass */
.glass-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(76, 175, 80, 0.2);
    border-radius: 16px;
    padding: 24px 20px;
    backdrop-filter: blur(12px);
    transition: all .25s ease;
    margin-bottom: 12px;
}
.glass-card:hover {
    border-color: rgba(76, 175, 80, 0.5);
    background: rgba(255,255,255,0.07);
}

/* KPI hero */
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
.kpi-label { font-size: .72rem; color: #6b9e70; font-weight: 600;
             text-transform: uppercase; letter-spacing: .8px; margin-bottom: 6px; }
.kpi-value { font-size: 1.9rem; font-weight: 800; color: #f0fdf4; line-height: 1; }
.kpi-delta { font-size: .74rem; margin-top: 6px; font-weight: 600; }
.delta-up   { color: #ef4444; }
.delta-down { color: #4ade80; }
.delta-flat { color: #94a3b8; }

/* Equivalencias */
.equiv-card {
    background: rgba(46,125,50,0.12);
    border: 1px solid rgba(76,175,80,0.3);
    border-radius: 16px;
    padding: 20px;
    text-align: center;
}
.equiv-icon  { font-size: 2.4rem; display: block; margin-bottom: 10px; }
.equiv-num   { font-size: 2rem; font-weight: 800; color: #86efac; line-height: 1; }
.equiv-label { font-size: .75rem; color: #6b9e70; margin-top: 6px;
                font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }

/* Sección */
.sec-title {
    font-size: 1rem; font-weight: 700; color: #a7f3d0;
    text-transform: uppercase; letter-spacing: .8px;
    border-left: 3px solid #2e7d32; padding-left: 10px;
    margin: 20px 0 14px;
}

/* Ranking bar */
.rank-row { display:flex; align-items:center; padding:9px 0; border-bottom:1px solid rgba(76,175,80,0.1); }
.rank-num  { width:26px; font-size:.85rem; font-weight:700; color:#6b9e70; }
.rank-dom  { width:90px; font-size:.85rem; font-weight:700; color:#e2e8f0; }
.rank-bg   { flex:1; height:8px; background:rgba(255,255,255,0.06); border-radius:4px; margin:0 10px; overflow:hidden; }
.rank-fill { height:8px; border-radius:4px; }
.rank-val  { font-size:.82rem; font-weight:700; width:80px; text-align:right; }

/* Alerta */
.alerta-box {
    background: rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.35);
    border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
}
.ok-box {
    background: rgba(74,222,128,0.08); border:1px solid rgba(74,222,128,0.3);
    border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
}

/* Ocultar elementos extra */
.stMarkdown p, .stMarkdown span, .stMarkdown div { color: #e2e8f0 !important; }
[data-testid="stMetricValue"] { color: #f0fdf4 !important; }
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
    # Cargamos ambas hojas
    df_emi = pd.read_csv(f"{BASE_URL}&gid=882343299")
    df_kms = pd.read_csv(f"{BASE_URL}&gid=1044040871")

    def norm(df):
        df.columns = (df.columns.str.strip().str.upper()
                      .str.replace('Í','I').str.replace('Á','A')
                      .str.replace('É','E').str.replace('Ó','O'))
        m = {}
        for c in df.columns:
            if   "DOMINIO" in c:                                     m[c] = "DOMINIO"
            elif "FECHA"   in c:                                     m[c] = "FECHA"
            elif ("KM" in c or "KILOM" in c or "DISTANCIA" in c or "RECORRID" in c) and "CO2" not in c and "L/100" not in c: m[c] = "KMS"
            elif "CO2"     in c or "EMISION" in c:                   m[c] = "CO2"
            elif "RALENTI" in c:                                     m[c] = "RALENTI"
            elif "MARCA"   in c:                                     m[c] = "MARCA"
        df = df.rename(columns=m)

        # Procesar valores numéricos
        for nc in ["KMS","CO2","RALENTI"]:
            if nc in df.columns:
                df[nc] = pd.to_numeric(
                    df[nc].astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),
                    errors='coerce').fillna(0)

        # Limpieza estricta de dominios
        if 'DOMINIO' in df.columns:
            df['DOMINIO'] = df['DOMINIO'].astype(str).str.strip().str.replace(' ','').str.upper()

        # --- NORMALIZACIÓN CRÍTICA DE FECHA PARA EL MERGE ---
        if 'FECHA' in df.columns:
            # Forzamos conversión a datetime (dayfirst ayuda con formatos latinos)
            df['FECHA_DT'] = pd.to_datetime(df['FECHA'], dayfirst=True, errors='coerce')
            
            # Si falló (ej: formato "2026-03"), reintentamos sin dayfirst
            mask_nat = df['FECHA_DT'].isna()
            if mask_nat.any():
                df.loc[mask_nat, 'FECHA_DT'] = pd.to_datetime(df.loc[mask_nat, 'FECHA'], errors='coerce')
            
            # Creamos la columna MES con formato uniforme YYYY-MM
            df['MES'] = df['FECHA_DT'].dt.strftime('%Y-%m')
        
        # Si la columna ya se llama MES o periodo, aseguramos formato YYYY-MM
        if 'MES' in df.columns:
             df['MES'] = df['MES'].astype(str).str.strip()
        elif 'FECHA' not in df.columns:
             # buscar algo que parezca fecha
             for c in df.columns:
                 if df[c].astype(str).str.contains(r'\d{4}-\d{2}', regex=True).any():
                     df['MES'] = df[c].astype(str).str.strip()
                     break

        return df

    df_emi = norm(df_emi)
    df_kms = norm(df_kms)

    # Creamos un diccionario de Marcas para asegurar que no se pierdan
    marca_lk = (df_kms[['DOMINIO','MARCA']].dropna(subset=['MARCA'])
                .drop_duplicates('DOMINIO', keep='last')
                if 'MARCA' in df_kms.columns else pd.DataFrame(columns=['DOMINIO','MARCA']))

    # MERGE: Unimos los KMS a la tabla de Emisiones usando DOMINIO y MES estandarizado
    cols_k = [c for c in ['DOMINIO','MES','KMS'] if c in df_kms.columns]
    df = df_emi.merge(df_kms[cols_k], on=['DOMINIO','MES'], how='left', suffixes=('', '_KMS_RAW'))
    
    # Si los KMS vinieron del merge, los usamos; si no, dejamos el original o 0
    if 'KMS_KMS_RAW' in df.columns:
        df['KMS'] = df['KMS_KMS_RAW'].fillna(df.get('KMS', 0))
        df.drop(columns=['KMS_KMS_RAW'], inplace=True)

    # MARCA: Re-asociar marca si se perdió en el merge
    if 'MARCA' not in df.columns or df['MARCA'].isna().all():
        df = df.drop(columns=['MARCA'], errors='ignore').merge(marca_lk, on='DOMINIO', how='left')
    else:
        df = df.merge(marca_lk.rename(columns={'MARCA':'_MF'}), on='DOMINIO', how='left')
        df['MARCA'] = df['MARCA'].fillna(df.get('_MF',''))
        df.drop(columns=['_MF'], errors='ignore', inplace=True)

    # Métricas derivadas
    df['CO2_RALENTI'] = df['RALENTI'] * FACTOR_CO2 if 'RALENTI' in df.columns else 0
    df['CO2_DIRECTO'] = np.maximum(df['CO2'] - df['CO2_RALENTI'], 0)
    # Intensidad: gramos de CO2 por kilómetro
    df['INTENSIDAD']  = np.where(df['KMS'] > 0, (df['CO2'] / df['KMS']) * 1000, 0)

    return df

# ── Carga Final ───────────────────────────────────────────────────────────────
try:
    df_master = get_data()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# ── Sidebar y Filtros ──────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/HuellaCarbonoDM/main/logo_diemar4.png", width=180)
    st.markdown("---")
    meses_disp = sorted(df_master['MES'].dropna().unique().tolist())
    mes_desde  = st.selectbox("Desde", meses_disp, index=0)
    mes_hasta  = st.selectbox("Hasta", meses_disp, index=len(meses_disp) - 1)
    if mes_desde > mes_hasta: mes_desde, mes_hasta = mes_hasta, mes_desde
    
    marcas_disp = ["Todas"] + sorted(df_master['MARCA'].dropna().unique().tolist()) if 'MARCA' in df_master.columns else ["Todas"]
    marca_sel = st.selectbox("🚛 Marca", marcas_disp)
    st.markdown("---")
    st.markdown(f"<div style='font-size:.72rem;color:#4ade80;'>🔄 Actualización cada 2 min</div>", unsafe_allow_html=True)

# Filtro de los datos actuales
df = df_master[(df_master['MES'] >= mes_desde) & (df_master['MES'] <= mes_hasta)].copy()
if marca_sel != "Todas":
    df = df[df['MARCA'] == marca_sel]

# Período anterior (para deltas)
idx_desde = meses_disp.index(mes_desde)
n_rango = len(df['MES'].unique())
if idx_desde >= n_rango:
    ant_hasta = meses_disp[idx_desde - 1]
    ant_desde = meses_disp[max(0, idx_desde - n_rango)]
    df_ant = df_master[(df_master['MES'] >= ant_desde) & (df_master['MES'] <= ant_hasta)].copy()
    if marca_sel != "Todas": df_ant = df_ant[df_ant['MARCA'] == marca_sel]
else:
    df_ant = pd.DataFrame()

# ── Renderizado Principal ──────────────────────────────────────────────────────
st.markdown(CSS, unsafe_allow_html=True)

if df.empty:
    st.warning("No hay datos para la selección.")
    st.stop()

periodo_label = mes_desde if mes_desde == mes_hasta else f"{mes_desde} → {mes_hasta}"

st.markdown(f"""
<div style="margin-bottom:24px;">
  <div style="font-size:1.7rem;font-weight:800;color:#f0fdf4;letter-spacing:-.5px;">🌿 Carbon Tracker — {periodo_label}</div>
  <div style="font-size:.88rem;color:#6b9e70;margin-top:4px;">Flota Expreso Diemar · {df['DOMINIO'].nunique()} unidades activas</div>
</div>
""", unsafe_allow_html=True)

# Métricas
co2_total  = df['CO2'].sum()
kms_total  = df['KMS'].sum()
ral_total  = df['RALENTI'].sum()
int_total  = (co2_total / kms_total * 1000) if kms_total > 0 else 0

co2_ant = df_ant['CO2'].sum() if not df_ant.empty else 0
kms_ant = df_ant['KMS'].sum() if not df_ant.empty else 0

def delta_html(curr, prev, invert=False):
    if prev == 0: return '<span class="delta-flat">— sin dato</span>'
    pct = (curr - prev) / prev * 100
    css = "delta-up" if (pct > 0 and not invert) or (pct < 0 and invert) else "delta-down"
    return f'<span class="{css}">{"▲" if pct > 0 else "▼"} {abs(pct):.1f}%</span>'

k1, k2, k3, k4 = st.columns(4)
k1.markdown(f'<div class="kpi-hero"><div class="kpi-label">CO2 Total</div><div class="kpi-value">{co2_total:,.0f} kg</div><div class="kpi-delta">{delta_html(co2_total, co2_ant, True)}</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-hero"><div class="kpi-label">Distancia</div><div class="kpi-value">{kms_total:,.0f} km</div><div class="kpi-delta">{delta_html(kms_total, kms_ant)}</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-hero"><div class="kpi-label">Intensidad</div><div class="kpi-value">{int_total:.1f} g/km</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-hero"><div class="kpi-label">Ralentí</div><div class="kpi-value">{ral_total:,.0f} L</div></div>', unsafe_allow_html=True)

# Resto de secciones (Equivalencias, Ranking, Gráficos) se mantienen igual que tu original...
st.markdown('<div class="sec-title">Equivalencias ambientales</div>', unsafe_allow_html=True)
e1, e2, e3, e4 = st.columns(4)
e1.markdown(f'<div class="equiv-card"><span class="equiv-icon">🌳</span><div class="equiv-num">{co2_total/ARBOL_KG_AÑO:,.0f}</div><div class="equiv-label">Árboles necesarios</div></div>', unsafe_allow_html=True)
e2.markdown(f'<div class="equiv-card"><span class="equiv-icon">✈️</span><div class="equiv-num">{co2_total/KG_VUELO:,.0f}</div><div class="equiv-label">Vuelos equivalentes</div></div>', unsafe_allow_html=True)
e3.markdown(f'<div class="equiv-card"><span class="equiv-icon">🚗</span><div class="equiv-num">{co2_total/KG_AUTO_KM/1000:,.0f}k</div><div class="equiv-label">KM auto promedio</div></div>', unsafe_allow_html=True)
e4.markdown(f'<div class="equiv-card"><span class="equiv-icon">🌿</span><div class="equiv-num">{ral_total*FACTOR_CO2:,.0f} kg</div><div class="equiv-label">CO2 Evitable</div></div>', unsafe_allow_html=True)

# Ranking y Gráfico histórico (mismo código que pasaste)
# ... [Insertar aquí el bloque de Ranking y plotly_chart de tu script original]
