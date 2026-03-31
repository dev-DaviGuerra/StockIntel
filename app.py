import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from constantes import db_engine, logger

st.set_page_config(
    page_title="StockIntel | Market Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

_css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
with open(_css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_data(ttl=300, show_spinner=False)
def get_tickers() -> list[dict]:
    try:
        with db_engine.connect() as conn:
            rows = conn.execute(
                text("SELECT ticker, nome_empresa FROM dim_acoes ORDER BY ticker")
            ).fetchall()
        return [{"ticker": r[0], "empresa": r[1]} for r in rows]
    except Exception as e:
        logger.error(f"Erro ao carregar tickers: {e}")
        return []


@st.cache_data(ttl=300, show_spinner=False)
def get_prices(ticker: str, cutoff: str) -> pd.DataFrame:
    q = text("""
        SELECT fp.data_preco,
               fp.abertura,
               fp.maximo,
               fp.minimo,
               fp.fechamento,
               fp.volume
        FROM   fato_precos fp
        JOIN   dim_acoes   da ON fp.id_acao = da.id_acao
        WHERE  da.ticker     = :ticker
          AND  fp.data_preco >= :cutoff
        ORDER  BY fp.data_preco ASC
    """)
    try:
        with db_engine.connect() as conn:
            df = pd.read_sql(q, conn, params={"ticker": ticker, "cutoff": cutoff})
        df["data_preco"] = pd.to_datetime(df["data_preco"])
        for col in ["abertura", "maximo", "minimo", "fechamento", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
    except Exception as e:
        logger.error(f"Erro ao carregar preços ({ticker}): {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300, show_spinner=False)
def get_news(ticker: str, limit: int = 20) -> pd.DataFrame:
    q = text("""
        SELECT fn.titulo,
               fn.resumo,
               fn.url,
               fn.data_publicacao,
               fn.sentimento_ia_label,
               fn.sentimento_ia_score
        FROM   fato_noticias       fn
        JOIN   link_noticias_acoes lna ON fn.id_noticia = lna.id_noticia
        JOIN   dim_acoes           da  ON lna.id_acao   = da.id_acao
        WHERE  da.ticker = :ticker
        ORDER  BY fn.data_publicacao DESC
        LIMIT  :limit
    """)
    try:
        with db_engine.connect() as conn:
            return pd.read_sql(q, conn, params={"ticker": ticker, "limit": limit})
    except Exception as e:
        logger.error(f"Erro ao carregar notícias ({ticker}): {e}")
        return pd.DataFrame()


def compute_metrics(df: pd.DataFrame) -> dict:
    df = df.copy().sort_values("data_preco")
    df["ret"] = df["fechamento"].pct_change()
    price   = float(df["fechamento"].iloc[-1])
    prev    = float(df["fechamento"].iloc[-2]) if len(df) > 1 else price
    chg     = price - prev
    chg_pct = (chg / prev * 100) if prev else 0.0
    ret     = df["ret"].dropna()
    return {
        "price"     : price,
        "change"    : chg,
        "change_pct": chg_pct,
        "vol_ann"   : float(ret.std() * (252 ** 0.5) * 100),
        "var_95"    : float(ret.quantile(0.05) * 100),
        "mean_ret"  : float(ret.mean() * 100),
        "high_52w"  : float(df["maximo"].max()),
        "low_52w"   : float(df["minimo"].min()),
        "avg_vol"   : float(df["volume"].mean()),
        "n_days"    : len(df),
    }


_DARK = dict(
    paper_bgcolor="#0a0e1a",
    plot_bgcolor="#0d1117",
    font_family="Inter, sans-serif",
    font_color="#8892a4",
)

_MA_STYLE = {
    "MA20" : ("#f7b731", "dot"),
    "MA50" : ("#4bcffa", "dot"),
    "MA200": ("#a29bfe", "dash"),
}


def chart_candlestick(df: pd.DataFrame, ticker: str, mas: list) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.76, 0.24],
        vertical_spacing=0.02,
    )

    fig.add_trace(go.Candlestick(
        x=df["data_preco"],
        open=df["abertura"], high=df["maximo"],
        low=df["minimo"],   close=df["fechamento"],
        name=ticker,
        increasing_line_color="#00ff88",
        increasing_fillcolor="rgba(0,255,136,0.10)",
        decreasing_line_color="#ff4466",
        decreasing_fillcolor="rgba(255,68,102,0.10)",
        line_width=1,
    ), row=1, col=1)

    for ma, (color, dash) in _MA_STYLE.items():
        if ma in mas:
            period = int(ma[2:])
            fig.add_trace(go.Scatter(
                x=df["data_preco"],
                y=df["fechamento"].rolling(period).mean(),
                name=ma,
                line=dict(color=color, width=1.4, dash=dash),
                opacity=0.9,
            ), row=1, col=1)

    vol_colors = [
        "rgba(0,255,136,0.50)" if c >= o else "rgba(255,68,102,0.50)"
        for c, o in zip(df["fechamento"], df["abertura"])
    ]
    fig.add_trace(go.Bar(
        x=df["data_preco"], y=df["volume"],
        marker_color=vol_colors, name="Volume", showlegend=False,
    ), row=2, col=1)

    _grid = dict(showgrid=True, gridcolor="#1a2536", gridwidth=0.5, zeroline=False)
    fig.update_layout(
        **_DARK,
        height=500,
        margin=dict(l=0, r=58, t=10, b=0),
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(0,0,0,0)", bordercolor="#1e2d3d",
        ),
    )
    fig.update_yaxes(**_grid, side="right")
    fig.update_xaxes(**_grid, showline=True, linecolor="#1e2d3d")
    return fig


def chart_gauge(score: float) -> go.Figure:
    c = "#00ff88" if score > 0.15 else "#ff4466" if score < -0.15 else "#8892a4"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"valueformat": ".3f", "font": {"size": 32, "color": c}},
        gauge={
            "axis": {
                "range": [-1, 1], "tickwidth": 1, "tickcolor": "#1e2d3d",
                "tickvals": [-1, -0.5, 0, 0.5, 1],
                "ticktext": ["-1.0", "-0.5", "0", "+0.5", "+1.0"],
            },
            "bar": {"color": c, "thickness": 0.26},
            "bgcolor": "#0d1117",
            "borderwidth": 1, "bordercolor": "#1e2d3d",
            "steps": [
                {"range": [-1,   -0.15], "color": "rgba(255,68,102,0.07)"},
                {"range": [-0.15, 0.15], "color": "rgba(30,45,61,0.35)"},
                {"range": [0.15,  1],    "color": "rgba(0,255,136,0.07)"},
            ],
        },
    ))
    fig.update_layout(**_DARK, height=195, margin=dict(l=12, r=12, t=18, b=0))
    return fig


