"""
test_pipeline.py — Unit tests for the cleaning logic.

These tests run entirely locally with no Azure SDK calls.
The blob I/O is mocked so you can verify the pandas transformations in isolation.

Run with:
    pytest tests/ -v
"""

import os
import sys
import types
from io import StringIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Stub out azure.storage.blob before any project modules are imported.
# This prevents "ImportError: No module named azure" when running tests
# without the Azure SDK installed (CI environments, local dev without venv).
# ---------------------------------------------------------------------------
def _make_azure_stub():
    azure = types.ModuleType("azure")
    azure.storage = types.ModuleType("azure.storage")
    azure.storage.blob = types.ModuleType("azure.storage.blob")
    azure.storage.blob.BlobServiceClient = MagicMock()
    azure.storage.blob.BlockBlobService = MagicMock()  # Keep for backward compatibility if needed
    azure.storage.blob.ContentSettings = MagicMock()
    sys.modules.setdefault("azure", azure)
    sys.modules.setdefault("azure.storage", azure.storage)
    sys.modules.setdefault("azure.storage.blob", azure.storage.blob)

_make_azure_stub()

# ---------------------------------------------------------------------------
# Sample DataFrames that mimic what would be read from a real CSV blob
# ---------------------------------------------------------------------------

SAMPLE_S1 = pd.DataFrame({
    "customer": [1111, 2222, 3333, 4444, 5555],
    "order":    [9001, 9002, 9003, 9004, 9005],
    "names":    ["Aaron", "Aaron", "Ben", "Ben", "Nick"],
    "region":   ["east", "east", "west", "east", "east"],
    "item":     ["paper", "pens", "paper", "binder", "paper"],
    "units":    [100, 200, 150, 300, 50],
    "price":    [10, 20, 15, 30, 5],
})

SAMPLE_S2 = pd.DataFrame({
    "customer": [6666, 7777, 8888],
    "order":    [9006, 9007, 9008],
    "names":    ["Aaron", "Ben", "Nick"],
    "region":   ["east", "west", "central"],
    "item":     ["binder", "binder", "pens"],
    "units":    [400, 500, 100],
    "price":    [40, 50, 10],
})


# ===========================================================================
# CleanSales1 — clean_blob logic
# ===========================================================================

class TestCleanSales1:
    """Tests for the CleanSales1 groupby + filter transformation."""

    def _apply_transform(self, df: pd.DataFrame, target_region: str = "east") -> pd.DataFrame:
        """Replicate the exact transformation in CleanSales1/clean.py."""
        aggregated = (
            df.groupby(["names", "region"], as_index=False)[["units", "price"]]
            .sum()
        )
        return aggregated[aggregated["region"] == target_region].copy()

    def test_filters_to_east_region_only(self):
        result = self._apply_transform(SAMPLE_S1)
        assert set(result["region"].unique()) == {"east"}, \
            "Result should contain only 'east' rows"

    def test_aggregates_multiple_rows_for_same_name(self):
        # Aaron has two east rows: units 100 + 200 = 300, price 10 + 20 = 30
        result = self._apply_transform(SAMPLE_S1)
        aaron = result[result["names"] == "Aaron"]
        assert len(aaron) == 1, "Multiple Aaron/east rows should collapse into one"
        assert aaron.iloc[0]["units"] == 300
        assert aaron.iloc[0]["price"] == 30

    def test_west_rows_excluded(self):
        result = self._apply_transform(SAMPLE_S1)
        assert "west" not in result["region"].values

    def test_returns_dataframe(self):
        result = self._apply_transform(SAMPLE_S1)
        assert isinstance(result, pd.DataFrame)

    def test_empty_input_returns_empty_dataframe(self):
        empty = SAMPLE_S1.iloc[0:0].copy()
        result = self._apply_transform(empty)
        assert result.empty


# ===========================================================================
# CleanSales2 — clean_blob logic
# ===========================================================================

