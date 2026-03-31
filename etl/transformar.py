import pandas as pd
import constantes
from etl.validar import validar_precos, DataValidationError

def transformar_dados_precos(df_bruto, id_acao):
    if df_bruto is None or df_bruto.empty:
        constantes.logger.warning("Dataframe vazio recebido para transformação, nada a fazer.")
        return None

    constantes.logger.info("Iniciando transformação dos dados de preços...")

    try:
        df = df_bruto.rename(columns={
            'timestamp': 'data_preco',
            'open':      'abertura',
            'high':      'maximo',
            'low':       'minimo',
            'close':     'fechamento',
            'volume':    'volume',
        })

        df['id_acao']    = id_acao
        df['data_preco'] = pd.to_datetime(df['data_preco'])

        colunas = ['id_acao', 'data_preco', 'abertura', 'maximo', 'minimo', 'fechamento', 'volume']
        df = df[colunas]

        # Validação de qualidade
        df = validar_precos(df)

        constantes.logger.info(f"Transformação concluída: {len(df)} registros válidos.")
        return df

    except DataValidationError as e:
        constantes.logger.error(f"Validação falhou: {e}")
        return None
    except Exception as e:
        constantes.logger.error(f"Erro crítico durante a transformação: {e}")
        return None