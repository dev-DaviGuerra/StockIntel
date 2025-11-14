import requests
import pandas as pd
from io import StringIO
import constantes

def extrair_dados_precos(ticker):
    constantes.logger.info(f"Iniciando extração para {ticker}")
    try:
        url= (
            f"https://www.alphavantage.co/query?"
            f"function=TIME_SERIES_DAILY"
            f"&symbol={ticker}"
            f"&outputsize=full"
            f"&datatype=csv"
            f"&apikey={constantes.API_KEY}"
            )
        
        response = requests.get(url)
        response.raise_for_status()

        csv_data = StringIO(response.text)
        df_bruto = pd.read_csv(csv_data)

        if df_bruto.empty:
            constantes.logger.warning(f"Nenhum dado retornado da API para {ticker}.")
            return None
        
        constantes.logger.info(f"Extração concluída. {len(df_bruto)} registros encontrados para {ticker}.")
        return df_bruto
    
    except requests.exceptions.RequestException as e:
        constantes.logger.error(f"Erro na requisição da API para {ticker}: {e}")
        return None
    except pd.errors.EmptyDataError:
        constantes.logger.error(f"A API retornou dados vazios ou mal formatados para {ticker}.")
        return None
    except Exception as e:
        constantes.logger.error(f"Erro inesperado na extração de {ticker}: {e}")
    