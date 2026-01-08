from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


#constants
RAW_DIR = Path("data/raw/housing_education")
CLEAN_DIR = Path("data/cleaned/housing_education")

TABLE_PREFIX = "CPNI11"
OUT_PATH = CLEAN_DIR / "household_size.csv"

REGION_MAP = {
    "Ireland": "Republic of Ireland",
    "Northern Ireland": "Northern Ireland",
}

HOUSEHOLD_SIZE_MAP = {
    "Households - 1 person household": "1",
    "Households - 2 person household": "2",
    "Households - 3 person household": "3",
    "Households - 4 person household": "4",
    "Households - 5 or more person household": "5+",
}


def _latest_timestamped_file(raw_dir: Path, prefix: str) -> Path:
    """
    Picks the latest file like: <prefix>.<YYYYMMDDThhmmss>.csv
    Falls back to newest mtime among prefix-matching csvs.
    """
    candidates = sorted(raw_dir.glob(f"{prefix}*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No raw files found in {raw_dir} matching {prefix}*.csv")

    def _stamp(p: Path) -> str:
        #prefer embedded timestamp if present, else mtime key
        return p.name

    #try lexicographic (works for timestamped names), else mtime
    best = max(candidates, key=lambda p: (_stamp(p), p.stat().st_mtime))
    return best


def _parse_census_year(s: str) -> int:
    #expects e.g. "2001/2002" -> 2002
    parts = str(s).split("/")
    last = parts[-1]
    return int(last)


def clean_household_size(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)

    expected = {
        "Statistic Label",
        "Census Year",
        "Household Size",
        "Ireland and Northern Ireland",
        "UNIT",
        "VALUE",
    }
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Missing expected columns: {sorted(missing)}")

    #drop total row 
    df = df[df["Household Size"] != "All private households"].copy()

    #map + select
    df["region"] = df["Ireland and Northern Ireland"].map(REGION_MAP)
    if df["region"].isna().any():
        bad = sorted(df.loc[df["region"].isna(), "Ireland and Northern Ireland"].unique().tolist())
        raise ValueError(f"Unmapped region labels: {bad}")

    df["censusyear"] = df["Census Year"].map(_parse_census_year).astype(int)

    df["household_size"] = df["Household Size"].map(HOUSEHOLD_SIZE_MAP)
    if df["household_size"].isna().any():
        bad = sorted(df.loc[df["household_size"].isna(), "Household Size"].unique().tolist())
        raise ValueError(f"Unmapped household size labels: {bad}")

    #pivot UNIT -> columns
    #UNIT is "Number" or "%"
    df["UNIT"] = df["UNIT"].replace({"%": "percentage", "Number": "number"})
    if not set(df["UNIT"].unique()).issubset({"number", "percentage"}):
        raise ValueError(f"Unexpected UNIT values: {sorted(df['UNIT'].unique().tolist())}")

    out = (
        df[["censusyear", "region", "household_size", "UNIT", "VALUE"]]
        .rename(columns={"VALUE": "value"})
        .pivot_table(
            index=["censusyear", "region", "household_size"],
            columns="UNIT",
            values="value",
            aggfunc="sum",
        )
        .reset_index()
    )

    #ensure both metrics exist for all rows
    if "number" not in out.columns or "percentage" not in out.columns:
        raise ValueError(f"Pivot failed; got columns: {list(out.columns)}")

    #types
    out["percentage"] = pd.to_numeric(out["percentage"], errors="coerce")
    out["number"] = pd.to_numeric(out["number"], errors="coerce")

    if out[["percentage", "number"]].isna().any().any():
        raise ValueError("Found NaNs in number/percentage after coercion")

    #number should be whole counts (allow tiny float noise)
    out["number"] = out["number"].round(0).astype(int)

    #sanity: percentages sum to ~100 per region/year
    check = out.groupby(["region", "censusyear"])["percentage"].sum().round(1)
    if not all(check.between(99.5, 100.5)):
        raise ValueError(f"Percentages do not sum to ~100 by region/year: {check.to_dict()}")

    #final column order
    out = out[["censusyear", "household_size", "region", "number", "percentage"]].copy()

    #stable sort for diffs
    size_order = pd.CategoricalDtype(["1", "2", "3", "4", "5+"], ordered=True)
    out["household_size"] = out["household_size"].astype(size_order)
    out = out.sort_values(["censusyear", "region", "household_size"]).reset_index(drop=True)

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = _latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_household_size(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
