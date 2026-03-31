"""
StockIntel — ETL Data Validation
Validações de qualidade antes de persistir no banco de dados.
"""

import pandas as pd
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when a critical data quality check fails."""
    pass


# ─── Price Validation ─────────────────────────────────────────────────────────

def validar_precos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates and cleans a price DataFrame.
    Raises DataValidationError on unrecoverable issues.
    Returns cleaned DataFrame.
    """
    tag = "[validar_precos]"

    if df is None or df.empty:
        raise DataValidationError(f"{tag} DataFrame vazio ou nulo.")

    required = {"data_preco", "abertura", "maximo", "minimo", "fechamento", "volume"}
    missing  = required - set(df.columns)
    if missing:
        raise DataValidationError(f"{tag} Colunas ausentes: {missing}")

    original_len = len(df)

    # ── Tipo de dado ──────────────────────────────────────────────────────────
    df["data_preco"] = pd.to_datetime(df["data_preco"], errors="coerce")
    for col in ["abertura", "maximo", "minimo", "fechamento", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Nulos ─────────────────────────────────────────────────────────────────
    nulls = df[list(required)].isnull().sum()
    if nulls.any():
        logger.warning(f"{tag} Nulos encontrados — removendo linhas: {nulls[nulls > 0].to_dict()}")
        df = df.dropna(subset=list(required))

    if df.empty:
        raise DataValidationError(f"{tag} Nenhuma linha válida após remoção de nulos.")

    # ── Sanidade de preços ────────────────────────────────────────────────────
    bad_range = df["maximo"] < df["minimo"]
    if bad_range.any():
        logger.warning(f"{tag} {bad_range.sum()} linhas com Máximo < Mínimo — removendo.")
        df = df[~bad_range]

    bad_prices = (df[["abertura", "maximo", "minimo", "fechamento"]] <= 0).any(axis=1)
    if bad_prices.any():
        logger.warning(f"{tag} {bad_prices.sum()} linhas com preços <= 0 — removendo.")
        df = df[~bad_prices]

    bad_vol = df["volume"] < 0
    if bad_vol.any():
        logger.warning(f"{tag} {bad_vol.sum()} linhas com volume negativo — zerado para 0.")
        df.loc[bad_vol, "volume"] = 0

    # ── Duplicatas ────────────────────────────────────────────────────────────
    dupes = df.duplicated(subset=["data_preco"], keep="last")
    if dupes.any():
        logger.warning(f"{tag} {dupes.sum()} datas duplicadas — mantendo mais recente.")
        df = df[~dupes]

    dropped = original_len - len(df)
    if dropped > 0:
        logger.info(f"{tag} {dropped} linhas removidas na validação. Restantes: {len(df)}")
    else:
        logger.info(f"{tag} OK — {len(df)} registros válidos.")

    return df.reset_index(drop=True)


# ─── News Validation ──────────────────────────────────────────────────────────

def validar_noticias(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates and cleans a news DataFrame.
    Raises DataValidationError on unrecoverable issues.
    Returns cleaned DataFrame.
    """
    tag = "[validar_noticias]"

    if df is None or df.empty:
        raise DataValidationError(f"{tag} DataFrame vazio ou nulo.")

    required = {"titulo", "url", "data_publicacao"}
    missing  = required - set(df.columns)
    if missing:
        raise DataValidationError(f"{tag} Colunas ausentes: {missing}")

    original_len = len(df)

    # ── URLs nulas ou vazias ──────────────────────────────────────────────────
    df = df[df["url"].notna() & (df["url"].str.strip() != "")]
    if df.empty:
        raise DataValidationError(f"{tag} Nenhuma notícia com URL válida.")

    # ── Títulos nulos ─────────────────────────────────────────────────────────
    df = df[df["titulo"].notna() & (df["titulo"].str.strip() != "")]

    # ── Datas ─────────────────────────────────────────────────────────────────
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors="coerce")
    bad_dates = df["data_publicacao"].isnull().sum()
    if bad_dates:
        logger.warning(f"{tag} {bad_dates} datas inválidas — removendo.")
        df = df[df["data_publicacao"].notna()]

    # ── Duplicatas por URL ────────────────────────────────────────────────────
    dupes = df.duplicated(subset=["url"], keep="first")
    if dupes.any():
        logger.warning(f"{tag} {dupes.sum()} URLs duplicadas — mantendo primeira.")
        df = df[~dupes]

    dropped = original_len - len(df)
    if dropped > 0:
        logger.info(f"{tag} {dropped} linhas removidas. Restantes: {len(df)}")
    else:
        logger.info(f"{tag} OK — {len(df)} notícias válidas.")

    return df.reset_index(drop=True)


# ─── Schema Report ────────────────────────────────────────────────────────────

def relatorio_qualidade(df: pd.DataFrame, nome: str) -> dict:
    """Returns a data quality summary dict for logging/monitoring."""
    return {
        "dataset"      : nome,
        "total_rows"   : len(df),
        "null_counts"  : df.isnull().sum().to_dict(),
        "duplicate_rows": int(df.duplicated().sum()),
        "dtypes"       : {c: str(t) for c, t in df.dtypes.items()},
    }
