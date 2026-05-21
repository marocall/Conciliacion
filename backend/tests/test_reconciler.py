"""Tests for reconciler.py: loading, matching, and Excel output."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reconciler import load_naos, load_exact, run_matching, run_reconciliation, norm_ref, norm_desc


# ---------------------------------------------------------------------------
# norm_ref
# ---------------------------------------------------------------------------

class TestNormRef:
    def test_strips_L_prefix(self):
        assert norm_ref("L12345") == "12345"

    def test_strips_R_prefix(self):
        assert norm_ref("R67890") == "67890"

    def test_strips_F_prefix(self):
        assert norm_ref("F99999") == "99999"

    def test_passthrough_no_prefix(self):
        assert norm_ref("12345") == "12345"

    def test_empty_string(self):
        assert norm_ref("") == ""

    def test_strips_whitespace(self):
        assert norm_ref("  L12345  ") == "12345"


# ---------------------------------------------------------------------------
# norm_desc
# ---------------------------------------------------------------------------

class TestNormDesc:
    def test_removes_separators(self):
        result = norm_desc("LOCAL A - ENERO")
        assert "-" not in result
        assert " " not in result

    def test_uppercases(self):
        assert norm_desc("local a") == norm_desc("LOCAL A")

    def test_max_25_chars(self):
        assert len(norm_desc("A" * 100)) <= 25


# ---------------------------------------------------------------------------
# load_naos
# ---------------------------------------------------------------------------

class TestLoadNaos:
    def test_loads_rows(self, naos_bytes):
        df = load_naos(naos_bytes, ".xlsx")
        assert len(df) == 3

    def test_saldo_column_computed(self, naos_bytes):
        df = load_naos(naos_bytes, ".xlsx")
        assert "SALDO" in df.columns

    def test_debe_row_is_positive_saldo(self, naos_bytes):
        df = load_naos(naos_bytes, ".xlsx")
        debe_rows = df[df["signo_co"] == "D"]
        assert (debe_rows["SALDO"] > 0).all()

    def test_haber_row_is_negative_saldo(self, naos_bytes):
        df = load_naos(naos_bytes, ".xlsx")
        haber_rows = df[df["signo_co"] == "H"]
        assert (haber_rows["SALDO"] < 0).all()

    def test_ref_norm_strips_prefix(self, naos_bytes):
        df = load_naos(naos_bytes, ".xlsx")
        assert "12345" in df["ref_norm"].values
        assert "67890" in df["ref_norm"].values

    def test_fecha_str_format(self, naos_bytes):
        df = load_naos(naos_bytes, ".xlsx")
        assert df["fecha_str"].iloc[0] == "2024-01-15"


# ---------------------------------------------------------------------------
# load_exact
# ---------------------------------------------------------------------------

class TestLoadExact:
    def test_loads_rows(self, exact_bytes):
        df = load_exact(exact_bytes, ".xlsx")
        assert len(df) == 3

    def test_saldo_column(self, exact_bytes):
        df = load_exact(exact_bytes, ".xlsx")
        assert "SALDO" in df.columns

    def test_ref_extracted_from_description(self, exact_bytes):
        df = load_exact(exact_bytes, ".xlsx")
        assert "12345" in df["ref_norm"].values

    def test_fecha_str_format(self, exact_bytes):
        df = load_exact(exact_bytes, ".xlsx")
        assert df["fecha_str"].iloc[0] == "2024-01-15"

    def test_skips_metadata_rows(self, exact_bytes):
        df = load_exact(exact_bytes, ".xlsx")
        # Should not contain empty/NaT date rows
        assert df["fecha_str"].notna().all()
        assert (df["fecha_str"] != "").all()


# ---------------------------------------------------------------------------
# run_matching
# ---------------------------------------------------------------------------

class TestRunMatching:
    def test_matched_column_exists(self, naos_bytes, exact_bytes):
        naos = load_naos(naos_bytes, ".xlsx")
        exact = load_exact(exact_bytes, ".xlsx")
        naos, exact = run_matching(naos, exact)
        assert "MATCHED" in naos.columns
        assert "MATCHED" in exact.columns

    def test_exact_match_by_ref(self, naos_bytes_balanced, exact_bytes_balanced):
        naos = load_naos(naos_bytes_balanced, ".xlsx")
        exact = load_exact(exact_bytes_balanced, ".xlsx")
        naos, exact = run_matching(naos, exact)
        assert naos["MATCHED"].all(), "All NAOS rows should match"
        assert exact["MATCHED"].all(), "All EXACT rows should match"

    def test_unmatched_row_detected(self, naos_bytes, exact_bytes):
        """16/01 NAOS has 250 but EXACT has 300 — that row should be unmatched."""
        naos = load_naos(naos_bytes, ".xlsx")
        exact = load_exact(exact_bytes, ".xlsx")
        naos, exact = run_matching(naos, exact)
        unmatched_exact = exact[~exact["MATCHED"]]
        # The 16/01 EXACT row (300) has no matching NAOS row (250)
        assert len(unmatched_exact) >= 1


# ---------------------------------------------------------------------------
# run_reconciliation (integration)
# ---------------------------------------------------------------------------

class TestRunReconciliation:
    def test_returns_excel_and_summary(self, naos_bytes, exact_bytes):
        excel_io, summary = run_reconciliation(naos_bytes, exact_bytes, ".xlsx", ".xlsx")
        assert excel_io.read(4) == b"PK\x03\x04"  # valid ZIP/xlsx magic bytes
        assert isinstance(summary, list)
        assert len(summary) > 0

    def test_summary_has_required_keys(self, naos_bytes, exact_bytes):
        _, summary = run_reconciliation(naos_bytes, exact_bytes, ".xlsx", ".xlsx")
        for item in summary:
            assert "fecha" in item
            assert "saldo_naos" in item
            assert "saldo_exact" in item
            assert "diferencia" in item
            assert "cuadra" in item

    def test_balanced_dates_cuadra_true(self, naos_bytes_balanced, exact_bytes_balanced):
        _, summary = run_reconciliation(naos_bytes_balanced, exact_bytes_balanced, ".xlsx", ".xlsx")
        assert all(item["cuadra"] for item in summary)

    def test_imbalanced_dates_cuadra_false(self, naos_bytes, exact_bytes):
        _, summary = run_reconciliation(naos_bytes, exact_bytes, ".xlsx", ".xlsx")
        cuadra_flags = [item["cuadra"] for item in summary]
        assert False in cuadra_flags, "At least one date should have a difference"

    def test_diferencia_is_float(self, naos_bytes, exact_bytes):
        _, summary = run_reconciliation(naos_bytes, exact_bytes, ".xlsx", ".xlsx")
        for item in summary:
            assert isinstance(item["diferencia"], float)
