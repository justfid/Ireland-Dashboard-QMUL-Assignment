from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd


#constants
RAW_DIR = Path("data/raw/living_conditions")
CLEAN_DIR = Path("data/cleaned/living_conditions")

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


def _ensure_cols(df: pd.DataFrame, cols: Iterable[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}. Got: {list(df.columns)}")


def _latest_timestamped_file(raw_dir: Path, prefix: str) -> Path:
    candidates = sorted(raw_dir.glob(f"{prefix}*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No matching files found in {raw_dir} for pattern {prefix}*.csv")
    return candidates[-1]


def _parse_year_to_int(census_year: str) -> int:
    s = str(census_year).strip()
    if "/" in s:
        tail = s.split("/")[-1]
        digits = "".join(ch for ch in tail if ch.isdigit())
        if len(digits) == 4:
            return int(digits)
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 4:
        return int(digits)
    raise ValueError(f"Could not parse Census Year '{census_year}' into a 4-digit year.")


def clean_housing_tenure(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    _ensure_cols(df, REQUIRED_COLS)

    #basic cleaning
    df["Census Year"] = df["Census Year"].astype(str).str.strip()
    df["Ireland and Northern Ireland"] = df["Ireland and Northern Ireland"].astype(str).str.strip()
    df["Nature of Occupancy"] = df["Nature of Occupancy"].astype(str).str.strip()
    df["UNIT"] = df["UNIT"].astype(str).str.strip()

    df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
    df = df.dropna(subset=["VALUE"]).copy()

    #map regions
    region_map = {
        "Ireland": "Republic of Ireland",
        "Northern Ireland": "Northern Ireland",
    }
    df["Region"] = df["Ireland and Northern Ireland"].map(region_map)
    if df["Region"].isna().any():
        unknown = sorted(df.loc[df["Region"].isna(), "Ireland and Northern Ireland"].unique())
        raise ValueError(f"Unknown region labels encountered: {unknown}")

    #year handling
    df["Year"] = df["Census Year"].apply(_parse_year_to_int).astype(int)
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

    raw_path = _latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_housing_tenure(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
