from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

from utils.cleaning import (
    get_project_root,
    find_raw_file,
    parse_census_year,
    map_regions,
    clean_string_column,
    clean_numeric_column,
    STANDARD_REGION_MAP,
)

#constants
RAW_SUBDIR: Final[str] = "data/raw/economy"
CLEAN_SUBDIR: Final[str] = "data/cleaned/economy"

RAW_FILE_PREFIX: Final[str] = "CPNI53"
RAW_FORCE_FILENAME: Final[str | None] = None

CLEAN_FILENAME: Final[str] = "cross_border_commuters.csv"

FILTER_STATISTIC_CONTAINS: Final[str | None] = "cross border commuters for work"
FILTER_SEX: Final[str] = "Both sexes"
FILTER_UNIT: Final[str] = "Number"


def clean_cross_border_commuters(raw_path: Path) -> pd.DataFrame:
    df: pd.DataFrame = pd.read_csv(raw_path)

    required_cols = {
        "Statistic Label",
        "Census Year",
        "Ireland and Northern Ireland",
        "Sex",
        "Age Group",
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

    out["Statistic Label"] = clean_string_column(out["Statistic Label"])
    out["Census Year"] = clean_string_column(out["Census Year"])
    out["Ireland and Northern Ireland"] = clean_string_column(out["Ireland and Northern Ireland"])
    out["Sex"] = clean_string_column(out["Sex"])
    out["Age Group"] = clean_string_column(out["Age Group"])
    out["UNIT"] = clean_string_column(out["UNIT"])

    if FILTER_STATISTIC_CONTAINS is not None:
        out = out[out["Statistic Label"].str.contains(FILTER_STATISTIC_CONTAINS, case=False, na=False)]
        if out.empty:
            raise ValueError(
                "After filtering by statistic label, no rows remain. "
                "Check FILTER_STATISTIC_CONTAINS against the raw file."
            )

    out = out[out["Sex"].eq(FILTER_SEX)].copy()

    out = out[out["UNIT"].eq(FILTER_UNIT)].copy()
    if out.empty:
        raise ValueError("No rows remain after filtering to absolute numbers (UNIT='Number').")

    out["VALUE"] = clean_numeric_column(out["VALUE"])
    out = out.dropna(subset=["VALUE"]).copy()

    out = map_regions(out, "Ireland and Northern Ireland", "Region")

    out["Year"] = out["Census Year"].apply(parse_census_year).astype(int)
    out = out.rename(columns={"Age Group": "Age group", "VALUE": "Persons"})

    out = out[["Year", "Region", "Age group", "Persons"]].copy()
    out["Persons"] = pd.to_numeric(out["Persons"], errors="coerce").astype(int)

    out = out.groupby(["Year", "Region", "Age group"], as_index=False)["Persons"].sum()
    out = out.sort_values(["Year", "Region", "Age group"]).reset_index(drop=True)

    return out


def main() -> None:
    project_root = get_project_root()

    raw_dir = project_root / RAW_SUBDIR
    clean_dir = project_root / CLEAN_SUBDIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    raw_path = find_raw_file(raw_dir, RAW_FILE_PREFIX, RAW_FORCE_FILENAME)
    cleaned = clean_cross_border_commuters(raw_path)

    out_path = clean_dir / CLEAN_FILENAME
    cleaned.to_csv(out_path, index=False)

    print(f"Read raw:     {raw_path}")
    print(f"Wrote cleaned:{out_path}")
    print("\nPreview:")
    print(cleaned.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
