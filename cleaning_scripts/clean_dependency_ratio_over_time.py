from __future__ import annotations

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

#constants (edit if needed)
RAW_SUBDIR: Final[str] = "data/raw/demographics"
CLEAN_SUBDIR: Final[str] = "data/cleaned/demographics"

RAW_FILE_PREFIX: Final[str] = "CPNI04"
RAW_FORCE_FILENAME: Final[str | None] = None

CLEAN_FILENAME: Final[str] = "dependency_ratio_over_time.csv"

POP_TIME_CLEAN_FILENAME: Final[str] = "population_over_time.csv"

#explicitly choose the intended series from the CPNI04 export
FILTER_STATISTIC_LABEL: Final[str | None] = "Total dependency (All ages)"

#some CSO exports include UNIT; set to None to skip filtering.
FILTER_UNIT: Final[str | None] = None

PREFER_BOTH_SEXES: Final[bool] = True


#year normalisation
def normalise_census_year(y: object) -> int | None:
    """
    Normalise census year formats.
    - "1936/1937" -> 1936 (uses FIRST year for historical data)
    - "1946" -> 1946
    """
    s = str(y).strip()
    if "/" in s:
        left = s.split("/")[0].strip()
        return int(left) if left.isdigit() else None
    return int(s) if s.isdigit() else None


#load population weights
def load_population_over_time(clean_dir: Path) -> pd.DataFrame:
    path = clean_dir / POP_TIME_CLEAN_FILENAME
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {POP_TIME_CLEAN_FILENAME}; required for All-Island weighting."
        )

    pop = pd.read_csv(path)
    required = {"Year", "Region", "Population"}
    if not required.issubset(pop.columns):
        raise ValueError(
            f"{POP_TIME_CLEAN_FILENAME} must contain columns: Year, Region, Population"
        )

    pop = pop.copy()
    pop["Year"] = pd.to_numeric(pop["Year"], errors="coerce").astype("Int64")
    pop["Population"] = pd.to_numeric(pop["Population"], errors="coerce").astype("Int64")
    pop["Region"] = pop["Region"].astype(str).str.strip()

    pop = pop.dropna(subset=["Year", "Population"]).copy()
    pop["Year"] = pop["Year"].astype(int)
    pop["Population"] = pop["Population"].astype(int)

    pop = pop[pop["Region"].isin([ROI_LABEL, NI_LABEL])].copy()

    if pop.duplicated(subset=["Year", "Region"]).any():
        pop = pop.groupby(["Year", "Region"], as_index=False)["Population"].sum()

    return pop


#column identification
def _col(df: pd.DataFrame, *names: str) -> str | None:
    wanted = {n.strip().lower() for n in names}
    return next((c for c in df.columns if c.strip().lower() in wanted), None)


def _choose_stat_label(stat_series: pd.Series) -> str:
    """
    Choose a dependency-ratio-like statistic label when not provided.
    If multiple plausible labels exist, raise with options (prevents silent blank output).
    """
    stats = (
        stat_series.astype(str).str.strip().replace({"": pd.NA}).dropna().unique().tolist()
    )
    if not stats:
        raise ValueError("No non-empty values found in 'Statistic Label' column.")

    candidates = [s for s in stats if "dependency" in s.lower()]

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        raise ValueError(
            "Multiple dependency-ratio series found in CPNI04 export. "
            "Set FILTER_STATISTIC_LABEL to one of:\n"
            + "\n".join(f"- {c}" for c in candidates)
        )

    if len(stats) == 1:
        return stats[0]

    raise ValueError(
        "Could not auto-detect a dependency ratio series. "
        "Set FILTER_STATISTIC_LABEL to one of:\n"
        + "\n".join(f"- {s}" for s in stats)
    )


