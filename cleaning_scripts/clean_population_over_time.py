# Cleans CSO/NISRA joint publication (CPNI01*) population time series into:
#   data/cleaned/demographics/population_over_time.csv

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

#constants
RAW_SUBDIR: Final[str] = "data/raw/demographics"
CLEAN_SUBDIR: Final[str] = "data/cleaned/demographics"

#accept any file starting with prefix (timestamped downloads are fine)
RAW_FILE_PREFIX: Final[str] = "CPNI01"
RAW_FILE_GLOB: Final[str] = f"{RAW_FILE_PREFIX}*.csv"

#if you want to force a specific filename, set this to e.g. "CPNI01.csv"
RAW_FORCE_FILENAME: Final[str | None] = None

CLEAN_FILENAME: Final[str] = "population_over_time.csv"

REGION_MAP: Final[dict[str, str]] = {
    "Ireland": "Republic of Ireland",
    "Northern Ireland": "Northern Ireland",
}

#optional filters: set to None to disable filtering
FILTER_STATISTIC_LABEL: Final[str | None] = "Population"
FILTER_SEX: Final[str | None] = "Both sexes"
FILTER_UNIT: Final[str | None] = "Number"


#project root detection 

def get_project_root() -> Path:
    """
    Find the project root by searching upward for a directory that contains
    both 'pages' and 'data'. This works no matter where you run the script from.
    """
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pages").exists() and (parent / "data").exists():
            return parent
    return here.parents[1]


def find_raw_file(raw_dir: Path) -> Path:
    """
    Pick the raw file to clean.
    - If RAW_FORCE_FILENAME is set and exists, use it.
    - Else pick the newest file matching RAW_FILE_GLOB (e.g. CPNI01*.csv).
    """
    if RAW_FORCE_FILENAME:
        forced = raw_dir / RAW_FORCE_FILENAME
        if not forced.exists():
            raise FileNotFoundError(f"Forced raw file not found: {forced}")
        return forced

    matches = list(raw_dir.glob(RAW_FILE_GLOB))
    if not matches:
        raise FileNotFoundError(
            f"No raw file matching '{RAW_FILE_GLOB}' found in {raw_dir}.\n"
            f"Put the downloaded CSV in {RAW_SUBDIR}/ (any filename starting with '{RAW_FILE_PREFIX}' is fine)."
        )

    newest = max(matches, key=lambda p: p.stat().st_mtime)
    return newest


def clean_population_over_time(raw_path: Path) -> pd.DataFrame:
    """
    Clean CSO/NISRA joint publication time series.

    Expected raw columns (as in your CPNI01 file):
      - Statistic Label
      - Year
      - Sex
      - Ireland and Northern Ireland
      - UNIT
      - VALUE

    Output columns:
      - Year (int)
      - Region (str): Republic of Ireland / Northern Ireland
      - Population (int)
    """
    df: pd.DataFrame = pd.read_csv(raw_path)

    required_cols = {
        "Statistic Label",
        "Year",
        "Sex",
        "Ireland and Northern Ireland",
        "UNIT",
        "VALUE",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}\n"
            f"Columns found: {list(df.columns)}"
        )

    out = df.copy()

    if FILTER_STATISTIC_LABEL is not None:
        out = out[out["Statistic Label"].astype(str).str.strip().eq(FILTER_STATISTIC_LABEL)]
    if FILTER_SEX is not None:
        out = out[out["Sex"].astype(str).str.strip().eq(FILTER_SEX)]
    if FILTER_UNIT is not None:
        out = out[out["UNIT"].astype(str).str.strip().eq(FILTER_UNIT)]

    out = out.rename(
        columns={
            "Ireland and Northern Ireland": "Region",
            "VALUE": "Population",
        }
    )

    out["Region"] = out["Region"].astype(str).str.strip().map(REGION_MAP).fillna(out["Region"])
    out["Year"] = pd.to_numeric(out["Year"], errors="coerce").astype("Int64")
    out["Population"] = pd.to_numeric(out["Population"], errors="coerce").astype("Int64")

    out = out.dropna(subset=["Year", "Population"]).copy()
    out["Year"] = out["Year"].astype(int)
    out["Population"] = out["Population"].astype(int)

    #keep only ROI and NI rows
    out = out[out["Region"].isin(REGION_MAP.values())]
    out = out.sort_values(["Region", "Year"]).reset_index(drop=True)

    #ensure 1 row per (Region, Year)
    if out.duplicated(subset=["Region", "Year"]).any():
        out = out.drop_duplicates(subset=["Region", "Year"], keep="last")

    cleaned = out[["Year", "Region", "Population"]].reset_index(drop=True)
    return cleaned


def main() -> None:
    project_root = get_project_root()

    raw_dir = project_root / RAW_SUBDIR
    clean_dir = project_root / CLEAN_SUBDIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    raw_path = find_raw_file(raw_dir)
    cleaned = clean_population_over_time(raw_path)

    out_path = clean_dir / CLEAN_FILENAME
    cleaned.to_csv(out_path, index=False)

    print(f"Read raw:     {raw_path}")
    print(f"Wrote cleaned:{out_path}")
    print("\nPreview:")
    print(cleaned.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
