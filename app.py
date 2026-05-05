import streamlit as st
import pandas as pd
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
.sec-title {
    font-size: 1rem; font-weight: 700; color: #a7f3d0;
    text-transform: uppercase; letter-spacing: .8px;
    border-left: 3px solid #2e7d32; padding-left: 10px;
    margin: 20px 0 14px;
}
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
.rank-row { display:flex; align-items:center; padding:9px 0; border-bottom:1px solid rgba(76,175,80,0.1); }
.rank-num  { width:26px; font-size:.85rem; font-weight:700; color:#6b9e70; }
.rank-dom  { width:90px; font-size:.85rem; font-weight:700; color:#e2e8f0; }
.rank-bg   { flex:1; height:8px; background:rgba(255,255,255,0.06); border-radius:4px; margin:0 10px; overflow:hidden; }
.rank-fill { height:8px; border-radius:4px; }
.rank-val  { font-size:.82rem; font-weight:700; width:80px; text-align:right; }
footer { display: none !important; }
.stMarkdown p, .stMarkdown span { color: #e2e8f0 !important; }
</style>
"""

# ══════════════════════════════════════════════════════════════════════════════
#  DATOS
# ══════════════════════════════════════════════════════════════════════════════
SHEET_ID = "1u7cckay0IJ60bfoKk2OZo-TjCvTbH9O1wKxNFdSKDCQ"
BASE_URL  = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=120)
def get_data():
    # Usar el tab TELEMETRIA (gid=0) — fuente única con todos los datos al día
    df = pd.read_csv(f"{BASE_URL}&gid=0")

    def parse_num(s):
        return pd.to_numeric(
            s.astype(str)
             .str.replace(r'\s', '', regex=True)
             .str.replace('.', '', regex=False)
             .str.replace(',', '.', regex=False),
            errors='coerce'
        ).fillna(0)

    # Normalizar columnas
    df.columns = (df.columns.str.strip().str.upper()
                  .str.replace('Í','I').str.replace('Á','A')
                  .str.replace('É','E').str.replace('Ó','O').str.replace('Ú','U'))

    # Mapeo: primera columna que coincide por destino
    m, usados = {}, set()
    for c in df.columns:
        if   "DOMINIO"  in c and "DOMINIO"  not in usados: m[c]="DOMINIO";  usados.add("DOMINIO")
        elif "FECHA"    in c and "FECHA"    not in usados: m[c]="FECHA";    usados.add("FECHA")
        elif "MARCA"    in c and "MARCA"    not in usados: m[c]="MARCA";    usados.add("MARCA")
        elif ("RALENTI" in c or "IDLE" in c) and "RALENTI" not in usados: m[c]="RALENTI"; usados.add("RALENTI")
        elif ("DISTANCIA" in c or ("KM" in c and "100" not in c and "CONSUMO" not in c)) and "LITRO" not in c and "KMS" not in usados:
            m[c]="KMS"; usados.add("KMS")
        elif ("LITRO" in c or "LTS" in c or "CONSUMID" in c) and "100" not in c and "LITROS" not in usados:
            m[c]="LITROS"; usados.add("LITROS")
    df = df.rename(columns=m)

    # Parsear numéricos
    for col in ["KMS", "LITROS", "RALENTI"]:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = parse_num(df[col])

    # DOMINIO limpio
    if 'DOMINIO' in df.columns:
        df['DOMINIO'] = df['DOMINIO'].astype(str).str.strip().str.upper()
        df = df[df['DOMINIO'].str.match(r'^[A-Z]{2}\d{3}[A-Z]{2}$|^[A-Z]{2}\d{3}[A-Z]{3}$', na=False)]

    # Fechas → MES
    if 'FECHA' in df.columns:
        df['FECHA_DT'] = pd.to_datetime(df['FECHA'], dayfirst=True, errors='coerce')
        df['MES'] = df['FECHA_DT'].dt.strftime('%Y-%m')

    # CO2 calculado desde litros
    df['CO2'] = df['LITROS'] * FACTOR_CO2

    # MARCA fallback
    if 'MARCA' not in df.columns:
        df['MARCA'] = 'Sin marca'

    # Agregar a nivel mensual por unidad
    agg_cols = {'CO2': 'sum', 'KMS': 'sum', 'LITROS': 'sum', 'RALENTI': 'sum', 'MARCA': 'first'}
    agg_cols = {k: v for k, v in agg_cols.items() if k in df.columns}
    df = (df.dropna(subset=['DOMINIO','MES'])
            .groupby(['DOMINIO','MES'], as_index=False)
            .agg(agg_cols))

    # Métricas derivadas
    df['CO2_RALENTI'] = df['RALENTI'] * FACTOR_CO2
    df['CO2_DIRECTO'] = np.maximum(df['CO2'] - df['CO2_RALENTI'], 0)
    df['INTENSIDAD']  = np.where(df['KMS'] > 0, df['CO2'] / df['KMS'] * 1000, 0)

    return df

# ── Carga ──────────────────────────────────────────────────────────────────────
try:
    df_master = get_data()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://raw.githubusercontent.com/nicolascolonna23/HuellaCarbonoDM/main/logo_diemar4.png", width=180)
    st.markdown("---")
    meses = sorted(df_master['MES'].dropna().unique().tolist())
    n = len(meses)
    st.markdown("<div style='font-size:.8rem;color:#6b9e70;font-weight:600;'>📅 Período</div>", unsafe_allow_html=True)
    mes_desde = st.selectbox("Desde", meses, index=0)
    mes_hasta = st.selectbox("Hasta", meses, index=n - 1)
    if mes_desde > mes_hasta:
        mes_desde, mes_hasta = mes_hasta, mes_desde

    marcas_lista = sorted(df_master['MARCA'].dropna().unique().tolist())
    marcas_lista = [m for m in marcas_lista if m and m != 'Sin marca']
    marca_sel = st.selectbox("🚛 Marca", ["Todas"] + marcas_lista)
    st.markdown("---")
    st.markdown("<div style='font-size:.72rem;color:#4ade80;'>🔄 Actualización cada 2 min</div>", unsafe_allow_html=True)

# ── Filtro ─────────────────────────────────────────────────────────────────────
df = df_master[(df_master['MES'] >= mes_desde) & (df_master['MES'] <= mes_hasta)].copy()
if marca_sel != "Todas":
    df = df[df['MARCA'] == marca_sel]

# Período anterior para delta
todos_meses = sorted(df_master['MES'].dropna().unique().tolist())
idx_desde   = todos_meses.index(mes_desde) if mes_desde in todos_meses else 0
n_rango     = max(len([m for m in todos_meses if mes_desde <= m <= mes_hasta]), 1)
if idx_desde >= n_rango:
    ant_desde = todos_meses[max(0, idx_desde - n_rango)]
    ant_hasta = todos_meses[idx_desde - 1]
    df_ant = df_master[(df_master['MES'] >= ant_desde) & (df_master['MES'] <= ant_hasta)].copy()
    if marca_sel != "Todas":
        df_ant = df_ant[df_ant['MARCA'] == marca_sel]
else:
    df_ant = pd.DataFrame()

def delta_html(curr, prev, invert=False):
    if not df_ant.empty and prev > 0:
        pct = (curr - prev) / abs(prev) * 100
        if abs(pct) < 0.5:
            return '<span style="color:#94a3b8;font-size:.74rem;">≈ igual período anterior</span>'
        up  = pct > 0
        bad = (up and not invert) or (not up and invert)
        col = '#ef4444' if bad else '#4ade80'
        arr = '▲' if up else '▼'
        return f'<span style="color:{col};font-size:.74rem;">{arr} {abs(pct):.1f}% vs período ant.</span>'
    return '<span style="color:#94a3b8;font-size:.74rem;">— sin dato prev.</span>'

# ── Métricas globales ──────────────────────────────────────────────────────────
co2_t  = df['CO2'].sum()
kms_t  = df['KMS'].sum()
ral_t  = df['RALENTI'].sum()
co2r_t = df['CO2_RALENTI'].sum()
int_t  = co2_t / kms_t * 1000 if kms_t > 0 else 0

co2_a  = df_ant['CO2'].sum()    if not df_ant.empty else 0
kms_a  = df_ant['KMS'].sum()    if not df_ant.empty else 0
ral_a  = df_ant['RALENTI'].sum() if not df_ant.empty else 0
int_a  = co2_a / kms_a * 1000  if kms_a > 0 else 0

periodo_label = mes_desde if mes_desde == mes_hasta else f"{mes_desde} → {mes_hasta}"

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
    🌿 Carbon Tracker — {periodo_label}
  </div>
  <div style="font-size:.88rem;color:#6b9e70;margin-top:4px;">
    Flota Expreso Diemar · {df['DOMINIO'].nunique()} unidades activas
    {f"· Marca: {marca_sel}" if marca_sel != "Todas" else ""}
  </div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ───────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
for col, icon, label, val, dlt in [
    (k1, "💨", "CO2 Total",       f"{co2_t:,.0f} kg",   delta_html(co2_t,  co2_a, invert=True)),
    (k2, "🛣️", "KM Recorridos",   f"{kms_t:,.0f} km",   delta_html(kms_t,  kms_a)),
    (k3, "📈", "Intensidad",       f"{int_t:.1f} g/km",  delta_html(int_t,  int_a, invert=True)),
    (k4, "⏱️", "Combustible Idle", f"{ral_t:,.0f} L",    delta_html(ral_t,  ral_a, invert=True)),
]:
    col.markdown(f"""
    <div class="kpi-hero">
      <span class="kpi-icon">{icon}</span>
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{val}</div>
      <div style="margin-top:6px;">{dlt}</div>
    </div>""", unsafe_allow_html=True)

# ── Equivalencias ──────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">Equivalencias ambientales</div>', unsafe_allow_html=True)
e1, e2, e3, e4 = st.columns(4)
for col, icon, num, label in [
    (e1, "🌳", f"{co2_t/ARBOL_KG_AÑO:,.0f}",      "árboles/año para compensar"),
    (e2, "✈️", f"{co2_t/KG_VUELO:,.0f}",           "vuelos BsAs–Córdoba equivalentes"),
    (e3, "🚗", f"{co2_t/KG_AUTO_KM/1000:,.0f} k",  "km en auto promedio"),
    (e4, "🌿", f"{co2r_t:,.0f} kg",                "CO2 evitable (por ralentí)"),
]:
    col.markdown(f"""
    <div class="equiv-card">
      <span class="equiv-icon">{icon}</span>
      <div class="equiv-num">{num}</div>
      <div class="equiv-label">{label}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Ranking + Donut ────────────────────────────────────────────────────────────
col_izq, col_der = st.columns([1.6, 1])

with col_izq:
    st.markdown('<div class="sec-title">Ranking de emisiones por unidad</div>', unsafe_allow_html=True)
    rank = (df.groupby('DOMINIO')
              .agg(CO2=('CO2','sum'), KMS=('KMS','sum'))
              .reset_index()
              .sort_values('CO2', ascending=False))
    rank['INTENSIDAD'] = np.where(rank['KMS'] > 0, rank['CO2'] / rank['KMS'] * 1000, 0)
    vmax = rank['CO2'].max() or 1

    html_rank = '<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(76,175,80,0.2);border-radius:16px;padding:16px 20px;">'
    html_rank += ('<div style="display:flex;font-size:.68rem;color:#4ade80;font-weight:700;'
                  'text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;">'
                  '<span style="width:26px;"></span>'
                  '<span style="width:90px;">Patente</span>'
                  '<span style="flex:1;margin:0 10px;">Proporción</span>'
                  '<span style="width:80px;text-align:right;">CO2 (kg)</span></div>')
    for i, (_, r) in enumerate(rank.iterrows(), 1):
        pct   = int(r['CO2'] / vmax * 100)
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
    co2_dir = max(co2_t - co2r_t, 0)
    fig_donut = go.Figure(go.Pie(
        labels=['Conducción directa', 'Ralentí (idle)'],
        values=[co2_dir, co2r_t],
        hole=0.62,
        marker=dict(colors=['#4ade80','#f97316'],
                    line=dict(color='rgba(0,0,0,0)', width=0)),
        textinfo='label+percent',
        textfont=dict(color='#e2e8f0', size=11),
        hovertemplate='<b>%{label}</b><br>%{value:,.0f} kg CO2<extra></extra>'
    ))
    fig_donut.add_annotation(
        text=f"<b>{co2_t:,.0f}</b><br><span style='font-size:10'>kg CO2</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(color='#f0fdf4', size=14))
    fig_donut.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e8f0'),
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, font=dict(color='#94a3b8', size=10)),
        margin=dict(l=0, r=0, t=20, b=40), height=300)
    st.plotly_chart(fig_donut, use_container_width=True)

    # Intensidad por marca
    df_int = df[df['KMS'] > 0]
    if 'MARCA' in df_int.columns and not df_int.empty:
        st.markdown('<div class="sec-title">Intensidad por marca</div>', unsafe_allow_html=True)
        int_marca = (df_int.groupby('MARCA')
                     .apply(lambda x: x['CO2'].sum() / x['KMS'].sum() * 1000)
                     .rename('g_km').reset_index().sort_values('g_km'))
        if not int_marca.empty:
            colors_int = ['#4ade80','#f59e0b','#ef4444']
            fig_int = go.Figure(go.Bar(
                x=int_marca['g_km'], y=int_marca['MARCA'],
                orientation='h',
                marker=dict(color=colors_int[:len(int_marca)],
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
hist = (df_master.groupby('MES')
        .agg(CO2=('CO2','sum'), KMS=('KMS','sum'), RALENTI=('RALENTI','sum'))
        .reset_index().sort_values('MES'))
hist['INTENSIDAD']  = np.where(hist['KMS'] > 0, hist['CO2'] / hist['KMS'] * 1000, np.nan)
hist['CO2_RALENTI'] = hist['RALENTI'] * FACTOR_CO2

fig_trend = go.Figure()
fig_trend.add_trace(go.Scatter(
    x=hist['MES'], y=hist['CO2'],
    name='CO2 Total (kg)', fill='tozeroy',
    fillcolor='rgba(74,222,128,0.1)', line=dict(color='#4ade80', width=2.5),
    hovertemplate='%{x}<br>CO2: <b>%{y:,.0f} kg</b><extra></extra>'
))
fig_trend.add_trace(go.Scatter(
    x=hist['MES'], y=hist['CO2_RALENTI'],
    name='CO2 Ralentí (kg)', fill='tozeroy',
    fillcolor='rgba(249,115,22,0.15)', line=dict(color='#f97316', width=1.8, dash='dot'),
    hovertemplate='%{x}<br>CO2 idle: <b>%{y:,.0f} kg</b><extra></extra>'
))
fig_trend.add_trace(go.Scatter(
    x=hist['MES'], y=hist['INTENSIDAD'],
    name='Intensidad (g/km)', yaxis='y2',
    line=dict(color='#a78bfa', width=2, dash='dot'),
    marker=dict(size=5, color='#a78bfa'),
    hovertemplate='%{x}<br>Intensidad: <b>%{y:.1f} g/km</b><extra></extra>'
))
# Líneas del rango seleccionado
fig_trend.add_vline(x=mes_desde, line_dash='dot', line_color='rgba(255,255,255,0.3)', line_width=1.5)
if mes_hasta != mes_desde:
    fig_trend.add_vline(x=mes_hasta, line_dash='dot', line_color='rgba(255,255,255,0.3)', line_width=1.5)

fig_trend.update_layout(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(5,26,10,0.4)',
    font=dict(color='#e2e8f0', family='Inter'),
    legend=dict(bgcolor='rgba(0,0,0,0)', orientation='h',
                yanchor='bottom', y=1.02, xanchor='right', x=1,
                font=dict(color='#94a3b8', size=10)),
    xaxis=dict(gridcolor='rgba(76,175,80,0.08)', tickfont=dict(color='#6b9e70', size=10), tickangle=-30),
    yaxis=dict(gridcolor='rgba(76,175,80,0.08)', tickfont=dict(color='#4ade80', size=10),
               title=dict(text='CO2 (kg)', font=dict(color='#4ade80', size=10))),
    yaxis2=dict(overlaying='y', side='right', tickfont=dict(color='#a78bfa', size=10),
                title=dict(text='g CO2/km', font=dict(color='#a78bfa', size=10)), showgrid=False),
    height=320, margin=dict(l=10, r=60, t=40, b=40), hovermode='x unified'
)
st.plotly_chart(fig_trend, use_container_width=True)

# ── Top 3 peores ───────────────────────────────────────────────────────────────
st.markdown('<div class="sec-title">Unidades con mayor huella este período</div>', unsafe_allow_html=True)
top3 = rank.head(3)
al1, al2, al3 = st.columns(3)
for col, (_, r) in zip([al1, al2, al3], top3.iterrows()):
    col.markdown(f"""
    <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.35);
                border-radius:12px;padding:14px 18px;margin-bottom:10px;">
      <div style="font-size:.85rem;font-weight:800;color:#fca5a5;">🚛 {r['DOMINIO']}</div>
      <div style="font-size:1.4rem;font-weight:800;color:#ef4444;margin:4px 0;">{r['CO2']:,.0f} kg CO2</div>
      <div style="font-size:.75rem;color:#fca5a5;">
        🌳 Necesita <b>{r['CO2']/ARBOL_KG_AÑO:.0f} árboles/año</b><br>
        📈 Intensidad: <b>{r['INTENSIDAD']:.1f} g/km</b>
      </div>
    </div>""", unsafe_allow_html=True)

# ── Tabla detalle ──────────────────────────────────────────────────────────────
with st.expander("📋 Ver tabla completa del período"):
    cols_show = [c for c in ['DOMINIO','MARCA','MES','KMS','CO2','RALENTI','CO2_RALENTI','INTENSIDAD']
                 if c in df.columns]
    df_show = df[cols_show].copy()
    for c in ['INTENSIDAD','CO2_RALENTI']:
        if c in df_show.columns:
            df_show[c] = df_show[c].round(1)
    st.dataframe(df_show.sort_values('CO2', ascending=False),
                 use_container_width=True, hide_index=True)

st.markdown(f"""
<div style="text-align:center;font-size:.72rem;color:#374151;margin-top:24px;padding:12px;">
  Expreso Diemar Carbon Tracker · Factor CO2 diesel: {FACTOR_CO2} kg/L
  · 1 árbol absorbe ~{ARBOL_KG_AÑO:.0f} kg CO2/año · Datos en tiempo real vía Google Sheets
</div>""", unsafe_allow_html=True)
