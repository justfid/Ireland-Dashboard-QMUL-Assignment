"""Unit tests for utils.cleaning module."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
from utils.cleaning import (
    parse_census_year,
    ensure_cols,
    map_regions,
    clean_string_column,
    clean_numeric_column,
    STANDARD_REGION_MAP,
    ROI_LABEL,
    NI_LABEL,
)


class TestParseCensusYear:
    """Tests for parse_census_year function."""
    
    def test_single_year(self):
        """Test parsing a single year."""
        assert parse_census_year("2022") == 2022
        assert parse_census_year("2021") == 2021
    
    def test_slash_separated_years(self):
        """Test parsing slash-separated years (should return later year)."""
        assert parse_census_year("2021/2022") == 2022
        assert parse_census_year("2020/2021") == 2021
    
    def test_year_with_whitespace(self):
        """Test parsing year with surrounding whitespace."""
        assert parse_census_year(" 2022 ") == 2022
        assert parse_census_year("  2021/2022  ") == 2022
    
    def test_invalid_year_raises_error(self):
        """Test that invalid year strings raise ValueError."""
        with pytest.raises(ValueError, match="Could not parse Census Year"):
            parse_census_year("invalid")
        with pytest.raises(ValueError):
            parse_census_year("20")
        with pytest.raises(ValueError):
            parse_census_year("")


class TestEnsureCols:
    """Tests for ensure_cols function."""
    
    def test_all_columns_present(self):
        """Test that no error is raised when all columns are present."""
        df = pd.DataFrame({"Year": [2022], "Region": ["ROI"], "Value": [100]})
        ensure_cols(df, ["Year", "Region", "Value"])  # Should not raise
    
    def test_missing_columns_raises_error(self):
        """Test that missing columns raise ValueError."""
        df = pd.DataFrame({"Year": [2022], "Value": [100]})
        with pytest.raises(ValueError, match="Missing expected columns"):
            ensure_cols(df, ["Year", "Region", "Value"])
    
    def test_empty_requirements(self):
        """Test that empty column list doesn't raise error."""
        df = pd.DataFrame({"Year": [2022]})
        ensure_cols(df, [])  # Should not raise


class TestMapRegions:
    """Tests for map_regions function."""
    
    def test_standard_region_mapping(self):
        """Test mapping with standard region map."""
        df = pd.DataFrame({
            "Country": ["Ireland", "Northern Ireland"],
            "Value": [100, 50]
        })
        result = map_regions(df, "Country", "Region")
        
        assert "Region" in result.columns
        assert list(result["Region"]) == [ROI_LABEL, NI_LABEL]
    
    def test_custom_region_mapping(self):
        """Test mapping with custom region map."""
        df = pd.DataFrame({"Location": ["A", "B"], "Value": [1, 2]})
        custom_map = {"A": "Alpha", "B": "Beta"}
        result = map_regions(df, "Location", "MappedLocation", custom_map)
        
        assert list(result["MappedLocation"]) == ["Alpha", "Beta"]
    
    def test_unknown_region_raises_error(self):
        """Test that unmapped regions raise ValueError."""
        df = pd.DataFrame({"Country": ["Unknown Country"], "Value": [100]})
        with pytest.raises(ValueError, match="Unknown region labels encountered"):
            map_regions(df, "Country", "Region")
    
    def test_original_df_unchanged(self):
        """Test that original DataFrame is not modified."""
        df = pd.DataFrame({"Country": ["Ireland"], "Value": [100]})
        original_cols = list(df.columns)
        map_regions(df, "Country", "Region")
        
        assert list(df.columns) == original_cols  # Original unchanged


class TestCleanStringColumn:
    """Tests for clean_string_column function."""
    
    def test_strips_whitespace(self):
        """Test that whitespace is stripped from strings."""
        series = pd.Series([" Ireland ", "Northern Ireland  ", "  Test"])
        result = clean_string_column(series)
        
        assert list(result) == ["Ireland", "Northern Ireland", "Test"]
    
    def test_converts_numbers_to_strings(self):
        """Test that numeric values are converted to strings."""
        series = pd.Series([123, 456.78, " text "])
        result = clean_string_column(series)
        
        assert list(result) == ["123", "456.78", "text"]
    
    def test_handles_none_values(self):
        """Test handling of None/NaN values."""
        series = pd.Series([None, "text", pd.NA])
        result = clean_string_column(series)
        
        assert result[0] in ["None", "nan", "<NA>"]  # Depends on pandas version
        assert result[1] == "text"


class TestCleanNumericColumn:
    """Tests for clean_numeric_column function."""
    
    def test_converts_string_to_numeric(self):
        """Test that numeric strings are converted to floats."""
        series = pd.Series(["100", "200.5", "300"])
        result = clean_numeric_column(series)
        
        assert list(result) == [100.0, 200.5, 300.0]
    
    def test_coerces_invalid_values_to_nan(self):
        """Test that invalid values become NaN."""
        series = pd.Series(["100", "invalid", "-", "200"])
        result = clean_numeric_column(series)
        
        assert result[0] == 100.0
        assert pd.isna(result[1])
        assert pd.isna(result[2])
        assert result[3] == 200.0
    
    def test_drop_na_option(self):
        """Test that drop_na removes NaN values."""
        series = pd.Series(["100", "invalid", "200"])
        result = clean_numeric_column(series, drop_na=True)
        
        assert len(result) == 2
        assert list(result) == [100.0, 200.0]
    
    def test_preserves_numeric_types(self):
        """Test that numeric types are preserved."""
        series = pd.Series([100, 200.5, 300])
        result = clean_numeric_column(series)
        
        assert list(result) == [100.0, 200.5, 300.0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
