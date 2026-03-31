from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import TaskGroup

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

logger = logging.getLogger(__name__)


SCHEDULE_INTERVAL = "0 */4 * * 1-5"

TICKERS: list[dict] = [
    {"ticker": "AAPL",  "empresa": "Apple Inc."},
    {"ticker": "MSFT",  "empresa": "Microsoft Corporation"},
    {"ticker": "GOOGL", "empresa": "Alphabet Inc."},
]

DEFAULT_ARGS: dict = {
    "owner"                 : "stockintel",
    "depends_on_past"       : False,
    "start_date"            : datetime(2025, 1, 1),
    "email_on_failure"      : False,
    "email_on_retry"        : False,
    "retries"               : 3,
    "retry_delay"           : timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay"       : timedelta(minutes=30),
}



def _health_check(**_):
    from constantes import db_engine
    from sqlalchemy import text

    with db_engine.connect() as conn:
        n = conn.execute(text("SELECT COUNT(*) FROM fato_precos")).scalar()
    logger.info(f"[health_check] Banco acessível. fato_precos: {n} registros.")
    return n


def _run_price_etl(ticker: str, empresa: str, **_):
    from constantes import db_engine
    from etl.extrair import extrair_dados_precos
    from etl.transformar import transformar_dados_precos
    from etl.salvar import garantir_dim_acao, salvar_fato_precos

    logger.info(f"[{ticker}] Iniciando ETL de preços...")

    df_bruto = extrair_dados_precos(ticker)
    if df_bruto is None or df_bruto.empty:
        logger.warning(f"[{ticker}] Sem dados de preço da API (limite ou sem resposta).")
        return {"ticker": ticker, "status": "skipped", "records": 0}

    id_acao  = garantir_dim_acao(ticker, empresa, db_engine)
    df_final = transformar_dados_precos(df_bruto, id_acao)

    if df_final is None or df_final.empty:
        raise RuntimeError(f"[{ticker}] Transformação de preços retornou vazio.")

    salvar_fato_precos(df_final, db_engine)
    logger.info(f"[{ticker}] ETL de preços concluído — {len(df_final)} registros.")
    return {"ticker": ticker, "status": "ok", "records": len(df_final)}


def _run_news_etl(ticker: str, empresa: str, **_):
    from constantes import db_engine
    from etl.extrair_noticias import extrair_dados_noticias
    from etl.transformar_noticias import transformar_dados_noticias
    from etl.salvar_noticias import salvar_noticias_e_vinculo
    from etl.salvar import garantir_dim_acao

    logger.info(f"[{ticker}] Iniciando ETL de notícias...")

    df_bruto = extrair_dados_noticias(ticker, limite=50)
    if df_bruto is None or df_bruto.empty:
        logger.warning(f"[{ticker}] Nenhuma notícia retornada pela API.")
        return {"ticker": ticker, "status": "skipped", "records": 0}

    df_clean = transformar_dados_noticias(df_bruto)
    if df_clean is None or df_clean.empty:
        logger.warning(f"[{ticker}] Transformação de notícias sem registros válidos.")
        return {"ticker": ticker, "status": "skipped", "records": 0}

    id_acao = garantir_dim_acao(ticker, empresa, db_engine)
    salvar_noticias_e_vinculo(df_clean, id_acao, db_engine)
    logger.info(f"[{ticker}] ETL de notícias concluído — {len(df_clean)} notícias.")
    return {"ticker": ticker, "status": "ok", "records": len(df_clean)}


def _run_sentiment_analysis(**_):
    """Processa notícias sem label com FinBERT (roda uma vez, cobre todos os tickers)."""
    from constantes import db_engine
    from analise.ia_sentimento import processar_novas_noticias

    logger.info("[sentimento] Iniciando análise FinBERT...")
    processar_novas_noticias(db_engine)
    logger.info("[sentimento] Análise concluída.")


# ── DAG ───────────────────────────────────────────────────────────────────────

with DAG(
    dag_id          ="stockintel_pipeline",
    description     ="Pipeline de inteligência de mercado: preços + notícias + FinBERT",
    default_args    =DEFAULT_ARGS,
    schedule=SCHEDULE_INTERVAL,
    catchup         =False,
    max_active_runs =1,
    tags            =["stockintel", "finance", "etl", "nlp"],
    doc_md          =__doc__,
) as dag:

    inicio = EmptyOperator(task_id="inicio")
    fim    = EmptyOperator(task_id="fim")

    health = PythonOperator(
        task_id        ="health_check_db",
        python_callable=_health_check,
        doc_md         ="Valida conectividade com Neon PostgreSQL antes de qualquer task.",
    )

    sentimento = PythonOperator(
        task_id        ="analise_sentimento_finbert",
        python_callable=_run_sentiment_analysis,
        execution_timeout=timedelta(minutes=30),
        doc_md         ="Classifica notícias pendentes com FinBERT (batch de até 50).",
    )

    # Um TaskGroup por ticker — precos e noticias correm em paralelo dentro do grupo
    ticker_groups: list = []
    for stock in TICKERS:
        tkr  = stock["ticker"]
        emp  = stock["empresa"]

        with TaskGroup(group_id=f"ticker_{tkr}") as tg:

            precos = PythonOperator(
                task_id        =f"etl_precos",
                python_callable=_run_price_etl,
                op_kwargs      ={"ticker": tkr, "empresa": emp},
                execution_timeout=timedelta(minutes=10),
                doc_md         =f"Extrai, transforma e salva preços diários de {tkr}.",
            )

            noticias = PythonOperator(
                task_id        =f"etl_noticias",
                python_callable=_run_news_etl,
                op_kwargs      ={"ticker": tkr, "empresa": emp},
                execution_timeout=timedelta(minutes=10),
                doc_md         =f"Extrai, transforma e salva notícias de {tkr}.",
            )

            # Preços e notícias são independentes — rodam em paralelo
            [precos, noticias]

        ticker_groups.append(tg)

    # ── Orquestração ──────────────────────────────────────────────────────────
    #
    #   inicio → health_check → [ticker_AAPL, ticker_MSFT, ...] → sentimento → fim
    #
    inicio >> health >> ticker_groups >> sentimento >> fim
