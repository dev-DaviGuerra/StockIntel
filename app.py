import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import text
import constantes
from analise import analise_risco
from etl import salvar

st.set_page_config(
    page_title="StockIntel Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title(f"📈 StockIntel: Monitoramento Inteligente ({constantes.TICKER})")
st.markdown("---")

engine = constantes.db_engine
if not engine:
    st.error("Erro de conexão com o banco de dados.")
    st.stop()

id_acao = salvar.garantir_dim_acao(constantes.TICKER, constantes.EMPRESA, engine)

metricas = analise_risco.calcular_metricas_risco(id_acao, engine)

if metricas:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Preço Atual", f"${metricas['ultimo_fechamento']:.2f}")
    
    with col2:
        st.metric("Risco Diário (VaR 95%)", f"{metricas['var_95_diario']:.2%}")
        st.caption("Queda máxima esperada para amanhã (95% confiança)")
        
    with col3:
        st.metric("Volatilidade Anual", f"{metricas['volatilidade_anual']:.2%}")
    
    with col4:
        st.metric("Retorno Médio Diário", f"{metricas['retorno_medio_diario']:.4%}")

st.markdown("---")

st.subheader("📊 Histórico de Preços")

query_precos = text("""
    SELECT data_preco, fechamento, volume 
    FROM fato_precos 
    WHERE id_acao = :id 
    ORDER BY data_preco ASC
""")
df_precos = pd.read_sql(query_precos, engine, params={"id": id_acao})

if not df_precos.empty:
    fig = px.line(df_precos, x='data_preco', y='fechamento', title=f'Evolução do Preço: {constantes.TICKER}')
    fig.update_traces(line_color='#007AFF')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Sem dados de preços para exibir.")

st.markdown("---")
st.subheader("🤖 Sentimento do Mercado (IA FinBERT)")

query_news = text("""
    SELECT titulo, data_publicacao, sentimento_ia_label, sentimento_ia_score, url, resumo
    FROM fato_noticias n
    JOIN link_noticias_acoes l ON n.id_noticia = l.id_noticia
    WHERE l.id_acao = :id
    ORDER BY data_publicacao DESC
    LIMIT 15
""")
df_news = pd.read_sql(query_news, engine, params={"id": id_acao})

if not df_news.empty:
    for index, row in df_news.iterrows():
        sentimento = row['sentimento_ia_label']
        score = row['sentimento_ia_score']
        
        if sentimento:
            sentimento_texto = sentimento.upper()
            if sentimento == 'positive':
                icon = "🟢"
                cor = "green"
            elif sentimento == 'negative':
                icon = "🔴"
                cor = "red"
            else:
                icon = "⚪"
                cor = "gray"
        else:
            sentimento_texto = "AGUARDANDO ANÁLISE"
            icon = "⏳"
            cor = "orange"
            score = 0.0
            
        with st.expander(f"{icon} {row['titulo']} ({score:.0%})"):
            st.markdown(f"**Data:** {row['data_publicacao']}")
            st.markdown(f"**Sentimento:** :{cor}[{sentimento_texto}]")
            st.write(row['resumo'])
            st.markdown(f"[Ler notícia original]({row['url']})")
else:
    st.info("Nenhuma notícia recente encontrada.")

st.markdown("---")
st.caption("StockIntel v1.0 - Desenvolvido por Davi Guerra")