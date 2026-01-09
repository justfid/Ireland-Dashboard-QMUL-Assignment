from __future__ import annotations

from pathlib import Path

import pandas as pd


def clean_religion_by_age():
    raw_path = Path("data/raw/cultural_identity/CPNI21.20260108T230129.csv")
    output_path = Path("data/cleaned/cultural_identity/religion_by_age.csv")
    
    df = pd.read_csv(raw_path)
    
    #filter to percentage rows only (not number rows)
    df = df[df["UNIT"] == "%"].copy()
    
    #exclude "all ages" aggregate
    df = df[df["Age Group"] != "All ages"].copy()
    
    #rename columns
    df = df.rename(columns={
        "Census Year": "Year",
        "Ireland and Northern Ireland": "Region",
        "Age Group": "Age_Bracket",
        "VALUE": "Percentage"
    })
    
    #standardize region names
    df["Region"] = df["Region"].replace({
        "Ireland": "Republic of Ireland",
        "Northern Ireland": "Northern Ireland"
    })
    
    #reorder columns
    df = df[["Year", "Region", "Religion", "Age_Bracket", "Percentage"]]
    
    #ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    #save
    df.to_csv(output_path, index=False)
    print(f"✅ Cleaned data saved to {output_path}")
    print(f"   Total rows: {len(df)}")
    
    #validation: check unique values
    print(f"\n   Unique religions: {df['Religion'].nunique()}")
    print(f"   Unique age brackets: {df['Age_Bracket'].nunique()}")
    print(f"   Age brackets: {sorted(df['Age_Bracket'].unique())}")


if __name__ == "__main__":
    clean_religion_by_age()
