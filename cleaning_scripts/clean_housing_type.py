from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd


#constants
RAW_DIR = Path("data/raw/living_conditions")
CLEAN_DIR = Path("data/cleaned/living_conditions")

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


def _normalise_type(label: str) -> str:
    s = str(label).strip()
    low = s.lower()

    #merge flat/apartment
    if "flat" in low or "apartment" in low:
        return "Flat / apartment"

    return s


def clean_housing_type(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    _ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = df["Statistic Label"].astype(str).str.strip()
    df["Census Year"] = df["Census Year"].astype(str).str.strip()
    df["Ireland and Northern Ireland"] = df["Ireland and Northern Ireland"].astype(str).str.strip()
    df["Type of Household"] = df["Type of Household"].astype(str).str.strip()
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
    df = df.rename(columns={"Type of Household": "Type"})

    #drop totals and zero-information categories
    df = df[~df["Type"].isin(DROP_TYPES)].copy()

    #normalise categories
    df["Type"] = df["Type"].apply(_normalise_type)

    #percentages only
    df = df[df["UNIT"].eq("%")].copy()
    if df.empty:
        raise ValueError("No percentage rows found (UNIT == '%').")

    df = df.rename(columns={"VALUE": "Percentage"})

    #re-aggregate after merging categories
    out = (
        df.groupby(["Year", "Region", "Type"], as_index=False)["Percentage"]
        .sum()
        .sort_values(["Year", "Region", "Type"])
        .reset_index(drop=True)
    )

    #sanity check: should sum to ~100 per region
    check = out.groupby("Region")["Percentage"].sum().round(1)
    if not all(check.between(99.0, 101.0)):
        raise ValueError(
            f"Housing type percentages do not sum to 100 by region: {check.to_dict()}"
        )

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = _latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_housing_type(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
