"""Unit tests for utils.common module."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
from utils.common import (
    ensure_cols,
    clean_region_column,
    clean_year_column,
    clean_numeric_column,
    ROI,
    NI,
    ALL,
    REGIONS,
    ALL_REGIONS,
)


class TestConstants:
    """Tests for module constants."""
    
    def test_region_constants_are_strings(self):
        """Test that region constants are properly defined as strings."""
        assert isinstance(ROI, str)
        assert isinstance(NI, str)
        assert isinstance(ALL, str)
    
    def test_regions_list_contents(self):
        """Test that REGIONS contains ROI and NI."""
        assert len(REGIONS) == 2
        assert ROI in REGIONS
        assert NI in REGIONS
    
    def test_all_regions_list_contents(self):
        """Test that ALL_REGIONS contains all three regions."""
        assert len(ALL_REGIONS) == 3
        assert ROI in ALL_REGIONS
        assert NI in ALL_REGIONS
        assert ALL in ALL_REGIONS


class TestEnsureCols:
    """Tests for ensure_cols function."""
    
    def test_valid_dataframe(self):
        """Test that valid DataFrame passes validation."""
        df = pd.DataFrame({"Year": [2022], "Region": ["ROI"], "Value": [100]})
        ensure_cols(df, ["Year", "Region", "Value"])  # Should not raise
    
    def test_missing_column_raises_error(self):
        """Test that missing columns raise ValueError."""
        df = pd.DataFrame({"Year": [2022], "Value": [100]})
        with pytest.raises(ValueError):
            ensure_cols(df, ["Year", "Region", "Value"])
    
    def test_extra_columns_allowed(self):
        """Test that extra columns don't cause errors."""
        df = pd.DataFrame({
            "Year": [2022],
            "Region": ["ROI"],
            "Value": [100],
            "Extra": ["data"]
        })
        ensure_cols(df, ["Year", "Region"])  # Should not raise


class TestCleanRegionColumn:
    """Tests for clean_region_column function."""
    
    def test_strips_whitespace(self):
        """Test that whitespace is properly stripped."""
        series = pd.Series([" Republic of Ireland ", "Northern Ireland  "])
        result = clean_region_column(series)
        
        assert list(result) == ["Republic of Ireland", "Northern Ireland"]
    
    def test_preserves_clean_values(self):
        """Test that already clean values are unchanged."""
        series = pd.Series(["Republic of Ireland", "Northern Ireland"])
        result = clean_region_column(series)
        
        assert list(result) == ["Republic of Ireland", "Northern Ireland"]


class TestCleanYearColumn:
    """Tests for clean_year_column function."""
    
    def test_converts_string_years(self):
        """Test that string years are converted to integers."""
        series = pd.Series(["2022", "2021", "2020"])
        result = clean_year_column(series)
        
        assert result.dtype == int
        assert list(result) == [2022, 2021, 2020]
    
    def test_preserves_numeric_years(self):
        """Test that numeric years remain as integers."""
        series = pd.Series([2022, 2021, 2020])
        result = clean_year_column(series)
        
        assert result.dtype == int
        assert list(result) == [2022, 2021, 2020]
    
    def test_handles_invalid_years(self):
        """Test that invalid years raise an error or are coerced."""
        series = pd.Series([2022, "invalid", 2020])
        # This should coerce invalid to NaN then convert
        with pytest.raises((ValueError, TypeError)):
            result = clean_year_column(series)


class TestCleanNumericColumn:
    """Tests for clean_numeric_column function."""
    
    def test_converts_string_numbers(self):
        """Test that string numbers are converted to floats."""
        series = pd.Series(["100.5", "200", "300.75"])
        result = clean_numeric_column(series)
        
        assert list(result) == [100.5, 200.0, 300.75]
    
    def test_coerces_invalid_to_nan(self):
        """Test that invalid values become NaN."""
        series = pd.Series(["100", "invalid", "200"])
        result = clean_numeric_column(series)
        
        assert result[0] == 100.0
        assert pd.isna(result[1])
        assert result[2] == 200.0
    
    def test_preserves_numeric_values(self):
        """Test that numeric values are preserved."""
        series = pd.Series([100.5, 200, 300.75])
        result = clean_numeric_column(series)
        
        assert list(result) == [100.5, 200.0, 300.75]


class TestIntegration:
    """Integration tests combining multiple functions."""
    
    def test_clean_census_data_workflow(self):
        """Test a typical data cleaning workflow."""
        # Simulate raw census data
        raw_df = pd.DataFrame({
            "Census Year": ["2022", "2022", "2021"],
            "Ireland and Northern Ireland": [" Ireland ", "Northern Ireland", " Ireland"],
            "VALUE": ["1000000", "500000", "950000"]
        })
        
        # Validate columns
        ensure_cols(raw_df, ["Census Year", "Ireland and Northern Ireland", "VALUE"])
        
        # Clean columns
        raw_df["Year"] = clean_year_column(raw_df["Census Year"])
        raw_df["Region"] = clean_region_column(raw_df["Ireland and Northern Ireland"])
        raw_df["Value"] = clean_numeric_column(raw_df["VALUE"])
        
        # Verify results
        assert list(raw_df["Year"]) == [2022, 2022, 2021]
        assert list(raw_df["Region"]) == ["Ireland", "Northern Ireland", "Ireland"]
        assert list(raw_df["Value"]) == [1000000.0, 500000.0, 950000.0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
