import constantes
import extrair
import salvar
import transformar

def pipeline_completo():
    constantes.logger.info('---INICIANDO PIPELINE STOCKINTEL---')

    try:
        engine = constantes.db_engine
        ticker = constantes.TICKER
        empresa = constantes.EMPRESA

        if not engine:
            constantes.logger.error('Sem conexão com o banco')
            return
        
        id_acao = salvar.garantir_dim_acao(ticker, empresa, engine)

        if not id_acao:
            constantes.logger.error('Falha ao obter o id da ação')
            return
        
        df_bruto = extrair.extrair_dados_precos(ticker)

        df_final = transformar.transformar_dados_precos(df_bruto, id_acao)

        salvar.salvar_fato_precos(df_final, engine)

        constantes.logger.info('---PIPELINE FINALIZADO COM SUCESSO---')
    
    except Exception as e:
        constantes.logger.critical(f'Erro fatal no pipeline: {e}', exc_info=True)


if __name__ == '__main__':
    pipeline_completo()