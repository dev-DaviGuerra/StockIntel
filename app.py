import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
import constantes
from analise import analise_risco
from etl import salvar

st.set_page_config(
    page_title=f"StockIntel | {constantes.TICKER}",
    layout="wide",
    initial_sidebar_state="expanded"
)

def carregar_css(nome_arquivo):
    with open(nome_arquivo) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

carregar_css("style.css")

with st.sidebar:
    st.title("StockIntel")
    st.caption("Intelligence for Smart Investors")
    st.markdown("---")
    
    st.markdown(f"**Ativo Monitorado:** `{constantes.TICKER}`")
    st.markdown(f"**Empresa:** {constantes.EMPRESA}")
    
    st.markdown("---")
    st.info("""
    **Como funciona:**
    1. **ETL:** Coleta preços e notícias (Alpha Vantage).
    2. **NLP:** IA (FinBERT) lê e classifica notícias.
    3. **Risk:** Cálculo estatístico de VaR.
    """)
    st.markdown("---")
    st.caption("Desenvolvido por Davi Guerra")

st.title(f"Painel de Controle: {constantes.TICKER}")

engine = constantes.db_engine
if not engine:
    st.error("Erro crítico: Sem conexão com o banco de dados.")
    st.stop()

id_acao = salvar.garantir_dim_acao(constantes.TICKER, constantes.EMPRESA, engine)

metricas = analise_risco.calcular_metricas_risco(id_acao, engine)

if metricas:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💵 Preço Atual", f"${metricas['ultimo_fechamento']:.2f}")
    with col2:
        st.metric("⚠️ Risco (VaR 95%)", f"{metricas['var_95_diario']:.2%}", help="Queda máxima esperada para amanhã")
    with col3:
        st.metric("🌊 Volatilidade Anual", f"{metricas['volatilidade_anual']:.2%}")
    with col4:
        retorno = metricas['retorno_medio_diario']
        st.metric("📈 Retorno Médio", f"{retorno:.4%}", delta_color="normal")

st.markdown("---")

col_grafico, col_ia = st.columns([2, 1])

with col_grafico:
    st.subheader("📉 Evolução do Preço")
    
    query_precos = text("""
        SELECT data_preco, fechamento, volume 
        FROM fato_precos 
        WHERE id_acao = :id 
        ORDER BY data_preco ASC
    """)
    df_precos = pd.read_sql(query_precos, engine, params={"id": id_acao})

    if not df_precos.empty:
        fig = px.area(df_precos, x='data_preco', y='fechamento', title="")
        
        fig.update_traces(line_color='#00b4d8', fillcolor="rgba(0, 180, 216, 0.1)")
        fig.update_layout(
            xaxis_title=None, 
            yaxis_title="Preço ($)",
            hovermode="x unified",
            template="plotly_dark", 
            margin=dict(l=0, r=0, t=0, b=0),
            height=400
        )
        fig.update_xaxes(
            rangeslider_visible=False,
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(label="TUDO", step="all")
                ])
            )
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Aguardando dados de preços (Limite de API diário). Tente amanhã.")

with col_ia:
    st.subheader("🧠 Termômetro da IA")
    
    query_news = text("""
        SELECT sentimento_ia_label, sentimento_ia_score
        FROM fato_noticias n
        JOIN link_noticias_acoes l ON n.id_noticia = l.id_noticia
        WHERE l.id_acao = :id AND sentimento_ia_label IS NOT NULL
        ORDER BY data_publicacao DESC
        LIMIT 50
    """)
    df_sentimento = pd.read_sql(query_news, engine, params={"id": id_acao})
    
    score_final = 0
    if not df_sentimento.empty:
        mapa_valor = {'positive': 1, 'negative': -1, 'neutral': 0}
        
        total_score = 0
        total_peso = 0
        
        for index, row in df_sentimento.iterrows():
            peso = row['sentimento_ia_score'] 
            valor = mapa_valor.get(row['sentimento_ia_label'], 0)
            total_score += valor * peso
            total_peso += peso
            
        if total_peso > 0:
            score_final = total_score / total_peso 

    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = score_final,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Sentimento Médio (50 news)"},
        delta = {'reference': 0, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge = {
            'axis': {'range': [-1, 1], 'tickwidth': 1},
            'bar': {'color': "white", 'thickness': 0.2},
            'bgcolor': "black",
            'steps': [
                {'range': [-1, -0.3], 'color': "#ff4d4d"},
                {'range': [-0.3, 0.3], 'color': "#555555"},
                {'range': [0.3, 1], 'color': "#00cc66"}
            ],
        }
    ))
    fig_gauge.update_layout(
        height=300, 
        margin=dict(l=10, r=10, t=30, b=10),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("---")
st.subheader("📰 Feed de Notícias (Classificadas)")

query_feed = text("""
    SELECT titulo, data_publicacao, sentimento_ia_label, sentimento_ia_score, url, resumo
    FROM fato_noticias n
    JOIN link_noticias_acoes l ON n.id_noticia = l.id_noticia
    WHERE l.id_acao = :id
    ORDER BY data_publicacao DESC
    LIMIT 10
""")
df_feed = pd.read_sql(query_feed, engine, params={"id": id_acao})

if not df_feed.empty:
    for index, row in df_feed.iterrows():
        sentimento = row['sentimento_ia_label']
        score = row['sentimento_ia_score']
        
        if sentimento == 'positive':
            icon = "🟢 OTIMISTA"
            cor_box = "rgba(0, 204, 102, 0.1)" 
            border = "1px solid #00cc66"
        elif sentimento == 'negative':
            icon = "🔴 PESSIMISTA"
            cor_box = "rgba(255, 77, 77, 0.1)"
            border = "1px solid #ff4d4d"
        else:
            icon = "⚪ NEUTRO"
            cor_box = "rgba(255, 255, 255, 0.05)"
            border = "1px solid #555"
            
        if not sentimento:
            icon = "⏳ AGUARDANDO"
            score = 0.0
            cor_box = "rgba(255, 165, 0, 0.1)"
            border = "1px solid orange"

        st.markdown(f"""
        <div style="background-color: {cor_box}; padding: 15px; border-radius: 10px; border: {border}; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 1.1em;">{row['titulo']}</span>
                <span style="font-size: 0.8em; color: #ccc;">{row['data_publicacao'].strftime('%d/%m %H:%M')}</span>
            </div>
            <div style="margin-top: 5px; font-size: 0.9em;">
                <strong>IA:</strong> {icon} <span style="color: #888; font-size: 0.8em;">(Confiança: {score:.1%})</span>
            </div>
            <p style="margin-top: 10px; font-size: 0.95em; color: #ddd;">{row['resumo']}</p>
            <a href="{row['url']}" target="_blank" style="font-size: 0.8em; color: #00b4d8; text-decoration: none;">Ler notícia completa →</a>
        </div>
        """, unsafe_allow_html=True)

else:
    st.info("Nenhuma notícia recente encontrada no banco de dados.")