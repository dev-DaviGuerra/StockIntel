import pandas as pd
import constantes

def transformar_dados_precos(df_bruto, id_acao):

    if df_bruto is None or df_bruto.empty:
        constantes.logger.warning("Dataframe vazio recebido para transformação, nada a fazer.")
        return None

    constantes.logger.info("Iniciando transformação dos dados de preços...")

    try:
        df_transformado = df_bruto.rename(columns={
            'timestamp': 'data_preco',
            'open': 'abertura',
            'high': 'maximo',
            'low': 'minimo',
            'close': 'fechamento',
            'volume': 'volume'
        })

        df_transformado['id_acao'] = id_acao

        df_transformado['data_preco'] = pd.to_datetime(df_transformado['data_preco'])

        colunas_finais = [
            'id_acao', 
            'data_preco', 
            'abertura', 
            'maximo', 
            'minimo', 
            'fechamento', 
            'volume'
        ]

        df_final = df_transformado[colunas_finais]
        
        constantes.logger.info("Transformação concluída com sucesso.")
        return df_final
        
    except Exception as e:
        constantes.logger.error(f"Erro crítico durante a transformação: {e}")
        return None