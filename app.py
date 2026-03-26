import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
# ... (mantener tus otros imports de engine)

# ─────────────────────────────────────────────
# CONFIGURACIÓN Y ESTÉTICA DARK
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Expreso Diemar - Fleet Analytics",
    page_icon="🚛",
    layout="wide",
)

# Inyectamos CSS para el fondo difuminado y modo oscuro
st.markdown(f"""
    <style>
    .stApp {{
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url("https://tu-url-de-imagen-de-camiones.jpg"); /* Reemplazar con URL de tu foto de flota */
        background-size: cover;
        background-attachment: fixed;
    }}
    .stMetric {{
        background-color: rgba(33, 37, 41, 0.7);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #444;
    }}
    [data-testid="stSidebar"] {{
        background-color: rgba(20, 20, 20, 0.95);
    }}
    h1, h2, h3, p {{
        color: white !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# NAVEGACIÓN (Portal de Emisiones)
# ─────────────────────────────────────────────
with st.sidebar:
    # Mostramos tu logo
    st.image("logo_diemar4.png", use_container_width=True)
    st.divider()
    
    # Selector de "Portal"
    paginas = ["📊 Desempeño de Flota", "🌿 Portal de Emisiones CO2"]
    seleccion = st.radio("Ir a:", paginas)
    
    st.divider()
    # ... (Tus filtros de Mes y Marca aquí)

# ─────────────────────────────────────────────
# LÓGICA DE PÁGINAS
# ─────────────────────────────────────────────

if seleccion == "📊 Desempeño de Flota":
    # --- AQUÍ VA TODO TU CÓDIGO ORIGINAL DEL DASHBOARD ---
    st.title("🚛 Fleet Analytics — Desempeño")
    # (Mover el código de KPIs, Ranking y Scatter aquí)

elif seleccion == "🌿 Portal de Emisiones CO2":
    st.title("🌿 Portal de Sustentabilidad - Expreso Diemar")
    st.markdown("Seguimiento de Huella de Carbono por Unidad")
    
    # KPIs de Emisiones
    c1, c2, c3 = st.columns(3)
    c1.metric("Emisiones Totales", f"{df['co2_kg'].sum():,.0f} kg CO2", delta_color="inverse")
    c2.metric("Promedio gCO2/km", f"{(df['co2_kg'].sum() / df['km'].sum() * 1000):.1f} g", delta_color="inverse")
    c3.metric("Unidad más Limpia", df.sort_values("co2_kg").iloc[0]["dominio"])

    st.divider()

    col_map, col_table = st.columns([1.5, 1])

    with col_map:
        # Gráfico de emisiones por Patente
        fig_co2 = px.bar(
            df.sort_values("co2_kg", ascending=False),
            x="dominio", y="co2_kg",
            color="co2_kg",
            title="CO2 Total por Patente (kg)",
            color_continuous_scale="Reds"
        )
        fig_co2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(fig_co2, use_container_width=True)

    with col_table:
        # Eficiencia de emisión (CO2 por KM)
        st.subheader("Eficiencia de Emisión")
        df["g_co2_km"] = (df["co2_kg"] / df["km"]) * 1000
        df_emisiones = df[["dominio", "marca", "km", "co2_kg", "g_co2_km"]].sort_values("g_co2_km")
        
        st.dataframe(df_emisiones.style.background_gradient(cmap="RdYlGn_r", subset=["g_co2_km"]), use_container_width=True)

    # Gráfico de burbujas: KM vs CO2
    fig_bubble = px.scatter(
        df, x="km", y="co2_kg", size="l_100km", color="marca",
        hover_name="dominio", title="Relación Distancia vs. Huella de Carbono",
        labels={"km": "Kilómetros Recorridos", "co2_kg": "CO2 Total (kg)"}
    )
    fig_bubble.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
    st.plotly_chart(fig_bubble, use_container_width=True)
