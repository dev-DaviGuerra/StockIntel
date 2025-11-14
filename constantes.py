import urllib.parse
import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

API_KEY = os.getenv("API_KEY")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_PASS_ENCODED = urllib.parse.quote_plus(DB_PASS)
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

TICKER = "AAPL"
EMPRESA = "Apple Inc."

try:
    DB_STRING = f"postgresql://{DB_USER}:{DB_PASS_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    db_engine = create_engine(DB_STRING)
    print("Engine do DB criada com sucesso.")
except Exception as e:
    print(f"Erro ao criar engine do DB: {e}")
    db_engine = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stockintel_pipeline.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)