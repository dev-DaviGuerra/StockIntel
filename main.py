import constantes
import salvar
import extrair
import transformar
import extrair_noticias
import transformar_noticias
import salvar_noticias

def pipeline_engenharia():

    constantes.logger.info("--- INICIANDO PIPELINE STOCKINTEL (ETL APENAS) ---")
    
    try:
        engine = constantes.db_engine
        ticker = constantes.TICKER
        empresa = constantes.EMPRESA
        
        if not engine:
            constantes.logger.error("Sem conexão com o banco. Abortando.")
            return

        id_acao = salvar.garantir_dim_acao(ticker, empresa, engine)
        if not id_acao: 
            constantes.logger.error("Falha na Dimensão. Abortando.")
            return

        constantes.logger.info(">>> [1/2] ETL DE PREÇOS...")
        df_precos = extrair.extrair_dados_precos(ticker)
        
        if df_precos is not None:
            df_final_precos = transformar.transformar_dados_precos(df_precos, id_acao)
            if df_final_precos is not None:
                salvar.salvar_fato_precos(df_final_precos, engine)
        else:
            constantes.logger.warning("Pulo ETL de Preços (Sem dados).")

        constantes.logger.info(">>> [2/2] ETL DE NOTÍCIAS...")
        df_news = extrair_noticias.extrair_dados_noticias(ticker, limite=50)
        
        if df_news is not None:
            df_final_news = transformar_noticias.transformar_dados_noticias(df_news)
            
            if df_final_news is not None:
                salvar_noticias.salvar_noticias_e_vinculo(df_final_news, id_acao, engine)
        else:
            constantes.logger.warning("Pulo ETL de Notícias (Sem dados).")

        constantes.logger.info("--- PIPELINE DE ENGENHARIA FINALIZADO ---")

    except Exception as e:
        constantes.logger.critical(f"Erro fatal no pipeline: {e}", exc_info=True)

if __name__ == "__main__":
    pipeline_engenharia()