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

TABLE_PREFIX = "CPNI48"
OUT_PATH = CLEAN_DIR / "commute_mode.csv"

REQUIRED_COLS: List[str] = [
    "Statistic Label",
    "Census Year",
    "Ireland and Northern Ireland",
    "Means of Travel",
    "UNIT",
]

DROP_MODES = {"All means of travel"}


def clean_commute_mode(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    _ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = df["Statistic Label"].astype(str).str.strip()
    df["Census Year"] = df["Census Year"].astype(str).str.strip()
    df["Ireland and Northern Ireland"] = df["Ireland and Northern Ireland"].astype(str).str.strip()
    df["Means of Travel"] = df["Means of Travel"].astype(str).str.strip()
    df["UNIT"] = df["UNIT"].astype(str).str.strip()

    df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
    df = df.dropna(subset=["VALUE"]).copy()

    region_map = {
        "Ireland": "Republic of Ireland",
        "Northern Ireland": "Northern Ireland",
    }
    df["Region"] = df["Ireland and Northern Ireland"].map(region_map)
    if df["Region"].isna().any():
        unknown = sorted(df.loc[df["Region"].isna(), "Ireland and Northern Ireland"].unique())
        raise ValueError(f"Unknown region labels encountered: {unknown}")

    df["Year"] = df["Census Year"].apply(_parse_year_to_int).astype(int)
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
