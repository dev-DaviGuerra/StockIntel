import pandas as pd
from sqlalchemy import text
from io import StringIO
import constantes

def garantir_dim_acao(ticker, empresa, engine):
    constantes.logger.info(f"Verificando dimensão para {ticker}...")
    
    try:
        with engine.connect() as conn:
            sql_insert = text("""
                INSERT INTO dim_acoes (ticker, nome_empresa)
                VALUES (:ticker, :empresa)
                ON CONFLICT (ticker) DO NOTHING;
            """)
            conn.execute(sql_insert, {"ticker": ticker, "empresa": empresa})
            conn.commit()

            sql_get_id = text("SELECT id_acao FROM dim_acoes WHERE ticker = :ticker")
            resultado = conn.execute(sql_get_id, {"ticker": ticker}).fetchone()
            
            if resultado:
                id_acao = resultado[0]
                constantes.logger.info(f"ID recuperado para '{ticker}': {id_acao}")
                return id_acao
            else:
                constantes.logger.error(f"Erro: Ticker {ticker} não encontrado após inserção.")
                return None

    except Exception as e:
        constantes.logger.error(f"Erro ao interagir com dim_acoes: {e}")
        return None

def salvar_fato_precos(df_final, engine):
    if df_final is None or df_final.empty:
        constantes.logger.warning("DataFrame vazio. Nada a salvar.")
        return

    constantes.logger.info(f"Iniciando carga de {len(df_final)} linhas no Banco de Dados...")

    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE TEMPORARY TABLE temp_precos (LIKE fato_precos INCLUDING DEFAULTS)"))

            output = StringIO()
            df_final.to_csv(output, sep='\t', header=False, index=False)
            output.seek(0)

            colunas_sql = "(id_acao, data_preco, abertura, maximo, minimo, fechamento, volume)"
            sql_copy = f"COPY temp_precos {colunas_sql} FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t')"
            
            with conn.connection.cursor() as cursor:
                cursor.copy_expert(sql_copy, output)

            sql_move = text("""
                INSERT INTO fato_precos (id_acao, data_preco, abertura, maximo, minimo, fechamento, volume)
                SELECT id_acao, data_preco, abertura, maximo, minimo, fechamento, volume
                FROM temp_precos
                ON CONFLICT (id_acao, data_preco) DO NOTHING;
            """)
            result = conn.execute(sql_move)
            
            conn.execute(text("DROP TABLE temp_precos"))
            conn.commit()
            
            constantes.logger.info(f"Carga finalizada! Linhas inseridas: {result.rowcount}")

    except Exception as e:
        constantes.logger.error(f"Erro crítico ao salvar no banco: {e}")