from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd


#constants
RAW_SUBDIR: Final[str] = "data/raw/economy"
CLEAN_SUBDIR: Final[str] = "data/cleaned/economy"

RAW_FILE_PREFIX: Final[str] = "CPNI53"
RAW_FILE_GLOB: Final[str] = f"{RAW_FILE_PREFIX}*.csv"
RAW_FORCE_FILENAME: Final[str | None] = None

CLEAN_FILENAME: Final[str] = "cross_border_commuters.csv"

REGION_MAP: Final[dict[str, str]] = {
    "Ireland": "Republic of Ireland",
    "Northern Ireland": "Northern Ireland",
}

FILTER_STATISTIC_CONTAINS: Final[str | None] = "cross border commuters for work"
FILTER_SEX: Final[str] = "Both sexes"
FILTER_UNIT: Final[str] = "Number"


#project root detection
def get_project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "pages").exists() and (parent / "data").exists():
            return parent
    return here.parents[1]


def find_raw_file(raw_dir: Path) -> Path:
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

    out["Statistic Label"] = out["Statistic Label"].astype(str).str.strip()
    out["Census Year"] = out["Census Year"].astype(str).str.strip()
    out["Ireland and Northern Ireland"] = out["Ireland and Northern Ireland"].astype(str).str.strip()
    out["Sex"] = out["Sex"].astype(str).str.strip()
    out["Age Group"] = out["Age Group"].astype(str).str.strip()
    out["UNIT"] = out["UNIT"].astype(str).str.strip()

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

    out["VALUE"] = pd.to_numeric(out["VALUE"], errors="coerce")
    out = out.dropna(subset=["VALUE"]).copy()

    out["Region"] = out["Ireland and Northern Ireland"].map(REGION_MAP)
    if out["Region"].isna().any():
        unknown = sorted(out.loc[out["Region"].isna(), "Ireland and Northern Ireland"].unique())
        raise ValueError(f"Unknown region labels encountered: {unknown}")

    out["Year"] = out["Census Year"].apply(_parse_year_to_int).astype(int)
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

    raw_path = find_raw_file(raw_dir)
    cleaned = clean_cross_border_commuters(raw_path)

    out_path = clean_dir / CLEAN_FILENAME
    cleaned.to_csv(out_path, index=False)

    print(f"Read raw:     {raw_path}")
    print(f"Wrote cleaned:{out_path}")
    print("\nPreview:")
    print(cleaned.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
