"""Shared utility functions for data cleaning scripts."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Final

import pandas as pd


#constants
ROI_LABEL: Final[str] = "Republic of Ireland"
NI_LABEL: Final[str] = "Northern Ireland"
ALL_LABEL: Final[str] = "All-Island"

STANDARD_REGION_MAP: Final[dict[str, str]] = {
    "Ireland": ROI_LABEL,
    "Northern Ireland": NI_LABEL,
}


#project root detection
def get_project_root() -> Path:
    """Find the project root by searching upward for a directory that contains
    both 'pages' and 'data'. This works no matter where you run the script from.
    
    Returns:
        Path: Project root directory
    """
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pages").exists() and (parent / "data").exists():
            return parent
    return here.parents[1]


#file discovery
def find_raw_file(raw_dir: Path, prefix: str, force_filename: str | None = None) -> Path:
    """Pick the raw file to clean.
    
    Args:
        raw_dir: Directory containing raw files
        prefix: File prefix to match (e.g., "CPNI01")
        force_filename: If set and exists, use this specific filename
        
    Returns:
        Path: Path to the raw file to process
        
    Raises:
        FileNotFoundError: If no matching file is found
    """
    if force_filename:
        forced = raw_dir / force_filename
        if not forced.exists():
            raise FileNotFoundError(f"Forced raw file not found: {forced}")
        return forced

    matches = list(raw_dir.glob(f"{prefix}*.csv"))
    if not matches:
        raise FileNotFoundError(
            f"No raw file matching '{prefix}*.csv' found in {raw_dir}.\n"
            f"Put the downloaded CSV in {raw_dir}/ (any filename starting with '{prefix}' is fine)."
        )

    newest = max(matches, key=lambda p: p.stat().st_mtime)
    return newest


def latest_timestamped_file(raw_dir: Path, prefix: str) -> Path:
    """Pick the latest file matching pattern <prefix>.<YYYYMMDDThhmmss>.csv
    
    Args:
        raw_dir: Directory containing raw files
        prefix: File prefix to match
        
    Returns:
        Path: Most recent file based on timestamp
        
    Raises:
        FileNotFoundError: If no matching files found
    """
    candidates = sorted(raw_dir.glob(f"{prefix}*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No matching files found in {raw_dir} for pattern {prefix}*.csv")
    return candidates[-1]


#validation
def ensure_cols(df: pd.DataFrame, cols: Iterable[str]) -> None:
    """Validate that a DataFrame contains all required columns.
    
    Args:
        df: DataFrame to validate
        cols: Iterable of required column names
        
    Raises:
        ValueError: If any required columns are missing
    """
    cols_list = list(cols)
    missing = [c for c in cols_list if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}. Got: {list(df.columns)}")


#year parsing
def parse_census_year(census_year: str) -> int:
    """Parse census year from joint publication format.
    
    Handles formats like:
    - "2021/2022" -> 2022 (align to later year for consistency)
    - "2022" -> 2022
    - Other formats with embedded 4-digit year
    
    Args:
        census_year: Census year string from raw data
        
    Returns:
        int: 4-digit year
        
    Raises:
        ValueError: If no 4-digit year can be extracted
    """
    s = str(census_year).strip()
    
    #handle slash-separated years (e.g., "2021/2022")
    if "/" in s:
        tail = s.split("/")[-1]
        digits = "".join(ch for ch in tail if ch.isdigit())
        if len(digits) == 4:
            return int(digits)
    
    #extract any 4-digit sequence
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 4:
        return int(digits)
    
    raise ValueError(f"Could not parse Census Year '{census_year}' into a 4-digit year.")

#region mapping
def map_regions(df: pd.DataFrame, source_col: str, target_col: str = "Region", 
                region_map: dict[str, str] = STANDARD_REGION_MAP) -> pd.DataFrame:
    """Map region names from raw data to standardized names.
    
    Args:
        df: DataFrame to process
        source_col: Column name containing raw region names
        target_col: Column name for mapped regions (default: "Region")
        region_map: Mapping from raw to standard names (default: STANDARD_REGION_MAP)
        
    Returns:
        pd.DataFrame: DataFrame with mapped regions
        
    Raises:
        ValueError: If any regions cannot be mapped
    """
    df = df.copy()
    df[target_col] = df[source_col].map(region_map)
    
    if df[target_col].isna().any():
        unknown = sorted(df.loc[df[target_col].isna(), source_col].unique())
        raise ValueError(f"Unknown region labels encountered: {unknown}")
    
    return df


#data cleaning
def clean_string_column(series: pd.Series) -> pd.Series:
    """Standardize string column by converting to string and stripping whitespace.
    
    Args:
        series: Pandas series to clean
        
    Returns:
        pd.Series: Cleaned series
    """
    return series.astype(str).str.strip()


def clean_numeric_column(series: pd.Series, drop_na: bool = False) -> pd.Series:
    """Convert column to numeric type, coercing errors.
    
    Args:
        series: Pandas series to convert
        drop_na: If True, return series with NaN values dropped
        
    Returns:
        pd.Series: Series with numeric values
    """
    result = pd.to_numeric(series, errors="coerce")
    return result.dropna() if drop_na else result

