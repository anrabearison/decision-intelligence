"""
Module de profiling - Phase 1a.
"""
import pandas as pd


def descriptive_stats(series: pd.Series) -> dict:
    return {
        "mean": float(series.mean()),
        "std_dev": float(series.std()),
        "min": series.min().item() if hasattr(series.min(), "item") else series.min(),
        "max": series.max().item() if hasattr(series.max(), "item") else series.max(),
        "median": float(series.median()),
    }


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    numeric_df = df.select_dtypes(include="number")
    return numeric_df.corr()
