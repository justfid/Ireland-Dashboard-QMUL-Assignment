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
RAW_DIR = Path("data/raw/housing_education")
CLEAN_DIR = Path("data/cleaned/housing_education")

TABLE_PREFIX = "CPNI32"
OUT_PATH = CLEAN_DIR / "housing_occupancy.csv"

TARGET_YEAR = 2022

REQUIRED_COLS: List[str] = [
    "Census Year",
    "Ireland and Northern Ireland",
    "Type of Housing Stock",
    "UNIT",
    "VALUE",
]

#drop non-distribution rows
DROP_LABELS = {"Total housing stock"}


def _normalise_occupancy(label: str) -> str:
    s = str(label).strip().lower()

    if s.startswith("occupied"):
        return "Occupied"

    if s.startswith("unoccupied") or "vacant" in s:
        return "Vacant"

    raise ValueError(f"Unexpected housing occupancy label: '{label}'")


def clean_housing_occupancy(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)

    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Type of Housing Stock"] = clean_string_column(df["Type of Housing Stock"])
    df["UNIT"] = clean_string_column(df["UNIT"])

    df["VALUE"] = clean_numeric_column(df["VALUE"])
    df = df.dropna(subset=["VALUE"]).copy()

    df = map_regions(df, "Ireland and Northern Ireland", "Region")

    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)
    df = df[df["Year"] == TARGET_YEAR].copy()
    if df.empty:
        raise ValueError(f"No rows remain after filtering to Year == {TARGET_YEAR}.")

    #drop totals (not part of composition)
    if DROP_LABELS:
        df = df[~df["Type of Housing Stock"].isin(DROP_LABELS)].copy()

    df["Occupancy"] = df["Type of Housing Stock"].apply(_normalise_occupancy)

    # keep both % and Number, pivot UNIT -> columns
    unit_map = {"%": "Percentage", "Number": "Absolute"}
    df["UNIT_M"] = df["UNIT"].map(unit_map)
    if df["UNIT_M"].isna().any():
        bad = sorted(df.loc[df["UNIT_M"].isna(), "UNIT"].unique())
        raise ValueError(f"Unexpected UNIT values encountered: {bad}")

    out = (
        df[["Year", "Region", "Occupancy", "UNIT_M", "VALUE"]]
        .rename(columns={"UNIT_M": "unit", "VALUE": "value"})
        .pivot_table(
            index=["Year", "Region", "Occupancy"],
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

    out = (
        out.sort_values(["Year", "Region", "Occupancy"])
        .reset_index(drop=True)[["Year", "Region", "Occupancy", "Percentage", "Absolute"]]
    )

    #sanity check: percentages should sum to ~100 per region (for the selected year)
    check = out.groupby("Region")["Percentage"].sum().round(1)
    if not all(check.between(99.5, 100.5)):
        raise ValueError(f"Occupancy percentages do not sum to 100 by region: {check.to_dict()}")

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_housing_occupancy(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
