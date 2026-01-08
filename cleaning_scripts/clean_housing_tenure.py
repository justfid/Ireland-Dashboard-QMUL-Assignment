from __future__ import annotations

from pathlib import Path
from typing import List

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
RAW_DIR = Path("data/raw/housing_education")
CLEAN_DIR = Path("data/cleaned/housing_education")

TABLE_PREFIX = "CPNI34"
OUT_PATH = CLEAN_DIR / "housing_tenure.csv"

TARGET_YEAR = 2022

REQUIRED_COLS: List[str] = [
    "Census Year",
    "Ireland and Northern Ireland",
    "Nature of Occupancy",
    "UNIT",
    "VALUE",
]

#drop totals / non-distribution rows if present
DROP_NATURE = {"All types of occupancy"}


def clean_housing_tenure(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)

    #basic cleaning
    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Nature of Occupancy"] = clean_string_column(df["Nature of Occupancy"])
    df["UNIT"] = clean_string_column(df["UNIT"])

    df["VALUE"] = clean_numeric_column(df["VALUE"])
    df = df.dropna(subset=["VALUE"]).copy()

    #map regions
    df = map_regions(df, "Ireland and Northern Ireland", "Region")

    #year handling
    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)
    df = df[df["Year"] == TARGET_YEAR].copy()
    if df.empty:
        raise ValueError(f"No rows remain after filtering to Year == {TARGET_YEAR}.")

    # rename category
    df = df.rename(columns={"Nature of Occupancy": "Nature"})

    #drop totals if present
    if DROP_NATURE:
        df = df[~df["Nature"].isin(DROP_NATURE)].copy()

    #split percentage and absolute
    unit_pct = df[df["UNIT"].eq("%")].copy()
    unit_num = df[df["UNIT"].str.lower().eq("number")].copy()

    unit_pct = unit_pct.rename(columns={"VALUE": "Percentage"})
    unit_num = unit_num.rename(columns={"VALUE": "Absolute"})

    out = unit_pct[["Year", "Region", "Nature", "Percentage"]].merge(
        unit_num[["Year", "Region", "Nature", "Absolute"]],
        on=["Year", "Region", "Nature"],
        how="outer",
    )

    if out["Percentage"].isna().all() and out["Absolute"].isna().all():
        raise ValueError("No usable rows found after splitting by UNIT ('%' and 'Number').")

    #safety dedupe
    out = out.groupby(["Year", "Region", "Nature"], as_index=False).agg(
        {"Percentage": "mean", "Absolute": "mean"}
    )

    out = out.sort_values(["Year", "Region", "Nature"]).reset_index(drop=True)
    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_housing_tenure(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
