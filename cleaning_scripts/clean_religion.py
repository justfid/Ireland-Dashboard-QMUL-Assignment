from __future__ import annotations

from pathlib import Path

import pandas as pd


def clean_religion():
    raw_path = Path("data/raw/cultural_identity/CPNI20.20260108T230129.csv")
    output_path = Path("data/cleaned/cultural_identity/religion.csv")
    
    df = pd.read_csv(raw_path)
    
    #pivot unit column (number/%) into separate absolute/percentage columns
    df_num = df[df["UNIT"] == "Number"].copy()
    df_pct = df[df["UNIT"] == "%"].copy()
    
    df_num = df_num.rename(columns={"VALUE": "Absolute"})
    df_pct = df_pct.rename(columns={"VALUE": "Percentage"})
    
    merged = pd.merge(
        df_num[["Census Year", "Ireland and Northern Ireland", "Religion", "Absolute"]],
        df_pct[["Census Year", "Ireland and Northern Ireland", "Religion", "Percentage"]],
        on=["Census Year", "Ireland and Northern Ireland", "Religion"],
        how="outer"
    )
    
    #rename columns
    merged = merged.rename(columns={
        "Census Year": "Year",
        "Ireland and Northern Ireland": "Region"
    })
    
    #standardize region names
    merged["Region"] = merged["Region"].replace({
        "Ireland": "Republic of Ireland",
        "Northern Ireland": "Northern Ireland"
    })
    
    #reorder columns
    merged = merged[["Year", "Region", "Religion", "Percentage", "Absolute"]]
    
    #ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    #save
    merged.to_csv(output_path, index=False)
    print(f"✅ Cleaned data saved to {output_path}")
    print(f"   Total rows: {len(merged)}")
    
    #validation: check percentage sums by year and region
    print("\n   Percentage sums by Year and Region (excluding 'Not stated'):")
    for (year, region), group in merged.groupby(["Year", "Region"]):
        total_pct = group[group["Religion"] != "Not stated"]["Percentage"].sum()
        print(f"   - {region}: {total_pct:.1f}%")


if __name__ == "__main__":
    clean_religion()
