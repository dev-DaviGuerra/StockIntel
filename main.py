import constantes
from etl import salvar, extrair, transformar
from etl import extrair_noticias, transformar_noticias, salvar_noticias
from analise import ia_sentimento

def pipeline_completo():
    constantes.logger.info("--- INICIANDO PIPELINE STOCKINTEL ---")
    
    try:
        engine = constantes.db_engine
        ticker = constantes.TICKER
        empresa = constantes.EMPRESA
        
        if not engine:
            constantes.logger.error("Sem conexão com o banco. Abortando.")
            return

        id_acao = salvar.garantir_dim_acao(ticker, empresa, engine)
        if not id_acao: 
            constantes.logger.error("Falha na dimensão. Abortando.")
            return

        constantes.logger.info(">>> [1/3] ETL DE PREÇOS...")
        df_precos = extrair.extrair_dados_precos(ticker)
        
        if df_precos is not None:
            df_final = transformar.transformar_dados_precos(df_precos, id_acao)
            if df_final is not None:
                salvar.salvar_fato_precos(df_final, engine)
        else:
            constantes.logger.warning("Pulo ETL de Preços (Sem dados novos ou limite de API).")

        constantes.logger.info(">>> [2/3] ETL DE NOTÍCIAS...")
        df_news = extrair_noticias.extrair_dados_noticias(ticker, limite=50)
        
        if df_news is not None:
            df_clean = transformar_noticias.transformar_dados_noticias(df_news)
            if df_clean is not None:
                salvar_noticias.salvar_noticias_e_vinculo(df_clean, id_acao, engine)
        else:
            constantes.logger.warning("Pulo ETL de Notícias (Sem dados novos).")

        constantes.logger.info(">>> [3/3] IA & SENTIMENTO (FinBERT)...")
        ia_sentimento.processar_novas_noticias(engine)

        constantes.logger.info("--- PIPELINE FINALIZADO COM SUCESSO ---")

    except Exception as e:
        constantes.logger.critical(f"Erro fatal no pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    pipeline_completo()