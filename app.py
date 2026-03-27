import streamlit as st
import pandas as pd
import requests
import io

# 1. ESTÉTICA Y CONFIGURACIÓN (Siguiendo Identidad Institucional)
st.set_page_config(page_title="Expreso Diemar - Carbon Tracker", layout="wide")

# Estilo con colores de marca: Verde y Azul [cite: 84]
st.markdown("""
    <style>
    .stMetric { border-left: 5px solid #2e7d32; background-color: rgba(255, 255, 255, 0.05); padding: 15px; }
    h1, h2, h3 { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CARGA DE DATOS CON LIMPIEZA PROFUNDA
@st.cache_data(ttl=60)
def get_clean_data():
    # Fuente de Google Sheets Publicada
    base_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR35NkYPtJrOrdYHLGUH7GIW93s5cPAqQ0zEk5fP1c3gvErwbUW7HJ2OeWBYaBVsYKVmCf0yhLvs6eG/pub?output=csv"
    
    # Descarga de Telemetría (Hoja 1) y Unidades (Hoja 2)
    df_tel = pd.read_csv(f"{base_url}&gid=1044040871")
    df_uni = pd.read_csv(f"{base_url}&gid=882343299")
    
    def procesar_hoja(df):
        # Normalizar nombres de columnas a MAYÚSCULAS y sin tildes 
        df.columns = df.columns.str.strip().str.upper().str.replace('Í', 'I').str.replace('Á', 'A')
        
        # Diccionario de búsqueda inteligente
        mapeo = {
            "DOMINIO": "DOMINIO", "FECHA": "FECHA", 
            "DISTANCIA": "KMS", "KM": "KMS",
            "EMISIONES": "CO2", "CO2": "CO2",
            "RALENTI": "RALENTI", "MARCA": "MARCA"
        }
        
        for col in df.columns:
            for clave, nuevo in mapeo.items():
                if clave in col:
                    df = df.rename(columns={col: nuevo})
        
        # --- SOLUCIÓN AL TYPEERROR ---
        # Convertimos a texto, quitamos puntos de miles, cambiamos comas por puntos y a número.
        # Si falla (errors='coerce'), pone un 0 en lugar de romper la app.
        for col_val in ["KMS", "CO2", "RALENTI"]:
            if col_val in df.columns:
                df[col_val] = pd.to_numeric(
                    df[col_val].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), 
                    errors='coerce'
                ).fillna(0)
        
        return df

    df_tel = procesar_hoja(df_tel)
    df_uni = procesar_hoja(df_uni)

    # Preparar unión (Merge)
    for d in [df_tel, df_uni]:
        if 'FECHA' in d.columns:
            d['FECHA_DT'] = pd.to_datetime(d['FECHA'], errors='coerce')
            d['MES'] = d['FECHA_DT'].dt.strftime('%Y-%m')
        if 'DOMINIO' in d.columns:
            d['DOMINIO'] = d['DOMINIO'].astype(str).str.replace(' ', '').str.upper()

    # Unión por Patente y Mes
    return pd.merge(df_tel, df_uni, on=["DOMINIO", "MES"], suffixes=('', '_DROP')).filter(regex='^(?!.*_DROP)')

try:
    df_master = get_clean_data()
except Exception as e:
    st.error(f"Error técnico: {e}")
    st.stop()

# 3. DASHBOARD Y MÉTRICAS
st.title("🚛 Panel de Control - Expreso Diemar")

meses = sorted(df_master["MES"].unique().tolist(), reverse=True)
mes_sel = st.sidebar.selectbox("Seleccionar Período", meses)
df_f = df_master[df_master["MES"] == mes_sel]

if not df_f.empty:
    c1, c2, c3 = st.columns(3)
    
    # Las sumas ahora son seguras porque forzamos el tipo float arriba
    v_co2 = df_f['CO2'].sum()
    v_kms = df_f['KMS'].sum()
    v_ral = df_f['RALENTI'].sum()

    c1.metric("CO₂ EMITIDO (KG)", f"{v_co2:,.0f}")
    c2.metric("KM RECORRIDOS", f"{v_kms:,.0f}")
    c3.metric("RALENTÍ (LTS)", f"{v_ral:,.1f}")

    st.divider()
    st.subheader("📋 Detalle de Unidades")
    st.dataframe(df_f[['DOMINIO', 'MARCA', 'KMS', 'CO2', 'RALENTI']], use_container_width=True)
else:
    st.warning("No hay datos disponibles para el mes seleccionado.")
