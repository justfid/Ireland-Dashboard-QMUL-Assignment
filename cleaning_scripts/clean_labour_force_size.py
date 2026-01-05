from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import pandas as pd


#constants
RAW_DIR = Path("data/raw/economy")
CLEAN_DIR = Path("data/cleaned/economy")

TABLE_PREFIX = "CPNI35"
OUT_PATH = CLEAN_DIR / "labour_market_snapshot.csv"

REQUIRED_COLS: List[str] = [
    "Statistic Label",
    "Census Year",
    "Ireland and Northern Ireland",
    "Sex",
    "Principal Economic Status",
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
    #joint publication labels the observation as "2021/2022"
    #align to the later year (2022) for stable ordering/filtering
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


def _map_region(series: pd.Series) -> pd.Series:
    region_map = {
        "Ireland": "Republic of Ireland",
        "Northern Ireland": "Northern Ireland",
    }
    out = series.astype(str).str.strip().map(region_map)
    if out.isna().any():
        unknown = sorted(series[out.isna()].astype(str).str.strip().unique())
        raise ValueError(f"Unknown region labels encountered: {unknown}")
    return out


def clean_labour_market_snapshot(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    _ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = df["Statistic Label"].astype(str).str.strip()
    df["Census Year"] = df["Census Year"].astype(str).str.strip()
    df["Ireland and Northern Ireland"] = df["Ireland and Northern Ireland"].astype(str).str.strip()
    df["Sex"] = df["Sex"].astype(str).str.strip()
    df["Principal Economic Status"] = df["Principal Economic Status"].astype(str).str.strip()
    df["UNIT"] = df["UNIT"].astype(str).str.strip()
    df["VALUE"] = pd.to_numeric(df["VALUE"], errors="coerce")

    df = df.dropna(subset=["VALUE"])

    #keep only ROI/NI and standardise naming
    df["Region"] = _map_region(df["Ireland and Northern Ireland"])

    #align year
    df["Year"] = df["Census Year"].apply(_parse_year_to_int).astype(int)

    #we want the 16+ usual resident base (numbers) and its percentage form
    #statistic labels differ, so filter by contains rather than exact match
    stat_keep = (
        df["Statistic Label"].str.contains("Population usually resident age 16 years and over", case=False, na=False)
        | df["Statistic Label"].str.contains("Percentage of Population usually resident age 16 years and over", case=False, na=False)
    )
    df = df[stat_keep]

    #we only need both sexes for the dashboard toggle
    df = df[df["Sex"] == "Both sexes"]

    #we need employed + unemployed
    pes_keep = {"Persons at work", "All unemployed persons"}
    df = df[df["Principal Economic Status"].isin(pes_keep)]

    #validate units
    bad_units = sorted(set(df["UNIT"].unique()) - {"Number", "%"})
    if bad_units:
        raise ValueError(f"Unexpected UNIT values: {bad_units}. Expected only 'Number' and '%'.")

    #build rows per Region/Year
    rows = []
    for (year, region), g in df.groupby(["Year", "Region"]):
        employed_n = g.loc[
            (g["Principal Economic Status"] == "Persons at work") & (g["UNIT"] == "Number"),
            "VALUE",
        ]
        unemployed_n = g.loc[
            (g["Principal Economic Status"] == "All unemployed persons") & (g["UNIT"] == "Number"),
            "VALUE",
        ]
        employed_pct = g.loc[
            (g["Principal Economic Status"] == "Persons at work") & (g["UNIT"] == "%"),
            "VALUE",
        ]
        unemployed_pct = g.loc[
            (g["Principal Economic Status"] == "All unemployed persons") & (g["UNIT"] == "%"),
            "VALUE",
        ]

        #these four should exist for each region
        if employed_n.empty or unemployed_n.empty or employed_pct.empty or unemployed_pct.empty:
            raise ValueError(
                f"CPNI35 missing expected rows for Year={year}, Region={region}. "
                f"Need Persons at work + All unemployed persons for both Number and %."
            )

        labour_force_n = float(employed_n.iloc[0]) + float(unemployed_n.iloc[0])

        rows.append(
            {
                "Year": int(year),
                "Region": region,
                "Employed (16+)": int(round(float(employed_n.iloc[0]))),
                "Unemployed (16+)": int(round(float(unemployed_n.iloc[0]))),
                "Labour force (16+)": int(round(labour_force_n)),
                "Employment share (%)": float(employed_pct.iloc[0]),
                "Unemployment rate (%)": float(unemployed_pct.iloc[0]),
            }
        )

    out = pd.DataFrame(rows).sort_values(["Region", "Year"]).reset_index(drop=True)

    #sanity: rates should sum to ~100
    out["Sum check (%)"] = (out["Employment share (%)"] + out["Unemployment rate (%)"]).round(1)
    bad_sum = out[(out["Sum check (%)"] < 99.5) | (out["Sum check (%)"] > 100.5)]
    if not bad_sum.empty:
        raise ValueError(
            "Employment + unemployment percentages do not sum to ~100 for some rows. "
            "Check that the '%' rows are within-labour-force shares."
        )
    out = out.drop(columns=["Sum check (%)"])

    return out


def main() -> None:
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    raw_path = _latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_labour_market_snapshot(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
