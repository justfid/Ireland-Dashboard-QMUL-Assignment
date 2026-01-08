from __future__ import annotations

import sys
from pathlib import Path
from typing import List

# Add project root to path for utils import
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
RAW_DIR = Path("data/raw/social_indicators")
CLEAN_DIR = Path("data/cleaned/social_indicators")

TABLE_PREFIX = "CPNI09"
OUT_PATH = CLEAN_DIR / "household_composition.csv"

REQUIRED_COLS: List[str] = [
    "Statistic Label",
    "Census Year",
    "Ireland and Northern Ireland",
    "Household Composition",
    "UNIT",
    "VALUE",
]

#rows to drop (totals)
DROP_COMPOSITIONS = {
    "All household types",
}


def clean_household_composition(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = clean_string_column(df["Statistic Label"])
    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Household Composition"] = clean_string_column(df["Household Composition"])
    df["UNIT"] = clean_string_column(df["UNIT"])

    df["VALUE"] = clean_numeric_column(df["VALUE"])
    df = df.dropna(subset=["VALUE"]).copy()

    df = map_regions(df, "Ireland and Northern Ireland", "Region")

    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)
    df = df.rename(columns={"Household Composition": "Composition"})

    #drop totals
    df = df[~df["Composition"].isin(DROP_COMPOSITIONS)].copy()

    #validate units
    unit_map = {"%": "Percentage", "Number": "Absolute"}
    df["UNIT_M"] = df["UNIT"].map(unit_map)
    if df["UNIT_M"].isna().any():
        bad = sorted(df.loc[df["UNIT_M"].isna(), "UNIT"].unique())
        raise ValueError(f"Unexpected UNIT values encountered: {bad}")

    #pivot UNIT -> columns
    out = (
        df[["Year", "Region", "Composition", "UNIT_M", "VALUE"]]
        .rename(columns={"UNIT_M": "unit", "VALUE": "value"})
        .pivot_table(
            index=["Year", "Region", "Composition"],
            columns="unit",
            values="value",
            aggfunc="sum",
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

    #sanity check: percentages should sum to ~100 per region/year
    check = out.groupby(["Region", "Year"])["Percentage"].sum().round(1)
    if not all(check.between(99.0, 101.0)):
        raise ValueError(f"Household composition percentages do not sum to ~100 by region/year: {check.to_dict()}")

    out = out.sort_values(["Year", "Region", "Composition"]).reset_index(drop=True)

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_household_composition(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
