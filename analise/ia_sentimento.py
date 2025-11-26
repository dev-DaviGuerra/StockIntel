import pandas as pd
from sqlalchemy import text
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import torch.nn.functional as F
import constantes

NOME_MODELO = "ProsusAI/finbert"

def carregar_modelo():
    constantes.logger.info("Carregando cérebro da IA (FinBERT)...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(NOME_MODELO)
        model = AutoModelForSequenceClassification.from_pretrained(NOME_MODELO)
        return tokenizer, model
    except Exception as e:
        constantes.logger.critical(f"Erro ao baixar modelo de IA: {e}")
        return None, None

def prever_sentimento(texto, tokenizer, model):
    try:
        inputs = tokenizer(texto, return_tensors="pt", padding=True, truncation=True, max_length=512)
        
        with torch.no_grad():
            outputs = model(**inputs)
        
        probs = F.softmax(outputs.logits, dim=-1)
        id_classe = torch.argmax(probs).item()
        score = probs[0][id_classe].item()
        
        labels_map = {0: "positive", 1: "negative", 2: "neutral"}
        return labels_map[id_classe], score

    except Exception as e:
        constantes.logger.error(f"Erro ao analisar texto: {e}")
        return None, None

def processar_novas_noticias(engine):
    constantes.logger.info("Buscando notícias pendentes de análise de IA...")
    
    try:
        with engine.connect() as conn:
            query = text("""
                SELECT id_noticia, titulo 
                FROM fato_noticias 
                WHERE sentimento_ia_label IS NULL 
                LIMIT 50
            """)
            df_pendentes = pd.read_sql(query, conn)
            
            if df_pendentes.empty:
                constantes.logger.info("Nenhuma notícia pendente. A IA pode descansar.")
                return

            constantes.logger.info(f"{len(df_pendentes)} notícias encontradas. Acordando a IA...")
            
            tokenizer, model = carregar_modelo()
            if not tokenizer: return

            updates = []
            for index, row in df_pendentes.iterrows():
                id_noticia = row['id_noticia']
                titulo = row['titulo']
                
                label, score = prever_sentimento(titulo, tokenizer, model)
                
                if label:
                    updates.append({
                        "id": id_noticia, 
                        "label": label, 
                        "score": score
                    })
            
            if updates:
                constantes.logger.info(f"Salvando {len(updates)} classificações no banco...")
                
                try:
                    for update in updates:
                        sql_update = text("""
                            UPDATE fato_noticias 
                            SET sentimento_ia_label = :label, 
                                sentimento_ia_score = :score 
                            WHERE id_noticia = :id
                        """)
                        conn.execute(sql_update, update)
                    
                    conn.commit()
                    constantes.logger.info("Analise de sentimento concluída e salva com sucesso!")
                    
                except Exception as e:
                    conn.rollback()
                    constantes.logger.error(f"Erro ao salvar classificações: {e}")

    except Exception as e:
        constantes.logger.error(f"Erro no processo de IA: {e}")