import pandas as pd
from pathlib import Path

# File paths
RAW_DATA = Path(__file__).parent.parent / "data" / "raw" / "cultural_identity" / "CPNI14.20260108T220137.csv"
CLEANED_DATA = Path(__file__).parent.parent / "data" / "cleaned" / "cultural_identity" / "ethnicity.csv"

# Drop totals
DROP_ETHNICITIES = {"All ethnic or cultural backgrounds"}

def clean_ethnicity():
    df = pd.read_csv(RAW_DATA)
    
    # Standardize region names
    df["Ireland and Northern Ireland"] = df["Ireland and Northern Ireland"].replace({
        "Ireland": "Republic of Ireland",
        "Northern Ireland": "Northern Ireland"
    })
    
    # Filter out total rows
    df = df[~df["Ethnicity"].isin(DROP_ETHNICITIES)]
    
    # Pivot UNIT column to get Absolute and Percentage as separate columns
    df_pivot = df.pivot_table(
        index=["Census Year", "Ireland and Northern Ireland", "Ethnicity"],
        columns="UNIT",
        values="VALUE",
        aggfunc="first"
    ).reset_index()
    
    # Rename columns
    df_pivot.columns.name = None
    df_pivot = df_pivot.rename(columns={
        "Census Year": "Year",
        "Ireland and Northern Ireland": "Region",
        "Number": "Absolute",
        "%": "Percentage"
    })
    
    # Convert to numeric
    df_pivot["Percentage"] = pd.to_numeric(df_pivot["Percentage"], errors="coerce")
    df_pivot["Absolute"] = pd.to_numeric(df_pivot["Absolute"], errors="coerce")
    
    # Select and order columns
    df_pivot = df_pivot[["Year", "Region", "Ethnicity", "Percentage", "Absolute"]]
    
    # Sort for consistency
    df_pivot = df_pivot.sort_values(["Year", "Region", "Ethnicity"]).reset_index(drop=True)
    
    # Save cleaned data
    CLEANED_DATA.parent.mkdir(parents=True, exist_ok=True)
    df_pivot.to_csv(CLEANED_DATA, index=False)
    
    print(f"✅ Cleaned data saved to {CLEANED_DATA}")
    print(f"Total rows: {len(df_pivot)}")
    
    # Validation: Check percentages sum to ~100 for each Region (excluding Not stated)
    validation = df_pivot[df_pivot["Ethnicity"] != "Not stated"].groupby(["Year", "Region"])["Percentage"].sum()
    print("\nPercentage sums by Year and Region (excluding 'Not stated'):")
    print(validation)

if __name__ == "__main__":
    clean_ethnicity()
