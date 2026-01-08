from __future__ import annotations

import sys
from pathlib import Path
from typing import List

# Add project root to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from utils.cleaning import (
    ensure_cols,
    latest_timestamped_file,
    parse_census_year,
    map_regions,
    clean_string_column,
    clean_numeric_column,
)

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


def clean_labour_market_snapshot(raw_path: Path) -> pd.DataFrame:
    df = pd.read_csv(raw_path)
    ensure_cols(df, REQUIRED_COLS)

    df["Statistic Label"] = clean_string_column(df["Statistic Label"])
    df["Census Year"] = clean_string_column(df["Census Year"])
    df["Ireland and Northern Ireland"] = clean_string_column(df["Ireland and Northern Ireland"])
    df["Sex"] = clean_string_column(df["Sex"])
    df["Principal Economic Status"] = clean_string_column(df["Principal Economic Status"])
    df["UNIT"] = clean_string_column(df["UNIT"])
    df["VALUE"] = clean_numeric_column(df["VALUE"])

    df = df.dropna(subset=["VALUE"])

    #keep only ROI/NI and standardise naming
    df = map_regions(df, "Ireland and Northern Ireland", "Region")

    #align year
    df["Year"] = df["Census Year"].apply(parse_census_year).astype(int)

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

    raw_path = latest_timestamped_file(RAW_DIR, TABLE_PREFIX)
    cleaned = clean_labour_market_snapshot(raw_path)

    cleaned.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(cleaned)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
