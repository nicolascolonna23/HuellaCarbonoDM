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
    df_emi = pd.read_csv(f"{BASE_URL}&gid=882343299")
    df_kms = pd.read_csv(f"{BASE_URL}&gid=1044040871")

    def norm(df):
        df.columns = (df.columns.str.strip().str.upper()
                      .str.replace('Í','I').str.replace('Á','A')
                      .str.replace('É','E').str.replace('Ó','O'))
        m = {}
        for c in df.columns:
            if   "DOMINIO" in c:                              m[c] = "DOMINIO"
            elif "FECHA"   in c:                              m[c] = "FECHA"
            elif ("KM" in c or "DISTANCIA" in c) and "CO2" not in c and "L/100" not in c: m[c] = "KMS"
            elif "CO2"     in c or "EMISION" in c:           m[c] = "CO2"
            elif "RALENTI" in c:                              m[c] = "RALENTI"
            elif "MARCA"   in c:                              m[c] = "MARCA"
        df = df.rename(columns=m)
        for nc in ["KMS","CO2","RALENTI"]:
            if nc in df.columns:
                df[nc] = pd.to_numeric(
                    df[nc].astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),
                    errors='coerce').fillna(0)
        if 'DOMINIO' in df.columns:
            df['DOMINIO'] = df['DOMINIO'].astype(str).str.replace(' ','').str.upper()
        if 'FECHA' in df.columns:
            df['FECHA_DT'] = pd.to_datetime(df['FECHA'], dayfirst=True, errors='coerce')
            df['MES']      = df['FECHA_DT'].dt.strftime('%Y-%m')
        return df

    df_emi = norm(df_emi)
    df_kms = norm(df_kms)

    # Marca lookup
    marca_lk = (df_kms[['DOMINIO','MARCA']].dropna(subset=['MARCA'])
                .drop_duplicates('DOMINIO', keep='last')
                if 'MARCA' in df_kms.columns else pd.DataFrame(columns=['DOMINIO','MARCA']))

    cols_k = [c for c in ['DOMINIO','MES','KMS'] if c in df_kms.columns]
    df = df_emi.merge(df_kms[cols_k], on=['DOMINIO','MES'], how='left',
                      suffixes=('','_DROP'))
    df = df.loc[:, ~df.columns.str.contains('_DROP')]
    if 'KMS' in df.columns: df['KMS'] = df['KMS'].fillna(0)

    # MARCA
    if 'MARCA' not in df.columns or df['MARCA'].isna().all():
        df = df.drop(columns=['MARCA'], errors='ignore').merge(marca_lk, on='DOMINIO', how='left')
    else:
        df = df.merge(marca_lk.rename(columns={'MARCA':'_MF'}), on='DOMINIO', how='left')
        df['MARCA'] = df['MARCA'].fillna(df.get('_MF',''))
        df.drop(columns=['_MF'], errors='ignore', inplace=True)

    # Métricas derivadas
    df['CO2_RALENTI'] = df['RALENTI'] * FACTOR_CO2 if 'RALENTI' in df.columns else 0
    df['CO2_DIRECTO'] = np.maximum(df['CO2'] - df['CO2_RALENTI'], 0)
    df['INTENSIDAD']  = np.where(df['KMS']>0, df['CO2']/df['KMS']*1000, np.nan)  # g/km

    return df

# ── Carga ──────────────────────────────────────────────────────────────────────
try:
    df_master = get_data()
except Exception as e:
    st.error(f"Error al cargar datos: {e}")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/HuellaCarbonoDM/main/logo_diemar4.png", width=180)
    st.markdown("---")
    meses_disp = sorted(df_master['MES'].dropna().unique().tolist(), reverse=True)
    mes_sel = st.selectbox("📅 Período", meses_disp)
    marcas_disp = ["Todas"] + sorted(df_master['MARCA'].dropna().unique().tolist()) if 'MARCA' in df_master.columns else ["Todas"]
    marca_sel = st.selectbox("🚛 Marca", marcas_disp)
    st.markdown("---")
    st.markdown(f"<div style='font-size:.72rem;color:#4ade80;'>🔄 Actualización cada 2 min</div>", unsafe_allow_html=True)

