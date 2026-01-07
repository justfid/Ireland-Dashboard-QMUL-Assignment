from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd


#constants
RAW_DIR = Path("data/raw/living_conditions")
CLEAN_DIR = Path("data/cleaned/living_conditions")

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


#helpers
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


def _normalise_occupancy(label: str) -> str:
    s = str(label).strip().lower()

    if s.startswith("occupied"):
        return "Occupied"

    if s.startswith("unoccupied") or "vacant" in s:
        return "Vacant"

    raise ValueError(f"Unexpected housing occupancy label: '{label}'")


def clean_housing_occupancy(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    _ensure_cols(df, REQUIRED_COLS)

    df["Census Year"] = df["Census Year"].astype(str).str.strip()
    df["Ireland and Northern Ireland"] = df["Ireland and Northern Ireland"].astype(str).str.strip()
    df["Type of Housing Stock"] = df["Type of Housing Stock"].astype(str).str.strip()
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
    df = df[df["Year"] == TARGET_YEAR].copy()
    if df.empty:
        raise ValueError(f"No rows remain after filtering to Year == {TARGET_YEAR}.")

    #percentage only
    df = df[df["UNIT"].eq("%")].copy()
    if df.empty:
        raise ValueError("No percentage rows found (UNIT == '%').")

    #drop totals (not part of composition)
    if DROP_LABELS:
        df = df[~df["Type of Housing Stock"].isin(DROP_LABELS)].copy()

    df["Occupancy"] = df["Type of Housing Stock"].apply(_normalise_occupancy)
    df = df.rename(columns={"VALUE": "Percentage"})

    out = (
        df.groupby(["Year", "Region", "Occupancy"], as_index=False)["Percentage"]
        .sum()
        .sort_values(["Year", "Region", "Occupancy"])
        .reset_index(drop=True)
    )

    #sanity check: should sum to ~100 per region
    check = out.groupby("Region")["Percentage"].sum().round(1)
    if not all(check.between(99.5, 100.5)):
        raise ValueError(f"Occupancy percentages do not sum to 100 by region: {check.to_dict()}")

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = _latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_housing_occupancy(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
