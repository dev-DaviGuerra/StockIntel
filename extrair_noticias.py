import requests
import pandas as pd
import constantes

def extrair_dados_noticias(ticker, limite=100):
    constantes.logger.info(f"Iniciando extração de NOTÍCIAS para {ticker} (Limit={limite})...")

    try:
        url = (
            f"https://www.alphavantage.co/query?"
            f"function=NEWS_SENTIMENT"
            f"&tickers={ticker}"
            f"&limit={limite}"
            f"&apikey={constantes.API_KEY}"
        )

        response = requests.get(url)
        response.raise_for_status()
        
        dados_json = response.json()

        if "feed" not in dados_json:
            constantes.logger.warning(f"Campo 'feed' não encontrado. Resposta da API: {dados_json}")
            return None
        
        lista_noticias = dados_json['feed']

        if not lista_noticias:
            constantes.logger.warning(f"Nenhuma notícia encontrada para {ticker}.")
            return None
        
        df_noticias = pd.DataFrame(lista_noticias)

        constantes.logger.info(f"Extração de notícias concluída. {len(df_noticias)} notícias encontradas.")
        return df_noticias

    except requests.exceptions.RequestException as e:
        constantes.logger.error(f"Erro de rede na extração de notícias: {e}")
        return None
    except Exception as e:
        constantes.logger.error(f"Erro inesperado na extração de notícias: {e}")
        return None