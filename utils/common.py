"""Shared utility functions for all dashboard pages."""

from __future__ import annotations

from typing import List

import pandas as pd


#validation
def ensure_cols(df: pd.DataFrame, cols: List[str]) -> None:
    """Validate that a DataFrame contains all required columns.
    
    Args:
        df: DataFrame to validate
        cols: List of required column names
        
    Raises:
        ValueError: If any required columns are missing
    """
    if not set(cols).issubset(df.columns):
        raise ValueError(f"Expected columns {cols}, got {list(df.columns)}")


#data cleaning
def clean_region_column(series: pd.Series) -> pd.Series:
    """Standardize region names by stripping whitespace.
    
    Args:
        series: Pandas series containing region names
        
    Returns:
        Series with cleaned region names
    """
    return series.astype(str).str.strip()


def clean_year_column(series: pd.Series) -> pd.Series:
    """Convert year column to integer type.
    
    Args:
        series: Pandas series containing year values
        
    Returns:
        Series with integer year values
    """
    return pd.to_numeric(series, errors="coerce").astype(int)


def clean_numeric_column(series: pd.Series) -> pd.Series:
    """Convert column to numeric type, coercing errors.
    
    Args:
        series: Pandas series to convert
        
    Returns:
        Series with numeric values
    """
    return pd.to_numeric(series, errors="coerce")


#constants
ROI = "Republic of Ireland"
NI = "Northern Ireland"
ALL = "All-Island"
REGIONS: List[str] = [ROI, NI]
ALL_REGIONS: List[str] = [ROI, NI, ALL]
