import pandas as pd
from sqlalchemy import text
from io import StringIO
import constantes

def salvar_noticias_e_vinculo(df_noticias, id_acao, engine):

    if df_noticias is None or df_noticias.empty:
        constantes.logger.warning("DataFrame de notícias vazio. Nada a salvar.")
        return

    constantes.logger.info(f"Iniciando processo de carga para {len(df_noticias)} notícias...")

    try:
        with engine.connect() as conn:
            
            conn.execute(text("CREATE TEMPORARY TABLE temp_news (LIKE fato_noticias INCLUDING DEFAULTS)"))
            
            cols_fato = ['titulo', 'resumo', 'url', 'data_publicacao', 'sentimento_api_score', 'sentimento_api_label']
            output = StringIO()
            df_noticias[cols_fato].to_csv(output, sep='\t', header=False, index=False)
            output.seek(0)
            
            with conn.connection.cursor() as cursor:
                cursor.copy_expert("COPY temp_news (titulo, resumo, url, data_publicacao, sentimento_api_score, sentimento_api_label) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t')", output)
            
            conn.execute(text("""
                INSERT INTO fato_noticias (titulo, resumo, url, data_publicacao, sentimento_api_score, sentimento_api_label)
                SELECT titulo, resumo, url, data_publicacao, sentimento_api_score, sentimento_api_label
                FROM temp_news
                ON CONFLICT (url) DO NOTHING;
            """))
            conn.execute(text("DROP TABLE temp_news"))
            

            urls = tuple(df_noticias['url'].tolist())
            if not urls:
                return

            query_ids = text("SELECT id_noticia, url FROM fato_noticias WHERE url IN :urls")
            df_ids = pd.read_sql(query_ids, conn, params={"urls": urls})
            
            
            if not df_ids.empty:
                df_ids['id_acao'] = id_acao
                
                df_ids['relevancia_score'] = 0.5 

                conn.execute(text("CREATE TEMPORARY TABLE temp_links (LIKE link_noticias_acoes INCLUDING DEFAULTS)"))
                
                output_links = StringIO()
                df_ids[['id_noticia', 'id_acao', 'relevancia_score']].to_csv(output_links, sep='\t', header=False, index=False)
                output_links.seek(0)
                
                with conn.connection.cursor() as cursor:
                    cursor.copy_expert("COPY temp_links (id_noticia, id_acao, relevancia_score) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t')", output_links)
                
                conn.execute(text("""
                    INSERT INTO link_noticias_acoes (id_noticia, id_acao, relevancia_score)
                    SELECT id_noticia, id_acao, relevancia_score FROM temp_links
                    ON CONFLICT (id_noticia, id_acao) DO NOTHING;
                """))
                conn.execute(text("DROP TABLE temp_links"))
                
            conn.commit()
            constantes.logger.info("Carga de notícias e vínculos finalizada com sucesso.")

    except Exception as e:
        constantes.logger.error(f"Erro crítico ao salvar notícias: {e}")