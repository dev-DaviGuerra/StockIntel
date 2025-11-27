# 🦅 StockIntel: Inteligência de Mercado com IA

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://dev-daviguerra-stockintel-app-0ooopx.streamlit.app/)

Projeto End-to-End de Engenharia de Dados & NLP
Monitorização de ações, análise de risco (VaR) e sentimento de notícias em tempo real utilizando Inteligência Artificial.

## 🧠 Sobre o Projeto

O StockIntel é uma solução completa de dados que automatiza a recolha, processamento e análise de informações financeiras. Diferente de dashboards comuns que apenas mostram preços, o StockIntel utiliza Inteligência Artificial (Transformers) para ler notícias do mercado e classificar o sentimento (Otimista/Pessimista/Neutro), além de calcular métricas estatísticas de risco.

## 🎯 Principais Funcionalidades

ETL Robusto: Recolha automática de preços e notícias via API (Alpha Vantage) com tratamento de erros e backoff.

Data Warehouse na Nuvem: Armazenamento estruturado em PostgreSQL (hospedado no Neon.tech).

Inteligência Artificial: Análise de sentimento de notícias utilizando o modelo FinBERT (Hugging Face), especializado em finanças.

Gestão de Risco: Cálculo automático de Value at Risk (VaR 95%) e Volatilidade Anualizada.

Dashboard Interativo: Visualização de dados em tempo real com Streamlit e Plotly.

## 📸 Screenshots

1. Dashboard Principal

<img width="1900" height="925" alt="Captura de tela 2025-11-27 145846" src="https://github.com/user-attachments/assets/729ec294-ed17-4d54-a6a2-7f6130d98d89" />


2. Análise de Sentimento com IA

<img width="1872" height="1065" alt="Captura de tela 2025-11-27 150002" src="https://github.com/user-attachments/assets/98e12cda-6afd-410b-812b-f4eb5d88fae0" />


## 🛠️ Arquitetura Técnica

Stack Tecnológica

- Linguagem: Python 3.12

- Banco de Dados: PostgreSQL (Neon Serverless)

- Orquestração: Scripts Python modulares (main.py)

- Frontend: Streamlit Cloud

- IA/NLP: PyTorch + Transformers (Hugging Face)

- Bibliotecas: Pandas, SQLAlchemy, Plotly, Python-dotenv
