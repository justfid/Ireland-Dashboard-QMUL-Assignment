from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd


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
    #CPNI36 uses "2021/2022". We align to the later year (2022) for consistency.
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


def clean_unemployment_ilo(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    _ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = df["Statistic Label"].astype(str).str.strip()
    df["Census Year"] = df["Census Year"].astype(str).str.strip()
    df["Ireland and Northern Ireland"] = df["Ireland and Northern Ireland"].astype(str).str.strip()
    df["Sex"] = df["Sex"].astype(str).str.strip()
    df["UNIT"] = df["UNIT"].astype(str).str.strip()

    #filter to intended statistic only
    df = df[df["Statistic Label"].str.contains("ILO Unemployment Rate", case=False, na=False)]

    #keep only the 3 sex categories used in the publication
    sex_keep = {"Both sexes", "Male", "Female"}
    df = df[df["Sex"].isin(sex_keep)]

    #coerce value
    df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")
    df = df.dropna(subset=["VALUE"])

    #unit check
    bad_units = sorted(set(df["UNIT"].unique()) - {"%"})
    if bad_units:
        raise ValueError(f"Unexpected UNIT values: {bad_units}. Expected only '%'.")

    #map region names to dashboard standard
    region_map = {
        "Ireland": "Republic of Ireland",
        "Northern Ireland": "Northern Ireland",
    }
    df["Region"] = df["Ireland and Northern Ireland"].map(region_map)
    if df["Region"].isna().any():
        unknown = sorted(df.loc[df["Region"].isna(), "Ireland and Northern Ireland"].unique())
        raise ValueError(f"Unknown region labels encountered: {unknown}")

    #derive year int
    df["Year"] = df["Census Year"].apply(_parse_year_to_int).astype(int)

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

    raw_path = _latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_unemployment_ilo(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()