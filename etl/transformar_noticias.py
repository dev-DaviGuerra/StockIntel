import pandas as pd
import constantes
from etl.validar import validar_noticias, DataValidationError

def transformar_dados_noticias(df_bruto):
    if df_bruto is None or df_bruto.empty:
        constantes.logger.warning("DataFrame de notícias vazio. Transformação pulada.")
        return None
    
    constantes.logger.info("Iniciando transformação das notícias...")

    try:
        df_transformado = df_bruto.rename(columns={
            'title': 'titulo',
            'summary': 'resumo',
            'url': 'url',
            'overall_sentiment_score': 'sentimento_api_score',
            'overall_sentiment_label': 'sentimento_api_label'
        })

        df_transformado['data_publicacao'] = pd.to_datetime(
            df_bruto['time_published'], 
            format='%Y%m%dT%H%M%S', 
            errors='coerce'
        )

        df_transformado['sentimento_api_score'] = pd.to_numeric(
            df_transformado['sentimento_api_score'], 
            errors='coerce'
        )

        colunas_finais = [
            'titulo',
            'resumo',
            'url',
            'data_publicacao',
            'sentimento_api_score',
            'sentimento_api_label'
        ]

        colunas_existentes = [c for c in colunas_finais if c in df_transformado.columns]
        df_final = df_transformado[colunas_existentes]

        # Validação de qualidade
        df_final = validar_noticias(df_final)

        constantes.logger.info(f"Transformação de notícias concluída: {len(df_final)} válidas.")
        return df_final

    except DataValidationError as e:
        constantes.logger.error(f"Validação de notícias falhou: {e}")
        return None
    except Exception as e:
        constantes.logger.error(f"Erro na transformação de notícias: {e}")
        return None