# ── Filtro ─────────────────────────────────────────────────────────────────────
df = df_master[df_master['MES'] == mes_sel].copy()
if marca_sel != "Todas" and 'MARCA' in df.columns:
    df = df[df['MARCA'] == marca_sel]

# Mes anterior para delta
idx_mes = meses_disp.index(mes_sel)
mes_ant  = meses_disp[idx_mes + 1] if idx_mes + 1 < len(meses_disp) else None
df_ant   = df_master[df_master['MES'] == mes_ant].copy() if mes_ant else pd.DataFrame()
if marca_sel != "Todas" and not df_ant.empty and 'MARCA' in df_ant.columns:
    df_ant = df_ant[df_ant['MARCA'] == marca_sel]

def delta_html(curr, prev, invert=False):
    """Devuelve HTML del delta vs mes anterior."""
    if prev == 0 or pd.isna(prev): return '<span class="delta-flat">— sin dato prev.</span>'
    pct = (curr - prev) / abs(prev) * 100
    if abs(pct) < 0.5: return f'<span class="delta-flat">≈ igual al mes anterior</span>'
    up = pct > 0
    css = "delta-up" if (up and not invert) or (not up and invert) else "delta-down"
    arrow = "▲" if up else "▼"
    return f'<span class="{css}">{arrow} {abs(pct):.1f}% vs mes anterior</span>'

# ── Métricas globales ──────────────────────────────────────────────────────────
co2_total  = df['CO2'].sum()          if 'CO2'     in df.columns else 0
kms_total  = df['KMS'].sum()          if 'KMS'     in df.columns else 0
ral_total  = df['RALENTI'].sum()      if 'RALENTI' in df.columns else 0
co2_ral    = df['CO2_RALENTI'].sum()
intensidad = co2_total / kms_total * 1000 if kms_total > 0 else 0
arboles    = co2_total / ARBOL_KG_AÑO
vuelos     = co2_total / KG_VUELO
autos_km   = co2_total / KG_AUTO_KM

co2_ant  = df_ant['CO2'].sum()     if not df_ant.empty and 'CO2'     in df_ant.columns else 0
kms_ant  = df_ant['KMS'].sum()     if not df_ant.empty and 'KMS'     in df_ant.columns else 0
ral_ant  = df_ant['RALENTI'].sum() if not df_ant.empty and 'RALENTI' in df_ant.columns else 0
int_ant  = co2_ant / kms_ant * 1000 if kms_ant > 0 else 0

# ══════════════════════════════════════════════════════════════════════════════
#  RENDER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(CSS, unsafe_allow_html=True)

if df.empty:
    st.warning("Sin datos para el período y filtro seleccionados.")
    st.stop()

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-bottom:24px;">
  <div style="font-size:1.7rem;font-weight:800;color:#f0fdf4;letter-spacing:-.5px;">
    🌿 Carbon Tracker — {mes_sel}
  </div>
  <div style="font-size:.88rem;color:#6b9e70;margin-top:4px;">
    Flota Expreso Diemar · {df['DOMINIO'].nunique()} unidades activas
    {f"· Marca: {marca_sel}" if marca_sel != "Todas" else ""}
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPI row ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
kpis = [
    (k1, "💨", "CO2 Total",       f"{co2_total:,.0f} kg",    delta_html(co2_total, co2_ant, invert=True)),
    (k2, "🛣️", "KM Recorridos",   f"{kms_total:,.0f} km",    delta_html(kms_total, kms_ant)),
    (k3, "📈", "Intensidad",       f"{intensidad:.1f} g/km",  delta_html(intensidad, int_ant, invert=True)),
    (k4, "⏱️", "Combustible Idle", f"{ral_total:,.0f} L",     delta_html(ral_total, ral_ant, invert=True)),
]
for col, icon, label, val, dlt in kpis:
    col.markdown(f"""
    <div class="kpi-hero">
      <span class="kpi-icon">{icon}</span>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{val}</div>
      <div class="kpi-delta">{dlt}</div>
    </div>""", unsafe_allow_html=True)

