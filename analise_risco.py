import pandas as pd
import numpy as np
from sqlalchemy import text
import constantes

def calcular_metricas_risco(id_acao, engine):
    constantes.logger.info(f"Calculando riscos para ID Ação: {id_acao}...")
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT data_preco, fechamento 
                FROM fato_precos 
                WHERE id_acao = :id_acao 
                ORDER BY data_preco ASC
            """)
            df = pd.read_sql(query, conn, params={"id_acao": id_acao})
            
            if df.empty:
                constantes.logger.warning("Sem dados de preço para calcular risco.")
                return None

            df['retorno'] = df['fechamento'].pct_change()
            
            df = df.dropna()

            var_95 = np.percentile(df['retorno'], 5)
            
            volatilidade = df['retorno'].std() * np.sqrt(252)

            metricas = {
                "var_95_diario": var_95,
                "volatilidade_anual": volatilidade,
                "retorno_medio_diario": df['retorno'].mean(),
                "ultimo_fechamento": df['fechamento'].iloc[-1],
                "data_base": df['data_preco'].iloc[-1]
            }
            
            return metricas

    except Exception as e:
        constantes.logger.error(f"Erro ao calcular risco: {e}")
        return None