def chart_returns_dist(df: pd.DataFrame) -> go.Figure:
    ret   = df["fechamento"].pct_change().dropna() * 100
    var95 = float(ret.quantile(0.05))
    fig   = go.Figure()
    fig.add_trace(go.Histogram(
        x=ret, nbinsx=50, histnorm="probability density",
        marker_color="#4bcffa", opacity=0.60, name="Retornos",
    ))
    fig.add_vline(
        x=var95, line_color="#ff4466", line_width=2, line_dash="dash",
        annotation_text=f"VaR 95%: {var95:.2f}%",
        annotation_font_color="#ff4466",
        annotation_position="top right",
    )
    fig.update_layout(
        **_DARK,
        height=225,
        margin=dict(l=4, r=4, t=8, b=35),
        showlegend=False,
        xaxis=dict(title="Retorno Diário (%)", gridcolor="#1a2536"),
        yaxis=dict(title="Densidade",          gridcolor="#1a2536"),
    )
    return fig


with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
      <span class="logo-mark">SI</span>
      <div>
        <div class="logo-title">StockIntel</div>
        <div class="logo-sub">Market Intelligence</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='sidebar-sep'></div>", unsafe_allow_html=True)

    tickers = get_tickers()
    if not tickers:
        st.warning("Nenhum ativo no banco. Execute o pipeline ETL.")
        ticker_map = {}
    else:
        ticker_map = {t["ticker"]: f"{t['ticker']}  ·  {t['empresa']}" for t in tickers}

    sel_ticker = st.selectbox(
        "Ativo monitorado",
        options=list(ticker_map) or ["—"],
        format_func=lambda x: ticker_map.get(x, x),
    )
    sel_empresa = next(
        (t["empresa"] for t in tickers if t["ticker"] == sel_ticker), sel_ticker
    )

    st.markdown("<div class='sidebar-sep'></div>", unsafe_allow_html=True)

    PERIODS = {"1M": 30, "3M": 90, "6M": 180, "1A": 365, "2A": 730, "Máx": 3650}
    sel_period = st.radio("Período", list(PERIODS), index=3, horizontal=True)
    days   = PERIODS[sel_period]
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    st.markdown("<div class='sidebar-sep'></div>", unsafe_allow_html=True)

    st.markdown('<p class="sidebar-label">Médias Móveis</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    show_mas: list[str] = []
    if c1.checkbox("MA 20",  value=True):  show_mas.append("MA20")
    if c2.checkbox("MA 50",  value=True):  show_mas.append("MA50")
    if c3.checkbox("MA 200", value=False): show_mas.append("MA200")

    st.markdown("<div class='sidebar-sep'></div>", unsafe_allow_html=True)

    if st.button("▶  Executar Pipeline ETL", use_container_width=True, type="primary"):
        with st.spinner("Executando pipeline completo..."):
            try:
                from main import pipeline_completo
                pipeline_completo()
                st.cache_data.clear()
                st.success("Pipeline finalizado com sucesso.")
            except Exception as exc:
                st.error(f"Erro: {exc}")

    st.markdown("""
    <div class="sidebar-footer">
      <div>📡 Alpha Vantage API</div>
      <div>🧠 FinBERT NLP</div>
      <div>🗄️ Neon PostgreSQL</div>
    </div>
    """, unsafe_allow_html=True)


if not db_engine:
    st.error("Sem conexão com o banco de dados. Verifique o arquivo .env.")
    st.stop()

with st.spinner(""):
    df_prices = get_prices(sel_ticker, cutoff)
    df_news   = get_news(sel_ticker, 20)

if df_prices.empty:
    st.error(
        f"Sem dados para **{sel_ticker}** no período selecionado. "
        "Execute o pipeline ETL na barra lateral."
    )
    st.stop()

m = compute_metrics(df_prices)

sign  = "+" if m["change"] >= 0 else ""
color = "#00ff88" if m["change"] >= 0 else "#ff4466"
st.markdown(f"""
<div class="asset-header">
  <div class="ah-left">
    <span class="ah-ticker">{sel_ticker}</span>
    <span class="ah-name">{sel_empresa}</span>
  </div>
  <div class="ah-center">
    <span class="ah-price">${m['price']:,.2f}</span>
    <span class="ah-chg" style="color:{color}">
      {sign}{m['change']:.2f}&nbsp;&nbsp;({sign}{m['change_pct']:.2f}%)
    </span>
  </div>
  <div class="ah-right">
    <span class="ah-label">Última atualização</span>
    <span class="ah-ts">{datetime.now().strftime('%d/%m/%Y  %H:%M')}</span>
  </div>
</div>
<div class="header-rule"></div>
""", unsafe_allow_html=True)

kpis = [
    ("Preço Atual",        f"${m['price']:,.2f}",           None),
    ("Variação Diária",    f"{sign}{m['change_pct']:.2f}%", m["change_pct"]),
    ("Volatilidade Anual", f"{m['vol_ann']:.2f}%",          None),
    ("VaR 95%",            f"{m['var_95']:.2f}%",           m["var_95"]),
    ("Máx. 52 Semanas",    f"${m['high_52w']:,.2f}",        None),
    ("Mín. 52 Semanas",    f"${m['low_52w']:,.2f}",         None),
]
for col, (label, value, signal) in zip(st.columns(6), kpis):
    cls = (" kpi-pos" if signal is not None and signal > 0 else
           " kpi-neg" if signal is not None and signal < 0 else "")
    with col:
        st.markdown(f"""
        <div class="kpi-card{cls}">
          <div class="kpi-lbl">{label}</div>
          <div class="kpi-val">{value}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(
    '<p class="section-title">Gráfico de Preços &nbsp;·&nbsp; OHLCV</p>',
    unsafe_allow_html=True,
)
st.plotly_chart(
    chart_candlestick(df_prices, sel_ticker, show_mas),
    use_container_width=True,
    config={"displaylogo": False, "modeBarButtonsToRemove": ["autoScale2d"]},
)

col_gauge, col_dist, col_news = st.columns([1, 1, 2])

with col_gauge:
    st.markdown(
        '<p class="section-title">Sentimento IA &nbsp;·&nbsp; FinBERT</p>',
        unsafe_allow_html=True,
    )
    if not df_news.empty:
        scores    = pd.to_numeric(df_news["sentimento_ia_score"], errors="coerce").dropna()
        score_val = float(scores.mean()) if not scores.empty else 0.0
        st.plotly_chart(chart_gauge(score_val), use_container_width=True,
                        config={"displayModeBar": False})
        pos = (df_news["sentimento_ia_label"] == "positive").sum()
        neu = (df_news["sentimento_ia_label"] == "neutral").sum()
        neg = (df_news["sentimento_ia_label"] == "negative").sum()
        tot = max(pos + neu + neg, 1)
        st.markdown(f"""
        <div class="sent-row">
          <div class="sent-item si-pos">▲ Positivo &nbsp;<b>{pos}</b> ({pos/tot*100:.0f}%)</div>
          <div class="sent-item si-neu">● Neutro &nbsp;&nbsp;<b>{neu}</b> ({neu/tot*100:.0f}%)</div>
          <div class="sent-item si-neg">▼ Negativo &nbsp;<b>{neg}</b> ({neg/tot*100:.0f}%)</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Sem dados de sentimento. Execute o pipeline ETL.")

with col_dist:
    st.markdown(
        '<p class="section-title">Distribuição de Retornos</p>',
        unsafe_allow_html=True,
    )
    if len(df_prices) > 10:
        st.plotly_chart(chart_returns_dist(df_prices), use_container_width=True,
                        config={"displayModeBar": False})
        ret = df_prices["fechamento"].pct_change().dropna() * 100
        st.markdown(f"""
        <div class="stat-grid">
          <div class="stat-cell">
            <div class="stat-lbl">Retorno Médio</div>
            <div class="stat-val {'sv-pos' if ret.mean()>0 else 'sv-neg'}">{ret.mean():.3f}%</div>
          </div>
          <div class="stat-cell">
            <div class="stat-lbl">Desvio Padrão</div>
            <div class="stat-val">{ret.std():.3f}%</div>
          </div>
          <div class="stat-cell">
            <div class="stat-lbl">Máx. Ganho</div>
            <div class="stat-val sv-pos">{ret.max():.2f}%</div>
          </div>
          <div class="stat-cell">
            <div class="stat-lbl">Máx. Perda</div>
            <div class="stat-val sv-neg">{ret.min():.2f}%</div>
          </div>
        </div>""", unsafe_allow_html=True)

with col_news:
    st.markdown(
        '<p class="section-title">Feed de Notícias</p>',
        unsafe_allow_html=True,
    )
    if not df_news.empty:
        for _, row in df_news.head(8).iterrows():
            lbl   = (row.get("sentimento_ia_label") or "neutral").lower()
            score = float(row.get("sentimento_ia_score") or 0)
            cls, icon, txt = {
                "positive": ("nc-pos", "▲", "POSITIVO"),
                "negative": ("nc-neg", "▼", "NEGATIVO"),
            }.get(lbl, ("nc-neu", "●", "NEUTRO"))

            pub = ""
            raw_date = row.get("data_publicacao")
            if raw_date and str(raw_date) not in ("nan", "NaT", "None"):
                try:
                    pub = pd.to_datetime(raw_date).strftime("%d/%m/%Y  %H:%M")
                except Exception:
                    pub = str(raw_date)[:16]

            title   = str(row.get("titulo")  or "")[:110]
            summary = str(row.get("resumo")  or "")[:200]
            url     = str(row.get("url")     or "#")

            st.markdown(f"""
            <div class="news-card">
              <div class="nc-header">
                <span class="nc-badge {cls}">{icon} {txt}</span>
                <span class="nc-conf">conf {score:.2f}</span>
                <span class="nc-date">{pub}</span>
              </div>
              <a class="nc-title" href="{url}" target="_blank">{title}</a>
              <p  class="nc-body">{summary}</p>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Nenhuma notícia disponível.")

st.markdown(f"""
<div class="si-footer">
  StockIntel &nbsp;·&nbsp; Market Intelligence Platform &nbsp;·&nbsp;
  Alpha Vantage &nbsp;·&nbsp; FinBERT (ProsusAI) &nbsp;·&nbsp;
  Neon PostgreSQL &nbsp;·&nbsp; {m['n_days']} dias de histórico
</div>""", unsafe_allow_html=True)
