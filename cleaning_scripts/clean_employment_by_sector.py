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
RAW_DIR = Path("data/raw/economy")
CLEAN_DIR = Path("data/cleaned/economy")

TABLE_PREFIX = "CPNI38"
OUT_PATH = CLEAN_DIR / "employment_by_sector.csv"

REQUIRED_COLS: List[str] = [
    "Statistic Label",
    "Census Year",
    "Ireland and Northern Ireland",
    "Broad Industry Group",
    "UNIT",
    "VALUE",
]

#filters (set to none to disable)
FILTER_STATISTIC_CONTAINS = "in employment"

#rows to drop (not part of sector composition bars)
DROP_SECTORS = {"Total at work"}


def clean_employment_by_sector(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = clean_string_column(df["Statistic Label"])
    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Broad Industry Group"] = clean_string_column(df["Broad Industry Group"])
    df["UNIT"] = clean_string_column(df["UNIT"])

    if FILTER_STATISTIC_CONTAINS is not None:
        df = df[df["Statistic Label"].str.contains(FILTER_STATISTIC_CONTAINS, case=False, na=False)]
        if df.empty:
            raise ValueError(
                "After filtering by statistic label, no rows remain. "
                "Check FILTER_STATISTIC_CONTAINS against the raw file."
            )

    df["VALUE"] = clean_numeric_column(df["VALUE"])
    df = df.dropna(subset=["VALUE"]).copy()

    #map regions
    df = map_regions(df, "Ireland and Northern Ireland", "Region")

    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)
    df = df.rename(columns={"Broad Industry Group": "Sector"})

    if DROP_SECTORS:
        df = df[~df["Sector"].isin(DROP_SECTORS)].copy()

    unit_pct = df[df["UNIT"].eq("%")].copy()
    unit_num = df[df["UNIT"].str.lower().eq("number")].copy()

    unit_pct = unit_pct.rename(columns={"VALUE": "Share"})
    unit_num = unit_num.rename(columns={"VALUE": "Persons"})

    out = unit_pct[["Year", "Region", "Sector", "Share"]].merge(
        unit_num[["Year", "Region", "Sector", "Persons"]],
        on=["Year", "Region", "Sector"],
        how="outer",
    )

    if out["Share"].isna().any() and out["Persons"].isna().any():
        raise ValueError("No usable rows found after splitting by UNIT ('%' and 'Number').")

    out = out.groupby(["Year", "Region", "Sector"], as_index=False).agg(
        {"Share": "mean", "Persons": "mean"}
    )
    out = out.sort_values(["Year", "Region", "Sector"]).reset_index(drop=True)

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_employment_by_sector(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
