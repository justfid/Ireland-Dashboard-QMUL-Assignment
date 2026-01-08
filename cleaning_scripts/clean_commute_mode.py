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

TABLE_PREFIX = "CPNI48"
OUT_PATH = CLEAN_DIR / "commute_mode.csv"

REQUIRED_COLS: List[str] = [
    "Statistic Label",
    "Census Year",
    "Ireland and Northern Ireland",
    "Means of Travel",
    "UNIT",
    "VALUE",
]

DROP_MODES = {"All means of travel"}


def clean_commute_mode(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = clean_string_column(df["Statistic Label"])
    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Means of Travel"] = clean_string_column(df["Means of Travel"])
    df["UNIT"] = clean_string_column(df["UNIT"])

    df["VALUE"] = clean_numeric_column(df["VALUE"])
    df = df.dropna(subset=["VALUE"]).copy()

    df = map_regions(df, "Ireland and Northern Ireland", "Region")

    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)
    df = df.rename(columns={"Means of Travel": "Mode"})

    if DROP_MODES:
        df = df[~df["Mode"].isin(DROP_MODES)].copy()

    pct = df[df["UNIT"].eq("%")].copy()
    num = df[df["UNIT"].str.lower().eq("number")].copy()

    pct = pct.rename(columns={"VALUE": "Share"})
    num = num.rename(columns={"VALUE": "Persons"})

    out = pct[["Year", "Region", "Mode", "Share"]].merge(
        num[["Year", "Region", "Mode", "Persons"]],
        on=["Year", "Region", "Mode"],
        how="outer",
    )

    if out["Share"].isna().all() and out["Persons"].isna().all():
        raise ValueError("No usable rows found after splitting by UNIT ('%' and 'Number').")

    out["Share"] = pd.to_numeric(out["Share"], errors="coerce")
    out["Persons"] = pd.to_numeric(out["Persons"], errors="coerce")

    out = out.groupby(["Year", "Region", "Mode"], as_index=False).agg(
        {"Share": "mean", "Persons": "mean"}
    )
    out = out.sort_values(["Year", "Region", "Mode"]).reset_index(drop=True)

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_commute_mode(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
