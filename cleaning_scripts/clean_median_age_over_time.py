#cleans CSO/NISRA joint publication (CPNI03*) median age into:
#   data/cleaned/demographics/median_age_over_time.csv
#
#output schema (dashboard-ready):
#   Year (int), Region (str), Median age (float, 1 d.p.)

from __future__ import annotations

from pathlib import Path
from typing import Final

import pandas as pd

from utils.cleaning import (
    get_project_root,
    find_raw_file,
    map_regions,
    clean_string_column,
    clean_numeric_column,
    ROI_LABEL,
    NI_LABEL,
    ALL_LABEL,
    STANDARD_REGION_MAP,
)

#constants
RAW_SUBDIR: Final[str] = "data/raw/demographics"
CLEAN_SUBDIR: Final[str] = "data/cleaned/demographics"

RAW_FILE_PREFIX: Final[str] = "CPNI03"
RAW_FORCE_FILENAME: Final[str | None] = None

CLEAN_FILENAME: Final[str] = "median_age_over_time.csv"

POP_TIME_CLEAN_FILENAME: Final[str] = "population_over_time.csv"

FILTER_STATISTIC_LABEL: Final[str] = "Median Age"
FILTER_UNIT: Final[str] = "Number"



#load population weights
def load_population_over_time(clean_dir: Path) -> pd.DataFrame:
    path = clean_dir / POP_TIME_CLEAN_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {POP_TIME_CLEAN_FILENAME}; required for All-Island weighting."
        )

    pop = pd.read_csv(path)

    if not {"Year", "Region", "Population"}.issubset(pop.columns):
        raise ValueError(
            "population_over_time.csv must contain Year, Region, Population"
        )

    pop["Year"] = pd.to_numeric(pop["Year"], errors="coerce").astype(int)
    pop["Population"] = pd.to_numeric(pop["Population"], errors="coerce").astype(int)
    pop["Region"] = pop["Region"].astype(str).str.strip()

    pop = pop[pop["Region"].isin([ROI_LABEL, NI_LABEL])]

    if pop.duplicated(subset=["Year", "Region"]).any():
        pop = pop.groupby(["Year", "Region"], as_index=False)["Population"].sum()

    return pop



#cleaner

def clean_median_age_over_time(
    raw_path: Path, pop_time: pd.DataFrame
) -> pd.DataFrame:
    df = pd.read_csv(raw_path)

    col_stat = next(
        (c for c in df.columns if c.strip().lower() == "statistic label"), None
    )
    col_year = next((c for c in df.columns if c.strip().lower() == "year"), None)
    col_region = next(
        (c for c in df.columns if c.strip().lower() in {"region", "ireland and northern ireland"}),
        None,
    )
    col_unit = next((c for c in df.columns if c.strip().lower() == "unit"), None)
    col_value = next(
        (c for c in df.columns if c.strip().lower() in {"value", "values"}), None
    )

    required = [col_stat, col_year, col_region, col_unit, col_value]
    if any(c is None for c in required):
        raise ValueError(
            "Could not identify required columns in CPNI03 export.\n"
            f"Columns found: {list(df.columns)}"
        )

    out = df.copy()

    #filter to median age (overall)
    out = out[out[col_stat].astype(str).str.strip().eq(FILTER_STATISTIC_LABEL)]
    out = out[out[col_unit].astype(str).str.strip().eq(FILTER_UNIT)]

    out = out.rename(
        columns={
            col_year: "Year",
            col_region: "Region",
            col_value: "Median age",
        }
    )

    out["Region"] = clean_string_column(out["Region"])
    out = map_regions(out, "Region", "Region")

    out["Year"] = pd.to_numeric(out["Year"], errors="coerce").astype(int)
    out["Median age"] = clean_numeric_column(out["Median age"])

    out = out.dropna(subset=["Year", "Median age"])
    out = out[out["Region"].isin([ROI_LABEL, NI_LABEL])]

    if out.duplicated(subset=["Year", "Region"]).any():
        out = out.groupby(["Year", "Region"], as_index=False)["Median age"].mean()

    # All-Island derivation (population-weighted)
    weights = (
        pop_time.pivot(index="Year", columns="Region", values="Population")
        .rename(columns={ROI_LABEL: "ROI_pop", NI_LABEL: "NI_pop"})
        .reset_index()
    )
    weights["Total_pop"] = weights["ROI_pop"] + weights["NI_pop"]

    tmp = out.merge(weights, on="Year", how="left")

    def weighted_all_island(group: pd.DataFrame) -> float:
        roi = group[group["Region"] == ROI_LABEL]
        ni = group[group["Region"] == NI_LABEL]

        if roi.empty or ni.empty:
            return float(group["Median age"].mean())

        total = group["Total_pop"].iloc[0]
        if pd.isna(total) or total <= 0:
            return float(group["Median age"].mean())

        return float(
            (roi["Median age"].iloc[0] * group["ROI_pop"].iloc[0]
             + ni["Median age"].iloc[0] * group["NI_pop"].iloc[0])
            / total
        )

    all_island = (
        tmp.groupby("Year", as_index=False)
        .apply(lambda g: pd.Series({"Median age": weighted_all_island(g)}))
        .reset_index(drop=True)
    )
    all_island["Region"] = ALL_LABEL

    out = pd.concat([out, all_island], ignore_index=True)

    #final rounding
    out["Median age"] = out["Median age"].round(1)

    out = out.sort_values(["Region", "Year"]).reset_index(drop=True)

    return out[["Year", "Region", "Median age"]]


def main() -> None:
    project_root = get_project_root()
    raw_dir = project_root / RAW_SUBDIR
    clean_dir = project_root / CLEAN_SUBDIR

    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    raw_path = find_raw_file(raw_dir)
    pop_time = load_population_over_time(clean_dir)

    cleaned = clean_median_age_over_time(raw_path, pop_time)

    out_path = clean_dir / CLEAN_FILENAME
    cleaned.to_csv(out_path, index=False)

    print(f"Read raw:  {raw_path}")
    print(f"Wrote:     {out_path}")
    print("\nPreview:")
    print(cleaned.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
