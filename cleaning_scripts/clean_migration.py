#!/usr/bin/env python3
#cleaning script for cpni16 - top 10 places of birth

from __future__ import annotations

import sys
from pathlib import Path
from typing import List

#add project root to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from utils.cleaning import (
    ensure_cols,
    latest_timestamped_file,
    parse_census_year,
    map_regions,
    clean_string_column,
    clean_numeric_column,
)

#constants
RAW_DIR = Path("data/raw/cultural_identity")
CLEAN_DIR = Path("data/cleaned/cultural_identity")

TABLE_PREFIX = "CPNI16"
OUT_PATH = CLEAN_DIR / "migration.csv"

REQUIRED_COLS: List[str] = [
    "Statistic Label",
    "Census Year",
    "Ireland and Northern Ireland",
    "Top 10 Places of Birth",
    "UNIT",
    "VALUE",
]

DROP_COUNTRIES = {"All countries"}


def clean_migration(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)
    
    #filter out aggregate
    df = df[~df["Top 10 Places of Birth"].isin(DROP_COUNTRIES)].copy()
    
    #clean string columns
    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Top 10 Places of Birth"] = clean_string_column(df["Top 10 Places of Birth"])
    df["UNIT"] = clean_string_column(df["UNIT"])
    
    #clean numeric column
    df["VALUE"] = clean_numeric_column(df["VALUE"])
    df = df.dropna(subset=["VALUE"]).copy()
    
    #map regions
    df = map_regions(df, "Ireland and Northern Ireland", "Region")
    
    #parse census year
    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)
    
    #rename for clarity
    df = df.rename(columns={"Top 10 Places of Birth": "Country"})
    
    #validate units
    unit_map = {"%": "Percentage", "Number": "Absolute"}
    df["UNIT_M"] = df["UNIT"].map(unit_map)
    if df["UNIT_M"].isna().any():
        bad = sorted(df.loc[df["UNIT_M"].isna(), "UNIT"].unique())
        raise ValueError(f"Unexpected UNIT values encountered: {bad}")
    
    #pivot UNIT -> columns
    out = (
        df[["Year", "Region", "Country", "UNIT_M", "VALUE"]]
        .rename(columns={"UNIT_M": "unit", "VALUE": "value"})
        .pivot_table(
            index=["Year", "Region", "Country"],
            columns="unit",
            values="value",
            aggfunc="first",
        )
        .reset_index()
    )
    
    if "Percentage" not in out.columns or "Absolute" not in out.columns:
        raise ValueError(f"Expected both Percentage and Absolute after pivot; got: {list(out.columns)}")
    
    out["Percentage"] = pd.to_numeric(out["Percentage"], errors="coerce")
    out["Absolute"] = pd.to_numeric(out["Absolute"], errors="coerce")
    
    if out[["Percentage", "Absolute"]].isna().any().any():
        raise ValueError("Found NaNs in Percentage/Absolute after pivot + coercion")
    
    out["Absolute"] = out["Absolute"].round(0).astype(int)
    
    out = out.sort_values(["Year", "Region", "Country"]).reset_index(drop=True)
    
    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    
    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_migration(raw_path)
    
    cleaned.to_csv(OUT_PATH, index=False)
    print(f"✅ Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
