# Cleans CSO/NISRA joint publication (CPNI02*) population distribution (age bands) into:
#   data/cleaned/demographics/population_distribution.csv
#
# Output schema (tidy / dashboard-ready):
#   Year (int), Region (str), Sex (str), Age band (str), Population (int)

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

import pandas as pd

from utils.cleaning import (
    get_project_root,
    find_raw_file,
    STANDARD_REGION_MAP,
    ROI_LABEL,
    NI_LABEL,
    ALL_LABEL,
)

#constants to edit
RAW_SUBDIR: Final[str] = "data/raw/demographics"
CLEAN_SUBDIR: Final[str] = "data/cleaned/demographics"

RAW_FILE_PREFIX: Final[str] = "CPNI02"
RAW_FORCE_FILENAME: Final[str | None] = None  

CLEAN_FILENAME: Final[str] = "population_distribution.csv"

#optional filters (set to None to disable)
FILTER_STATISTIC_LABEL: Final[str | None] = "Population"
FILTER_UNIT: Final[str | None] = "Number"
FILTER_SEX: Final[str | None] = None  # e.g. "Both sexes" if you want totals only

ADD_ALL_ISLAND: Final[bool] = True


#age band normalisation
def normalise_age_band(raw: str) -> str:
    s = str(raw).strip().lower()
    s = re.sub(r"\s+", " ", s)

    if "85" in s and ("over" in s or "and" in s or "+" in s):
        return "85+"

    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        a = int(nums[0])
        b = int(nums[1])
        return f"{a}-{b}"

    m = re.match(r"^(\d{1,3})\s*-\s*(\d{1,3})$", s)
    if m:
        return f"{int(m.group(1))}-{int(m.group(2))}"

    return str(raw).strip()


def ensure_age_band_order(df: pd.DataFrame) -> pd.DataFrame:
    order = [
        "0-4", "5-9", "10-14", "15-19",
        "20-24", "25-29", "30-34", "35-39",
        "40-44", "45-49", "50-54", "55-59",
        "60-64", "65-69", "70-74", "75-79",
        "80-84", "85+",
    ]
    out = df.copy()
    if "Age band" in out.columns:
        vals = set(out["Age band"].astype(str).unique().tolist())
        if len(vals.intersection(set(order))) >= 6:
            out["Age band"] = pd.Categorical(out["Age band"].astype(str), categories=order, ordered=True)
    return out

#cleaner
def clean_population_distribution(raw_path: Path) -> pd.DataFrame:
    df: pd.DataFrame = pd.read_csv(raw_path)

    # Identify columns (supports "Census Year")
    col_stat = next((c for c in df.columns if c.strip().lower() == "statistic label"), None)

    year_aliases = {"year", "census year", "censusyear", "census_year"}
    col_year = next((c for c in df.columns if c.strip().lower() in year_aliases), None)

    col_sex = next((c for c in df.columns if c.strip().lower() == "sex"), None)
    col_region = next(
        (c for c in df.columns if c.strip().lower() in {"ireland and northern ireland", "region"}),
        None,
    )
    col_unit = next((c for c in df.columns if c.strip().lower() == "unit"), None)
    col_value = next((c for c in df.columns if c.strip().lower() in {"value", "values"}), None)

    age_aliases = {"age group", "age_group", "age", "age band", "ageband"}
    col_age = next((c for c in df.columns if c.strip().lower() in age_aliases), None)

    required = [col_year, col_sex, col_region, col_unit, col_value, col_age]
    if any(c is None for c in required):
        raise ValueError(
            "Could not identify required columns in CPNI02 export.\n"
            f"Columns found: {list(df.columns)}\n"
            "Need at least: Year/Census Year, Sex, Age Group, Ireland and Northern Ireland/Region, UNIT, VALUE."
        )

    out = df.copy()

    if col_stat and FILTER_STATISTIC_LABEL is not None:
        out = out[out[col_stat].astype(str).str.strip().eq(FILTER_STATISTIC_LABEL)]
    if FILTER_SEX is not None:
        out = out[out[col_sex].astype(str).str.strip().eq(FILTER_SEX)]
    if FILTER_UNIT is not None:
        out = out[out[col_unit].astype(str).str.strip().eq(FILTER_UNIT)]

    out = out.rename(
        columns={
            col_year: "Year",
            col_sex: "Sex",
            col_region: "Region",
            col_age: "Age band",
            col_value: "Population",
        }
    )

    out["Region"] = out["Region"].astype(str).str.strip().map(STANDARD_REGION_MAP).fillna(out["Region"].astype(str).str.strip())
    out["Sex"] = out["Sex"].astype(str).str.strip()

    out["Year"] = pd.to_numeric(out["Year"], errors="coerce").astype("Int64")
    out["Population"] = pd.to_numeric(out["Population"], errors="coerce").astype("Int64")
    out["Age band"] = out["Age band"].astype(str).map(normalise_age_band)

    out = out.dropna(subset=["Year", "Population"]).copy()
    out["Year"] = out["Year"].astype(int)
    out["Population"] = out["Population"].astype(int)

    #keep only ROI/NI (All-Island derived later)
    out = out[out["Region"].isin([ROI_LABEL, NI_LABEL])].copy()

    #remove totals if present
    out = out[~out["Age band"].astype(str).str.lower().isin({"all ages", "total", "all"})].copy()

    #de-dup by summing just in case
    if out.duplicated(subset=["Year", "Region", "Sex", "Age band"]).any():
        out = out.groupby(["Year", "Region", "Sex", "Age band"], as_index=False)["Population"].sum()

    if ADD_ALL_ISLAND:
        all_island = (
            out.groupby(["Year", "Sex", "Age band"], as_index=False)["Population"]
            .sum()
            .assign(Region=ALL_LABEL)
        )
        out = pd.concat([out, all_island], ignore_index=True)

    out = ensure_age_band_order(out)
    out = out.sort_values(["Region", "Year", "Sex", "Age band"]).reset_index(drop=True)

    if (out["Population"] < 0).any():
        raise ValueError("Found negative population values after cleaning. Check raw table filters/columns.")

    return out[["Year", "Region", "Sex", "Age band", "Population"]]


def main() -> None:
    project_root = get_project_root()
    raw_dir = project_root / RAW_SUBDIR
    clean_dir = project_root / CLEAN_SUBDIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    raw_path = find_raw_file(raw_dir, RAW_FILE_PREFIX, RAW_FORCE_FILENAME)
    cleaned = clean_population_distribution(raw_path)

    out_path = clean_dir / CLEAN_FILENAME
    cleaned.to_csv(out_path, index=False)

    print(f"Project root: {project_root}")
    print(f"Read raw:      {raw_path}")
    print(f"Wrote cleaned: {out_path}")
    print("\nPreview:")
    print(cleaned.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