#cleaner
def clean_dependency_ratio_over_time(raw_path: Path, pop_time: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_csv(raw_path)

    col_stat = _col(df, "Statistic Label")
    col_year = _col(df, "Year", "Census Year", "CensusYear", "Census_Year")
    col_sex = _col(df, "Sex")
    col_region = _col(df, "Ireland and Northern Ireland", "Region")
    col_unit = _col(df, "UNIT", "Unit")
    col_value = _col(df, "VALUE", "Value", "Values")

    required = [col_stat, col_year, col_region, col_value]
    if any(c is None for c in required):
        raise ValueError(
            "Could not identify required columns in CPNI04 export.\n"
            f"Columns found: {list(df.columns)}\n"
            "Need at least: Statistic Label, Year/Census Year, Ireland and Northern Ireland/Region, VALUE."
        )

    out = df.copy()

    #choose statistic label robustly
    stat_label = FILTER_STATISTIC_LABEL or _choose_stat_label(out[col_stat])
    out = out[out[col_stat].astype(str).str.strip().eq(stat_label)].copy()

    if out.empty:
        raise ValueError(
            f"After filtering Statistic Label == '{stat_label}', no rows remained. "
            "Open the CSV and confirm the Statistic Label values."
        )

    if FILTER_UNIT is not None and col_unit is not None:
        out = out[out[col_unit].astype(str).str.strip().eq(FILTER_UNIT)].copy()

    rename_map: dict[str, str] = {
        col_year: "Year",
        col_region: "Region",
        col_value: "Dependency ratio",
    }
    if col_sex is not None:
        rename_map[col_sex] = "Sex"

    out = out.rename(columns=rename_map)

    out["Region"] = (
        out["Region"].astype(str).str.strip().map(STANDARD_REGION_MAP).fillna(out["Region"].astype(str).str.strip())
    )

    #year normalisation (handles "1936/1937" -> 1936)
    out["Year"] = out["Year"].map(normalise_census_year)

    out["Dependency ratio"] = pd.to_numeric(out["Dependency ratio"], errors="coerce")

    out = out.dropna(subset=["Year", "Dependency ratio"]).copy()
    out["Year"] = out["Year"].astype(int)

    out = out[out["Region"].isin([ROI_LABEL, NI_LABEL])].copy()

    #remove sex dimension (overall only)
    if "Sex" in out.columns:
        out["Sex"] = out["Sex"].astype(str).str.strip()

        if PREFER_BOTH_SEXES and (out["Sex"].str.lower() == "both sexes").any():
            out = out[out["Sex"].str.lower() == "both sexes"].copy()
            out = out.groupby(["Year", "Region"], as_index=False)["Dependency ratio"].mean()
        else:
            out = out.groupby(["Year", "Region"], as_index=False)["Dependency ratio"].mean()
    else:
        if out.duplicated(subset=["Year", "Region"]).any():
            out = out.groupby(["Year", "Region"], as_index=False)["Dependency ratio"].mean()

    #all-Island derivation (population-weighted)
    weights = (
        pop_time.pivot(index="Year", columns="Region", values="Population")
        .rename(columns={ROI_LABEL: "ROI_pop", NI_LABEL: "NI_pop"})
        .reset_index()
    )
    weights["Total_pop"] = weights["ROI_pop"] + weights["NI_pop"]

    tmp = out.merge(weights, on="Year", how="left")

    def _weighted_all_island(g: pd.DataFrame) -> float:
        roi = g[g["Region"] == ROI_LABEL]
        ni = g[g["Region"] == NI_LABEL]

        if roi.empty or ni.empty:
            return float(g["Dependency ratio"].mean())

        total = g["Total_pop"].iloc[0]
        if pd.isna(total) or total <= 0:
            return float(g["Dependency ratio"].mean())

        return float(
            (roi["Dependency ratio"].iloc[0] * g["ROI_pop"].iloc[0]
             + ni["Dependency ratio"].iloc[0] * g["NI_pop"].iloc[0])
            / total
        )

    all_island = (
        tmp.groupby("Year", as_index=False)
        .apply(lambda g: pd.Series({"Dependency ratio": _weighted_all_island(g)}))
        .reset_index(drop=True)
    )
    all_island["Region"] = ALL_LABEL

    out = pd.concat([out, all_island], ignore_index=True)

    #final rounding
    out["Dependency ratio"] = out["Dependency ratio"].round(1)

    out = out.sort_values(["Region", "Year"]).reset_index(drop=True)

    return out[["Year", "Region", "Dependency ratio"]]


def main() -> None:
    project_root = get_project_root()
    raw_dir = project_root / RAW_SUBDIR
    clean_dir = project_root / CLEAN_SUBDIR
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)

    raw_path = find_raw_file(raw_dir, RAW_FILE_PREFIX, RAW_FORCE_FILENAME)
    pop_time = load_population_over_time(clean_dir)

    cleaned = clean_dependency_ratio_over_time(raw_path, pop_time)

    out_path = clean_dir / CLEAN_FILENAME
    cleaned.to_csv(out_path, index=False)

    print(f"Project root: {project_root}")
    print(f"Read raw:      {raw_path}")
    print(f"Wrote cleaned: {out_path}")
    print("\nPreview:")
    print(cleaned.head(12).to_string(index=False))


if __name__ == "__main__":
    main()
