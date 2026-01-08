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

TABLE_PREFIX = "CPNI30"
OUT_PATH = CLEAN_DIR / "housing_type.csv"

REQUIRED_COLS: List[str] = [
    "Statistic Label",
    "Census Year",
    "Ireland and Northern Ireland",
    "Type of Household",
    "UNIT",
    "VALUE",
]

#rows to drop (not part of distribution)
DROP_TYPES = {
    "All households",
    "Not stated",
    "Unknown",
    "Unspecified",
}


def _normalise_type(label: str) -> str:
    s = str(label).strip()
    low = s.lower()

    #merge flat/apartment
    if "flat" in low or "apartment" in low:
        return "Flat / apartment"

    return s


def clean_housing_type(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = clean_string_column(df["Statistic Label"])
    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Type of Household"] = clean_string_column(df["Type of Household"])
    df["UNIT"] = clean_string_column(df["UNIT"])

    df["VALUE"] = clean_numeric_column(df["VALUE"])
    df = df.dropna(subset=["VALUE"]).copy()

    df = map_regions(df, "Ireland and Northern Ireland", "Region")

    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)
    df = df.rename(columns={"Type of Household": "Type"})

    #drop totals and zero-information categories
    df = df[~df["Type"].isin(DROP_TYPES)].copy()

    #normalise categories
    df["Type"] = df["Type"].apply(_normalise_type)

    # keep both % and Number, pivot UNIT -> columns
    unit_map = {"%": "Percentage", "Number": "Absolute"}
    df["UNIT_M"] = df["UNIT"].map(unit_map)
    if df["UNIT_M"].isna().any():
        bad = sorted(df.loc[df["UNIT_M"].isna(), "UNIT"].unique())
        raise ValueError(f"Unexpected UNIT values encountered: {bad}")

    out = (
        df[["Year", "Region", "Type", "UNIT_M", "VALUE"]]
        .rename(columns={"UNIT_M": "unit", "VALUE": "value"})
        .pivot_table(
            index=["Year", "Region", "Type"],
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

    #re-aggregate after merging categories (pivot already sums; this is just for safety if duplicates exist)
    out = (
        out.groupby(["Year", "Region", "Type"], as_index=False)[["Percentage", "Absolute"]]
        .sum()
        .sort_values(["Year", "Region", "Type"])
        .reset_index(drop=True)
    )

    #sanity check: percentages should sum to ~100 per region/year
    check = out.groupby(["Region", "Year"])["Percentage"].sum().round(1)
    if not all(check.between(99.0, 101.0)):
        raise ValueError(f"Housing type percentages do not sum to ~100 by region/year: {check.to_dict()}")

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_housing_type(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