# ── Equivalencias ──────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">Equivalencias ambientales</div>', unsafe_allow_html=True)
e1, e2, e3, e4 = st.columns(4)
equivs = [
    (e1, "🌳", f"{arboles:,.0f}", "árboles/año para compensar"),
    (e2, "✈️", f"{vuelos:,.0f}", "vuelos BsAs–Córdoba equivalentes"),
    (e3, "🚗", f"{autos_km/1000:,.0f} k", "km en auto promedio"),
    (e4, "🛢️", f"{co2_ral/co2_total*100:.1f}%" if co2_total > 0 else "—", "del CO2 fue por ralentí"),
]
for col, icon, num, label in equivs:
    col.markdown(f"""
    <div class="equiv-card">
      <span class="equiv-icon">{icon}</span>
      <div class="equiv-num">{num}</div>
      <div class="equiv-label">{label}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Gráficos principales ────────────────────────────────────────────────────────
col_izq, col_der = st.columns([1.6, 1])

with col_izq:
    st.markdown('<div class="sec-title">Ranking de emisiones por unidad</div>', unsafe_allow_html=True)
    rank = (df.groupby('DOMINIO').agg(CO2=('CO2','sum'), KMS=('KMS','sum'))
              .reset_index().sort_values('CO2', ascending=False))
    rank['INTENSIDAD'] = np.where(rank['KMS']>0, rank['CO2']/rank['KMS']*1000, 0)
    vmax = rank['CO2'].max()

    html_rank = '<div class="glass-card" style="padding:16px 20px;">'
    html_rank += ('<div style="display:flex;font-size:.68rem;color:#4ade80;font-weight:700;'
                  'text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">'
                  '<span style="width:26px;"></span>'
                  '<span style="width:90px;">Patente</span>'
                  '<span style="flex:1;margin:0 10px;">Proporción</span>'
                  '<span style="width:80px;text-align:right;">CO2 (kg)</span></div>')
    for i, (_, r) in enumerate(rank.iterrows(), 1):
        pct  = int(r['CO2'] / vmax * 100) if vmax > 0 else 0
        color = '#ef4444' if i == 1 else ('#f97316' if i == 2 else ('#f59e0b' if i <= 5 else '#4ade80'))
        html_rank += (f'<div class="rank-row">'
                      f'<div class="rank-num">#{i}</div>'
                      f'<div class="rank-dom">{r["DOMINIO"]}</div>'
                      f'<div class="rank-bg"><div class="rank-fill" style="width:{pct}%;background:{color};"></div></div>'
                      f'<div class="rank-val" style="color:{color};">{r["CO2"]:,.0f}</div>'
                      f'</div>')
    html_rank += '</div>'
    st.markdown(html_rank, unsafe_allow_html=True)

with col_der:
    st.markdown('<div class="sec-title">Origen del CO2</div>', unsafe_allow_html=True)
    co2_dir = co2_total - co2_ral
    fig_donut = go.Figure(go.Pie(
        labels=['Conducción directa', 'Ralentí (idle)'],
        values=[max(co2_dir, 0), co2_ral],
        hole=0.62,
        marker=dict(colors=['#4ade80','#f97316'],
                    line=dict(color='rgba(0,0,0,0)', width=0)),
        textinfo='label+percent',
        textfont=dict(color='#e2e8f0', size=11),
        hovertemplate='<b>%{label}</b><br>%{value:,.0f} kg CO2<extra></extra>'
    ))
    fig_donut.add_annotation(text=f"<b>{co2_total:,.0f}</b><br><span style='font-size:10'>kg CO2</span>",
                              x=0.5, y=0.5, showarrow=False,
                              font=dict(color='#f0fdf4', size=14))
    fig_donut.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, font=dict(color='#94a3b8', size=10)),
        margin=dict(l=0, r=0, t=20, b=40), height=300)
    st.plotly_chart(fig_donut, use_container_width=True)

    # Intensidad por marca
    if 'MARCA' in df.columns:
        st.markdown('<div class="sec-title">Intensidad por marca</div>', unsafe_allow_html=True)
        int_marca = (df[df['KMS']>0].groupby('MARCA')
                     .apply(lambda x: x['CO2'].sum() / x['KMS'].sum() * 1000)
                     .reset_index(name='g_km').sort_values('g_km'))
        fig_int = go.Figure(go.Bar(
            x=int_marca['g_km'], y=int_marca['MARCA'],
            orientation='h',
            marker=dict(color=['#4ade80','#f59e0b','#ef4444'][:len(int_marca)],
                        line=dict(color='rgba(0,0,0,0)', width=0)),
            text=int_marca['g_km'].apply(lambda v: f'{v:.1f}'),
            textposition='outside', textfont=dict(color='#e2e8f0', size=10),
            hovertemplate='<b>%{y}</b><br>%{x:.1f} g CO2/km<extra></extra>'
        ))
        fig_int.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#e2e8f0'), height=160,
            xaxis=dict(gridcolor='rgba(76,175,80,0.1)', tickfont=dict(color='#94a3b8', size=9),
                       title=dict(text='g CO2/km', font=dict(color='#6b9e70', size=9))),
            yaxis=dict(tickfont=dict(color='#94a3b8', size=10)),
            margin=dict(l=5, r=50, t=10, b=20))
        st.plotly_chart(fig_int, use_container_width=True)

# ── Tendencia histórica ────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">Tendencia histórica</div>', unsafe_allow_html=True)

hist = (df_master.groupby('MES').agg(
    CO2=('CO2','sum'), KMS=('KMS','sum'), RALENTI=('RALENTI','sum')
).reset_index().sort_values('MES'))
hist['INTENSIDAD'] = np.where(hist['KMS']>0, hist['CO2']/hist['KMS']*1000, np.nan)
hist['CO2_RALENTI'] = hist['RALENTI'] * FACTOR_CO2

fig_trend = go.Figure()
# Área CO2 total
fig_trend.add_trace(go.Scatter(
    x=hist['MES'], y=hist['CO2'],
    name='CO2 Total (kg)', fill='tozeroy',
    fillcolor='rgba(74,222,128,0.1)', line=dict(color='#4ade80', width=2.5),
    hovertemplate='%{x}<br>CO2: <b>%{y:,.0f} kg</b><extra></extra>'
))
# Área CO2 ralentí
fig_trend.add_trace(go.Scatter(
    x=hist['MES'], y=hist['CO2_RALENTI'],
    name='CO2 Ralentí (kg)', fill='tozeroy',
    fillcolor='rgba(249,115,22,0.15)', line=dict(color='#f97316', width=1.8, dash='dot'),
    hovertemplate='%{x}<br>CO2 idle: <b>%{y:,.0f} kg</b><extra></extra>'
))
# Intensidad (eje derecho)
fig_trend.add_trace(go.Scatter(
    x=hist['MES'], y=hist['INTENSIDAD'],
    name='Intensidad (g/km)', yaxis='y2',
    line=dict(color='#a78bfa', width=2, dash='dot'),
    marker=dict(size=5, color='#a78bfa'),
    hovertemplate='%{x}<br>Intensidad: <b>%{y:.1f} g/km</b><extra></extra>'
))
# Línea del mes seleccionado
fig_trend.add_vline(
    x=mes_sel, line_dash='dot', line_color='rgba(255,255,255,0.3)', line_width=1.5,
    annotation_text='▶ hoy', annotation_font_color='#94a3b8', annotation_font_size=10)

fig_trend.update_layout(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(5,26,10,0.4)',
    font=dict(color='#e2e8f0', family='Inter'),
    legend=dict(bgcolor='rgba(0,0,0,0)', bordercolor='rgba(76,175,80,0.2)',
                borderwidth=1, orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                font=dict(color='#94a3b8', size=10)),
    xaxis=dict(gridcolor='rgba(76,175,80,0.08)', linecolor='rgba(76,175,80,0.2)',
               tickfont=dict(color='#6b9e70', size=10), tickangle=-30),
    yaxis=dict(gridcolor='rgba(76,175,80,0.08)', tickfont=dict(color='#4ade80', size=10),
               title=dict(text='CO2 (kg)', font=dict(color='#4ade80', size=10))),
    yaxis2=dict(overlaying='y', side='right', tickfont=dict(color='#a78bfa', size=10),
                title=dict(text='g CO2/km', font=dict(color='#a78bfa', size=10)), showgrid=False),
    height=320, margin=dict(l=10, r=60, t=40, b=40), hovermode='x unified'
)
st.plotly_chart(fig_trend, use_container_width=True)

# ── Alertas top 3 peores ───────────────────────────────────────────────────────
st.markdown('<div class="sec-title">Unidades con mayor huella este período</div>', unsafe_allow_html=True)
top3 = rank.head(3)
al1, al2, al3 = st.columns(3)
for col, (_, r) in zip([al1, al2, al3], top3.iterrows()):
    arb_u = r['CO2'] / ARBOL_KG_AÑO
    int_u = r['INTENSIDAD']
    col.markdown(f"""
    <div class="alerta-box">
      <div style="font-size:.85rem;font-weight:800;color:#fca5a5;">🚛 {r['DOMINIO']}</div>
      <div style="font-size:1.4rem;font-weight:800;color:#ef4444;margin:4px 0;">{r['CO2']:,.0f} kg CO2</div>
      <div style="font-size:.75rem;color:#fca5a5;">
        🌳 Necesita <b>{arb_u:.0f} árboles/año</b><br>
        📈 Intensidad: <b>{int_u:.1f} g/km</b>
      </div>
    </div>""", unsafe_allow_html=True)

# ── Mejor unidad ───────────────────────────────────────────────────────────────
mejor = rank.tail(1).iloc[0] if len(rank) > 3 else None
if mejor is not None:
    col_m1, col_m2, col_m3 = st.columns([1, 2, 1])
    with col_m2:
        st.markdown(f"""
        <div class="ok-box" style="text-align:center;">
          <div style="font-size:.78rem;color:#86efac;font-weight:600;text-transform:uppercase;">
            ✅ Unidad más eficiente del período
          </div>
          <div style="font-size:1.5rem;font-weight:800;color:#4ade80;margin:4px 0;">
            {mejor['DOMINIO']}
          </div>
          <div style="font-size:.8rem;color:#86efac;">
            {mejor['CO2']:,.0f} kg CO2 · {mejor['INTENSIDAD']:.1f} g/km
            · 🌳 {mejor['CO2']/ARBOL_KG_AÑO:.0f} árboles/año
          </div>
        </div>""", unsafe_allow_html=True)

# ── Tabla detalle ──────────────────────────────────────────────────────────────
with st.expander("📋 Ver tabla completa del período"):
    cols_show = [c for c in ['DOMINIO','MARCA','FECHA','KMS','CO2','RALENTI','CO2_RALENTI','INTENSIDAD']
                 if c in df.columns]
    df_show = df[cols_show].copy()
    if 'INTENSIDAD' in df_show.columns: df_show['INTENSIDAD'] = df_show['INTENSIDAD'].round(1)
    if 'CO2_RALENTI' in df_show.columns: df_show['CO2_RALENTI'] = df_show['CO2_RALENTI'].round(1)
    st.dataframe(df_show, use_container_width=True, hide_index=True)

st.markdown(f"""
<div style="text-align:center;font-size:.72rem;color:#374151;margin-top:24px;padding:12px;">
  Expreso Diemar Carbon Tracker · Factor CO2 diesel: {FACTOR_CO2} kg/L
  · 1 árbol absorbe ~{ARBOL_KG_AÑO:.0f} kg CO2/año · Datos en tiempo real vía Google Sheets
</div>""", unsafe_allow_html=True)
