import pandas as pd
from pathlib import Path

# File paths
RAW_DATA = Path(__file__).parent.parent / "data" / "raw" / "social_indicators" / "CPNI25.20260108T010109.csv"
CLEANED_DATA = Path(__file__).parent.parent / "data" / "cleaned" / "social_indicators" / "general_health_by_age.csv"

# Drop ratings (totals we don't need)
DROP_RATINGS = {"All"}
DROP_AGES = {"All ages"}

def clean_general_health_by_age():
    df = pd.read_csv(RAW_DATA)
    
    # Filter to only Percentage rows (not the Number rows)
    df = df[df["Statistic Label"].str.contains("Percentage")]
    
    # Standardize region names
    df["Ireland and Northern Ireland"] = df["Ireland and Northern Ireland"].replace({
        "Ireland": "Republic of Ireland",
        "Northern Ireland": "Northern Ireland"
    })
    
    # Clean rating names (remove "General health - " prefix)
    df["General Health"] = df["General Health"].str.replace("General health - ", "")
    
    # Filter out "All" rating (total) and "All ages" 
    df = df[~df["General Health"].isin(DROP_RATINGS)]
    df = df[~df["Age Group"].isin(DROP_AGES)]
    
    # Select and rename columns
    df = df[[
        "Census Year",
        "Ireland and Northern Ireland",
        "General Health",
        "Age Group",
        "VALUE"
    ]].rename(columns={
        "Census Year": "Year",
        "Ireland and Northern Ireland": "Region",
        "General Health": "Rating",
        "Age Group": "Age_Bracket",
        "VALUE": "Percentage"
    })
    
    # Convert percentage to numeric
    df["Percentage"] = pd.to_numeric(df["Percentage"], errors="coerce")
    
    # Sort for consistency
    df = df.sort_values(["Year", "Region", "Age_Bracket", "Rating"]).reset_index(drop=True)
    
    # Save cleaned data
    CLEANED_DATA.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEANED_DATA, index=False)
    
    print(f"✅ Cleaned data saved to {CLEANED_DATA}")
    print(f"Total rows: {len(df)}")
    
    # Validation: Check percentages sum to ~100 for each Region/Age combination
    validation = df.groupby(["Region", "Age_Bracket"])["Percentage"].sum()
    print("\nPercentage sums by Region and Age Bracket:")
    print(validation)

if __name__ == "__main__":
    clean_general_health_by_age()
