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
RAW_DIR = Path("data/raw/economy")
CLEAN_DIR = Path("data/cleaned/economy")

TABLE_PREFIX = "CPNI36"
OUT_PATH = CLEAN_DIR / "unemployment_rate.csv"

REQUIRED_COLS: List[str] = [
    "Statistic Label",
    "Census Year",
    "Ireland and Northern Ireland",
    "Sex",
    "UNIT",
    "VALUE",
]


def clean_unemployment_ilo(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = clean_string_column(df["Statistic Label"])
    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Sex"] = clean_string_column(df["Sex"])
    df["UNIT"] = clean_string_column(df["UNIT"])

    #filter to intended statistic only
    df = df[df["Statistic Label"].str.contains("ILO Unemployment Rate", case=False, na=False)]

    #keep only the 3 sex categories used in the publication
    sex_keep = {"Both sexes", "Male", "Female"}
    df = df[df["Sex"].isin(sex_keep)]

    #coerce value
    df["VALUE"] = clean_numeric_column(df["VALUE"])
    df = df.dropna(subset=["VALUE"])

    #unit check
    bad_units = sorted(set(df["UNIT"].unique()) - {"%"})
    if bad_units:
        raise ValueError(f"Unexpected UNIT values: {bad_units}. Expected only '%'.")

    #map region names to dashboard standard
    df = map_regions(df, "Ireland and Northern Ireland", "Region")

    #derive year int
    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)

    out = df[["Year", "Region", "Sex", "VALUE"]].rename(columns={"VALUE": "Unemployment rate"}).copy()

    #deduplicate defensively
    out = out.groupby(["Year", "Region", "Sex"], as_index=False)["Unemployment rate"].mean()

    #stable ordering
    sex_order = {"Both sexes": 0, "Male": 1, "Female": 2}
    out["_sex_order"] = out["Sex"].map(sex_order)
    out = out.sort_values(["Region", "Year", "_sex_order"]).drop(columns=["_sex_order"]).reset_index(drop=True)

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_unemployment_ilo(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()