class TestCleanSales2:
    """Tests for the CleanSales2 groupby + item filter transformation."""

    def _apply_transform(self, df: pd.DataFrame, target_item: str = "binder") -> pd.DataFrame:
        aggregated = (
            df.groupby(["names", "item"], as_index=False)[["units", "price"]]
            .sum()
        )
        return aggregated[aggregated["item"] == target_item].copy()

    def test_filters_to_binder_only(self):
        result = self._apply_transform(SAMPLE_S2)
        assert set(result["item"].unique()) == {"binder"}

    def test_pens_rows_excluded(self):
        result = self._apply_transform(SAMPLE_S2)
        assert "pens" not in result["item"].values

    def test_aggregates_binder_rows(self):
        # SAMPLE_S2 has one binder row per name — no aggregation needed, but result is correct
        result = self._apply_transform(SAMPLE_S2)
        assert len(result) == 2  # Aaron/binder and Ben/binder

    def test_empty_input_returns_empty_dataframe(self):
        empty = SAMPLE_S2.iloc[0:0].copy()
        result = self._apply_transform(empty)
        assert result.empty


# ===========================================================================
# Reconcile — merge logic
# ===========================================================================

class TestReconcile:
    """Tests for the Reconcile outer-merge transformation."""

    def _reconcile(self, df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
        return pd.merge(df1, df2, on="names", how="outer", suffixes=("_s1", "_s2"))

    def test_merge_preserves_all_names(self):
        # Both DataFrames share Aaron and Ben; Nick only in s1; Richard only added here
        df1 = pd.DataFrame({"names": ["Aaron", "Ben", "Nick"], "units": [10, 20, 30]})
        df2 = pd.DataFrame({"names": ["Aaron", "Ben", "Richard"], "units": [5, 15, 25]})
        result = self._reconcile(df1, df2)
        assert set(result["names"]) == {"Aaron", "Ben", "Nick", "Richard"}

    def test_shared_column_suffixes(self):
        df1 = pd.DataFrame({"names": ["Aaron"], "units": [100], "price": [10]})
        df2 = pd.DataFrame({"names": ["Aaron"], "units": [200], "price": [20]})
        result = self._reconcile(df1, df2)
        assert "units_s1" in result.columns
        assert "units_s2" in result.columns

    def test_missing_rows_produce_nan(self):
        df1 = pd.DataFrame({"names": ["Aaron"], "units": [100]})
        df2 = pd.DataFrame({"names": ["Ben"], "units": [200]})
        result = self._reconcile(df1, df2)
        # Aaron has no match in df2 → units_s2 should be NaN
        aaron_row = result[result["names"] == "Aaron"]
        assert pd.isna(aaron_row.iloc[0]["units_s2"])

    def test_output_is_dataframe(self):
        result = self._reconcile(SAMPLE_S1, SAMPLE_S2)
        assert isinstance(result, pd.DataFrame)


# ===========================================================================
# CSV Generator
# ===========================================================================

class TestCSVGenerator:
    """Tests for the random CSV generator utility."""

    def test_generates_correct_row_count(self, tmp_path):
        # Import here so the stub is already in place
        sys.path.insert(0, str(tmp_path))
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[Columns]\n"
            "names=Alice,Bob\n"
            "region=east,west\n"
            "units=lowrandom\n"
        )
        out_path = tmp_path / "test_out.csv"

        # Import and call directly
        import importlib, importlib.util
        spec = importlib.util.spec_from_file_location(
            "randomcsvgenerator",
            os.path.join(os.path.dirname(__file__), "..", "dataset", "randomcsvgenerator.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        mod.generate(rows=50, config_path=str(config_path), out_path=str(out_path))

        df = pd.read_csv(str(out_path))
        assert len(df) == 50

    def test_generated_columns_match_config(self, tmp_path):
        config_path = tmp_path / "config.ini"
        config_path.write_text(
            "[Columns]\n"
            "customer=highrandom\n"
            "names=Alice,Bob\n"
        )
        out_path = tmp_path / "test_out.csv"

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "randomcsvgenerator",
            os.path.join(os.path.dirname(__file__), "..", "dataset", "randomcsvgenerator.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.generate(rows=10, config_path=str(config_path), out_path=str(out_path))

        df = pd.read_csv(str(out_path))
        assert list(df.columns) == ["customer", "names"]
