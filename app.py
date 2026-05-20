import streamlit as st
import pandas as pd
import plotly.express as px
import os
from db_connection import get_portfolio_data, register_transaction
from market_data import get_current_prices, get_recent_earnings
from sec_downloader import download_sec_report

# Configuración de la página (Debe ser la primera llamada a Streamlit)
st.set_page_config(
    page_title="Monitor de Portafolio",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para una estética premium (Dark Mode)
st.markdown("""
<style>
    /* Fondo principal y tipografía */
    .stApp {
        background-color: #0E1117;
        font-family: 'Inter', sans-serif;
    }
    
    /* Títulos */
    h1, h2, h3 {
        color: #F8F9FA !important;
        font-weight: 600;
    }
    
    /* Contenedores de métricas tipo tarjetas Glassmorphism */
    div[data-testid="metric-container"] {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        background: rgba(255, 255, 255, 0.08);
    }
    
    /* Textos oscuros a azul claro */
    p, label, span {
        color: #ADD8E6 !important;
    }
    
    /* Etiquetas de las métricas */
    div[data-testid="metric-container"] label,
    div[data-testid="stMetricLabel"] * {
        color: #ADD8E6 !important;
        font-size: 1.1rem;
    }
    
    /* Valores de las métricas */
    div[data-testid="metric-container"] div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {
        color: #FFFFFF !important;
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* Mantener deltas con su color original (verde/rojo) */
    div[data-testid="stMetricDelta"] *, div[data-testid="stMetricDelta"] svg {
        color: inherit !important;
    }
    
    /* Tablas */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* Barra lateral en negro con contraste premium */
    section[data-testid="stSidebar"] {
        background-color: #000000 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    section[data-testid="stSidebar"] > div {
        background-color: #000000 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stForm"] {
        background-color: #0A0A0A !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px;
    }

    /* Header superior en negro */
    header[data-testid="stHeader"] {
        background-color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# Título y Logo
st.logo("Itzam_Logo.png")
col_logo, col_titulo = st.columns([1, 11])
with col_logo:
    st.image("Itzam_Logo.png", width=120)
with col_titulo:
    st.title("Monitor de Portafolio de Inversiones")
st.markdown("Panel de control en tiempo real conectado a Oracle OCI y Yahoo Finance.")

# Botón de actualización
if st.button("🔄 Actualizar Datos"):
    st.rerun()

# --- FORMULARIO DE REGISTRO EN SIDEBAR ---
with st.sidebar:
    st.markdown("## Registrar Compra de Acción")
    with st.form("purchase_form", clear_on_submit=True):
        new_ticker = st.text_input("Ticker", placeholder="ej. AAPL, ADBE.MX").upper().strip()
        new_platform = st.selectbox("Plataforma", ["GBM", "ACTINVER", "ETORO"])
        new_portfolio = st.selectbox("Portafolio / Dueño", ["RVE MXN", "RVE USD", "ERGN", "RALEX", "RALEX UNI"])
        new_asset_type = st.selectbox("Tipo de Activo", ["STK", "FIBRA", "ETF", "SOFIPO"])
        
        # Intentar preseleccionar divisa basada en portafolio
        default_div = "USD" if "USD" in new_portfolio else "MXN"
        new_currency = st.selectbox("Divisa", ["MXN", "USD"], index=0 if default_div == "MXN" else 1)
        
        new_shares = st.number_input("Cantidad de Acciones", min_value=0.0, step=1.0, value=0.0)
        new_price = st.number_input("Precio de Compra Unitario", min_value=0.0, step=0.01, value=0.0)
        new_date = st.date_input("Fecha de Compra")
        
        submit_btn = st.form_submit_button("💾 Guardar Compra")
        
        if submit_btn:
            if not new_ticker:
                st.error("Por favor, ingresa el Ticker.")
            elif new_shares <= 0:
                st.error("La cantidad de acciones debe ser mayor a 0.")
            elif new_price <= 0:
                st.error("El precio unitario debe ser mayor a 0.")
            else:
                success, msg = register_transaction(
                    plataforma=new_platform,
                    portafolio=new_portfolio,
                    tipo_activo=new_asset_type,
                    ticker=new_ticker,
                    cantidad=new_shares,
                    precio_unitario=new_price,
                    divisa=new_currency,
                    fecha_transaccion=new_date
                )
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(f"Error al registrar: {msg}")

# --- CARGA DE DATOS ---
with st.spinner("Conectando a Oracle y obteniendo datos..."):
    df_portfolio = get_portfolio_data()

if df_portfolio.empty:
    st.warning("No se encontraron datos en el portafolio o hubo un error de conexión.")
    st.stop()

# Validar que existan las columnas necesarias (basadas en la estructura obtenida)
required_cols = ['TICKER', 'NUMERO_ACCIONES', 'PRECIO_COMPRA_MEDIO']
missing_cols = [col for col in required_cols if col not in df_portfolio.columns]
if missing_cols:
    st.error(f"Faltan columnas requeridas en la tabla: {missing_cols}")
    st.stop()

# Limpiar tickers nulos
df_portfolio = df_portfolio.dropna(subset=['TICKER'])
tickers_list = df_portfolio['TICKER'].unique().tolist()

with st.spinner("Obteniendo precios actuales del mercado (yfinance)..."):
    current_prices = get_current_prices(tickers_list)

# --- CÁLCULOS ---
# Asegurar tipos numéricos
df_portfolio['NUMERO_ACCIONES'] = pd.to_numeric(df_portfolio['NUMERO_ACCIONES'], errors='coerce').fillna(0)
df_portfolio['PRECIO_COMPRA_MEDIO'] = pd.to_numeric(df_portfolio['PRECIO_COMPRA_MEDIO'], errors='coerce').fillna(0)

# Calcular inversión inicial
df_portfolio['Inversion_Total'] = df_portfolio['NUMERO_ACCIONES'] * df_portfolio['PRECIO_COMPRA_MEDIO']

# Mapear precios actuales
df_portfolio['Precio_Actual'] = df_portfolio['TICKER'].map(current_prices)

# Calcular valor actual y ganancias/pérdidas
df_portfolio['Valor_Actual'] = df_portfolio['NUMERO_ACCIONES'] * df_portfolio['Precio_Actual']
df_portfolio['Ganancia_Perdida'] = df_portfolio['Valor_Actual'] - df_portfolio['Inversion_Total']
df_portfolio['Rentabilidad_%'] = (df_portfolio['Ganancia_Perdida'] / df_portfolio['Inversion_Total']) * 100

# Calcular Totales para KPIs
total_inversion = df_portfolio['Inversion_Total'].sum()
total_actual = df_portfolio['Valor_Actual'].sum()
total_gp = df_portfolio['Ganancia_Perdida'].sum()
rentabilidad_global = (total_gp / total_inversion * 100) if total_inversion > 0 else 0

# --- INTERFAZ PREMIUM ---

# 1. KPIs Principales
st.markdown("### Resumen Global")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Inversión Inicial Total", value=f"${total_inversion:,.2f}")

with col2:
    st.metric(label="Valor Actual del Portafolio", value=f"${total_actual:,.2f}", 
              delta=f"${total_gp:,.2f} ({rentabilidad_global:.2f}%)",
              delta_color="normal")

with col3:
    # Mostrar el activo más rentable
    if not df_portfolio.empty and total_actual > 0:
        best_asset = df_portfolio.loc[df_portfolio['Ganancia_Perdida'].idxmax()]
        st.metric(label="Mejor Activo", value=best_asset['TICKER'], 
                  delta=f"+${best_asset['Ganancia_Perdida']:,.2f}")
    else:
        st.metric(label="Mejor Activo", value="-")

# --- INFORMES TRIMESTRALES RECIENTES ---
st.markdown("### Últimos Informes Trimestrales")

@st.cache_data
def get_monthly_earnings_final(tickers):
    return get_recent_earnings(tickers)

with st.spinner("Buscando fechas de últimos reportes trimestrales (solo empresas de EE.UU.)..."):
    # Filtrar solo 'STK' (excluye FIBRAS y ETFs) para reducir peticiones a Yahoo Finance
    df_stk = df_portfolio[df_portfolio['TIPO_ACTIVO'] == 'STK']
    tickers_stk_list = df_stk['TICKER'].unique().tolist()
    recent_earnings_data = get_monthly_earnings_final(tickers_stk_list)

if recent_earnings_data:
    # Mostramos los reportes en un número dinámico de columnas (máximo 4 por fila)
    n_cols = min(len(recent_earnings_data), 4)
    cols_earn = st.columns(n_cols)
    
    for idx, report in enumerate(recent_earnings_data):
        ticker = report['Empresa (Ticker)']
        col = cols_earn[idx % n_cols]
        with col:
            st.info(f"**{ticker}** reporta el: \n\n {report['Fecha de Reporte']}")
            
            # Solo mostrar el botón si la fecha de reporte ya pasó (es menor o igual a hoy)
            today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
            if report['Fecha de Reporte'] <= today_str:
                # Manejar el estado del archivo SEC
                if f"sec_file_{ticker}" not in st.session_state:
                    if st.button("Buscar Reporte SEC", key=f"btn_{ticker}"):
                        with st.spinner(f"Buscando en la SEC para {ticker}..."):
                            file_path = download_sec_report(ticker)
                            st.session_state[f"sec_file_{ticker}"] = file_path
                            st.rerun()
                
                if f"sec_file_{ticker}" in st.session_state:
                    file_path = st.session_state[f"sec_file_{ticker}"]
                    if file_path and os.path.exists(file_path):
                        with open(file_path, "r", encoding="utf-8") as f:
                            html_data = f.read()
                        
                        # Intento de conversión a PDF comentado por inestabilidad de xhtml2pdf en HTMLs complejos
                        # Por defecto la SEC usa HTML muy complejos. Ofrecemos el HTML nativo.
                        st.download_button(
                            label="⬇️ Descargar Reporte (HTML)",
                            data=html_data,
                            file_name=f"Reporte_{ticker}.html",
                            mime="text/html",
                            key=f"dl_{ticker}",
                            help="El reporte oficial se descarga en HTML. Puedes abrirlo y usar 'Imprimir a PDF' en tu navegador."
                        )
                    else:
                        st.error("No se encontró 10-Q o 6-K")
            else:
                st.caption("Aún no publica su reporte este mes.")
else:
    st.write("No se encontró información reciente de reportes trimestrales para este mes.")

st.markdown("---")

# 2. Gráficos
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("### Composición del Portafolio")
    # Agrupar por Ticker para el gráfico
    pie_data = df_portfolio.groupby('TICKER')['Valor_Actual'].sum().reset_index()
    pie_data = pie_data[pie_data['Valor_Actual'] > 0]
    
    if not pie_data.empty:
        pie_data.set_index('TICKER', inplace=True)
        fig_comp = px.bar(pie_data, y='Valor_Actual', color_discrete_sequence=["#4C51BF"], 
                          labels={'TICKER': 'Activo', 'Valor_Actual': 'Valor ($)'},
                          template='plotly_dark')
        fig_comp.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='#FFFFFF'),
            title=dict(font=dict(color='#FFFFFF')),
            legend=dict(font=dict(color='#FFFFFF'))
        )
        st.plotly_chart(fig_comp, use_container_width=True, theme=None)
    else:
        st.info("No hay datos suficientes para graficar.")

with col_chart2:
    st.markdown("### Ganancias/Pérdidas por Activo")
    gp_data = df_portfolio.groupby('TICKER')['Ganancia_Perdida'].sum().reset_index()
    if not gp_data.empty:
        gp_data.set_index('TICKER', inplace=True)
        fig_gp = px.bar(gp_data, y='Ganancia_Perdida', color_discrete_sequence=["#38B2AC"], 
                        labels={'TICKER': 'Activo', 'Ganancia_Perdida': 'G/P ($)'},
                        template='plotly_dark')
        fig_gp.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='#FFFFFF'),
            title=dict(font=dict(color='#FFFFFF')),
            legend=dict(font=dict(color='#FFFFFF'))
        )
        st.plotly_chart(fig_gp, use_container_width=True, theme=None)
    else:
        st.info("No hay datos suficientes para graficar.")

st.markdown("---")

# 3. Distribución del Portafolio
st.markdown("### Distribución del Portafolio")
col_pie1, col_pie2 = st.columns(2)

with col_pie1:
    if 'PORTAFOLIO' in df_portfolio.columns and not df_portfolio.empty:
        pie_port = df_portfolio.groupby('PORTAFOLIO')['Valor_Actual'].sum().reset_index()
        pie_port = pie_port[pie_port['Valor_Actual'] > 0]
        fig_port = px.pie(pie_port, values='Valor_Actual', names='PORTAFOLIO', 
                          title='Porcentaje por Dueño / Portafolio', hole=0.4,
                          template='plotly_dark')
        fig_port.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='#FFFFFF'),
            title=dict(font=dict(color='#FFFFFF')),
            legend=dict(font=dict(color='#FFFFFF'))
        )
        fig_port.update_traces(textfont_color='#FFFFFF')
        st.plotly_chart(fig_port, use_container_width=True, theme=None)

with col_pie2:
    if 'TIPO_ACTIVO' in df_portfolio.columns and not df_portfolio.empty:
        pie_tipo = df_portfolio.groupby('TIPO_ACTIVO')['Valor_Actual'].sum().reset_index()
        pie_tipo = pie_tipo[pie_tipo['Valor_Actual'] > 0]
        fig_tipo = px.pie(pie_tipo, values='Valor_Actual', names='TIPO_ACTIVO', 
                          title='Porcentaje por Tipo de Activo', hole=0.4,
                          template='plotly_dark')
        fig_tipo.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)', 
            font=dict(color='#FFFFFF'),
            title=dict(font=dict(color='#FFFFFF')),
            legend=dict(font=dict(color='#FFFFFF'))
        )
        fig_tipo.update_traces(textfont_color='#FFFFFF')
        st.plotly_chart(fig_tipo, use_container_width=True, theme=None)

st.markdown("---")

# 4. Tabla Detallada
st.markdown("### Detalle de Posiciones")

# Formatear columnas para mostrar
display_df = df_portfolio[['TICKER', 'PLATAFORMA', 'NUMERO_ACCIONES', 'PRECIO_COMPRA_MEDIO', 'Precio_Actual', 'Inversion_Total', 'Valor_Actual', 'Ganancia_Perdida', 'Rentabilidad_%']].copy()

# Redondear y dar formato
display_df = display_df.round(2)

# Mostrar tabla interactiva
st.dataframe(
    display_df,
    use_container_width=True,
    column_config={
        "Rentabilidad_%": st.column_config.NumberColumn(
            "Rentabilidad (%)",
            format="%.2f %%",
        ),
        "PRECIO_COMPRA_MEDIO": st.column_config.NumberColumn(
            "Precio Compra ($)",
            format="$ %.2f",
        ),
        "Precio_Actual": st.column_config.NumberColumn(
            "Precio Actual ($)",
            format="$ %.2f",
        ),
        "Inversion_Total": st.column_config.NumberColumn(
            "Inversión ($)",
            format="$ %.2f",
        ),
        "Valor_Actual": st.column_config.NumberColumn(
            "Valor Actual ($)",
            format="$ %.2f",
        ),
        "Ganancia_Perdida": st.column_config.NumberColumn(
            "G/P ($)",
            format="$ %.2f",
        ),
    }
)
