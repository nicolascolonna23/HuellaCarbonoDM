"""
FLEET ANALYTICS — Dashboard Interactivo
========================================
Ejecutar: streamlit run app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from engine import (
    cargar_telemetria, cargar_conduccion,
    combinar_y_calcular, calcular_score, detectar_anomalias,
    UMBRAL_ANOMALIA
)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Fleet Analytics",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

VERDE    = "#2e7d32"
AMARILLO = "#f57f17"
ROJO     = "#c62828"
AZUL     = "#1565c0"
GRIS     = "#546e7a"

# ─────────────────────────────────────────────
# CARGA DE DATOS (cacheado)
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)  # refresca cada 5 minutos
def cargar_todo():
    df_tel  = cargar_telemetria()
    df_cond = cargar_conduccion()
    df      = combinar_y_calcular(df_tel, df_cond)
    df      = calcular_score(df)
    df_anom = detectar_anomalias(df)
    df["mes_str"] = df["mes"].astype(str)
    return df, df_anom, df_tel


try:
    df_full, df_anom, df_tel = cargar_todo()
except Exception as e:
    st.error(f"❌ Error cargando datos: {e}")
    st.stop()

# ─────────────────────────────────────────────
# SIDEBAR — FILTROS
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3774/3774278.png", width=60)
    st.title("Fleet Analytics")
    st.caption("Dashboard de eficiencia de flota")
    st.divider()

    meses_disponibles = sorted(df_full["mes_str"].unique(), reverse=True)
    mes_sel = st.selectbox("📅 Mes", meses_disponibles,
                            help="Meses con datos de conducción disponibles")

    st.divider()
    marcas = ["Todas"] + sorted(df_full["marca"].dropna().unique().tolist())
    marca_sel = st.selectbox("🏭 Marca", marcas)

    st.divider()
    st.caption(f"Umbral anomalía: ±{UMBRAL_ANOMALIA}σ")
    st.caption("Actualiza datos: reemplazá los Excel y recargá la página")

# Filtrar por mes y marca
df = df_full[df_full["mes_str"] == mes_sel].copy()
if marca_sel != "Todas":
    df = df[df["marca"] == marca_sel]

df_anom_mes = df_anom[df_anom["mes"] == mes_sel] if not df_anom.empty else pd.DataFrame()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown(f"## 🚛 Fleet Analytics — {mes_sel}")
if marca_sel != "Todas":
    st.caption(f"Filtrado: {marca_sel}")

# ─────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)

km_total   = df["km"].sum()
lts_total  = df["litros"].sum()
l100_avg   = df["l_100km"].mean()
co2_total  = df["co2_kg"].sum()
ralenti_avg = df["pct_ralenti"].mean()

col1.metric("🛣️ Km Totales",      f"{km_total:,.0f}")
col2.metric("⛽ Litros Consumidos", f"{lts_total:,.0f}")
col3.metric("📊 L/100km Promedio", f"{l100_avg:.1f}")
col4.metric("🌿 CO₂ Total (kg)",   f"{co2_total:,.0f}")
col5.metric("⏸️ % Ralentí Prom.", f"{ralenti_avg:.1f}%" if not np.isnan(ralenti_avg) else "N/D")

st.divider()

# ─────────────────────────────────────────────
# FILA 1: RANKING + SCATTER
# ─────────────────────────────────────────────
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("🏆 Ranking de Eficiencia")

    df_rank = df.sort_values("ranking")

    def color_score_bar(score):
        if pd.isna(score):
            return GRIS
        if score >= 70:
            return VERDE
        elif score >= 40:
            return AMARILLO
        return ROJO

    colors = [color_score_bar(s) for s in df_rank["score"]]

    fig_rank = go.Figure(go.Bar(
        x=df_rank["score"],
        y=df_rank["dominio"],
        orientation="h",
        marker_color=colors,
        text=[f"{s:.0f}" if not pd.isna(s) else "N/D" for s in df_rank["score"]],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Score: %{x:.1f}<br>"
            "L/100km: %{customdata[0]:.1f}<br>"
            "%Ralentí: %{customdata[1]:.1f}%<extra></extra>"
        ),
        customdata=df_rank[["l_100km", "pct_ralenti"]].fillna(0).values
    ))

    fig_rank.update_layout(
        height=420,
        margin=dict(l=10, r=60, t=20, b=20),
        xaxis=dict(range=[0, 115], title="Score (0-100)"),
        yaxis=dict(autorange="reversed", title=""),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    fig_rank.add_vline(x=70, line_dash="dot", line_color=VERDE, opacity=0.5)
    fig_rank.add_vline(x=40, line_dash="dot", line_color=AMARILLO, opacity=0.5)

    st.plotly_chart(fig_rank, use_container_width=True)

with col_right:
    st.subheader("📍 Consumo vs. Ralentí")
    st.caption("Burbuja = km recorridos | ideal: abajo-izquierda")

    df_scatter = df.dropna(subset=["l_100km", "pct_ralenti"])

    fig_scatter = px.scatter(
        df_scatter,
        x="pct_ralenti",
        y="l_100km",
        size="km",
        color="score",
        color_continuous_scale=[(0, ROJO), (0.4, AMARILLO), (0.7, VERDE), (1, "#1b5e20")],
        hover_name="dominio",
        hover_data={
            "marca": True,
            "km": ":,.0f",
            "litros": ":,.0f",
            "score": ":.1f",
            "l_100km": ":.2f",
            "pct_ralenti": ":.2f",
        },
        labels={
            "pct_ralenti": "% Combustible en Ralentí",
            "l_100km": "L/100km",
            "score": "Score",
        },
        size_max=40,
    )

    fig_scatter.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=20, b=20),
        coloraxis_colorbar=dict(title="Score", len=0.6),
        plot_bgcolor="#f9f9f9",
        paper_bgcolor="white",
    )
    fig_scatter.update_traces(
        texttemplate="%{hovertext}",
        textfont_size=9,
        mode="markers+text",
        textposition="top center",
    )

    st.plotly_chart(fig_scatter, use_container_width=True)

# ─────────────────────────────────────────────
# FILA 2: MÉTRICAS DETALLE + ANOMALÍAS
# ─────────────────────────────────────────────
col_a, col_b = st.columns([1.5, 1])

with col_a:
    st.subheader("📋 Detalle por Camión")

    cols_show = {
        "ranking": "Rank",
        "dominio": "Dominio",
        "marca": "Marca",
        "score": "Score",
        "l_100km": "L/100km",
        "pct_ralenti": "% Ralentí",
        "lts_ralenti": "Lts Ralentí",
        "km": "Km",
        "litros": "Litros",
        "co2_kg": "CO₂ (kg)",
        "hs_motor": "Hs Motor",
        "score_nota": "Datos",
    }
    df_display = df.sort_values("ranking")[list(cols_show.keys())].rename(columns=cols_show)

    def highlight_score(row):
        score = row["Score"]
        if pd.isna(score):
            color = "#f5f5f5"
        elif score >= 70:
            color = "#e8f5e9"
        elif score >= 40:
            color = "#fff9c4"
        else:
            color = "#ffebee"
        return [f"background-color: {color}"] * len(row)

    st.dataframe(
        df_display.style.apply(highlight_score, axis=1)
            .format({
                "Score": "{:.1f}",
                "L/100km": "{:.2f}",
                "% Ralentí": lambda x: f"{x:.1f}%" if pd.notna(x) else "N/D",
                "Km": "{:,.0f}",
                "Litros": "{:,.0f}",
                "CO₂ (kg)": "{:,.0f}",
                "Hs Motor": "{:.1f}",
                "Lts Ralentí": lambda x: f"{x:.0f}" if pd.notna(x) else "N/D",
            }),
        use_container_width=True,
        height=380,
    )

with col_b:
    st.subheader("⚠️ Alertas del Período")

    if df_anom_mes.empty:
        st.success("✅ No se detectaron anomalías en este período.")
    else:
        for _, row in df_anom_mes.iterrows():
            delta = row["valor"] - row["media_flota"]
            pct   = (delta / row["media_flota"] * 100) if row["media_flota"] != 0 else 0
            with st.container():
                st.error(
                    f"**{row['dominio']}** — {row['tipo']}\n\n"
                    f"Valor: **{row['valor']:.1f}** | "
                    f"Media flota: {row['media_flota']:.1f} | "
                    f"Desvío: **+{pct:.0f}%** ({row['desvios']:.1f}σ)"
                )

    st.divider()
    st.subheader("📊 Distribución L/100km")

    fig_hist = px.histogram(
        df, x="l_100km", nbins=10,
        color_discrete_sequence=[AZUL],
        labels={"l_100km": "L/100km"},
    )
    mean_val = df["l_100km"].mean()
    fig_hist.add_vline(x=mean_val, line_dash="dash", line_color=ROJO,
                       annotation_text=f"Media: {mean_val:.1f}")
    fig_hist.update_layout(
        height=220,
        margin=dict(l=10, r=10, t=10, b=30),
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

st.divider()

# ─────────────────────────────────────────────
# FILA 3: EVOLUCIÓN HISTÓRICA (telemetría)
# ─────────────────────────────────────────────
st.subheader("📈 Evolución Histórica — L/100km por Camión (Telemetría)")
st.caption("Incluye todos los meses disponibles en ANALISIS CONSUMO.xlsx")

dominios_hist = sorted(df_full["dominio"].unique().tolist())
sel_hist = st.multiselect(
    "Seleccioná camiones",
    dominios_hist,
    default=dominios_hist[:6],
    key="hist_select"
)

df_hist = df_tel[df_tel["dominio"].isin(sel_hist)].copy()
df_hist["mes_str"] = df_hist["mes"].astype(str)

if not df_hist.empty:
    fig_hist2 = px.line(
        df_hist.sort_values("mes_str"),
        x="mes_str",
        y="l_100km",
        color="dominio",
        markers=True,
        labels={"mes_str": "Mes", "l_100km": "L/100km", "dominio": "Camión"},
    )
    fig_hist2.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(tickangle=-45),
        hovermode="x unified",
    )
    st.plotly_chart(fig_hist2, use_container_width=True)
else:
    st.info("Seleccioná al menos un camión para ver la evolución histórica.")

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.divider()
st.caption(
    "Fleet Analytics · Datos: ANALISIS CONSUMO.xlsx + DATOS-EXTRA-CONDUCCION.xlsx · "
    f"Período con datos conducción: {', '.join(meses_disponibles)}"
)
