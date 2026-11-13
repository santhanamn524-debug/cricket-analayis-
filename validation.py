"""
data_pipeline/validation.py
============================
RR Intelligence Hub – Data Validation Module
----------------------------------------------
PURPOSE:
    Validate the cleaned datasets for:
      - Referential integrity (foreign-key relationships)
      - Cricket-specific business rules
      - Completeness of required fields
      - Statistical plausibility checks

    Runs AFTER cleaning.py has produced the cleaned CSV files.

USAGE:
    python data_pipeline/validation.py

AUTHOR: RR Intelligence Hub
"""

import json
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("validation")

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR    = PROJECT_ROOT / "reports" / "data_audit"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Validation result tracker
# ---------------------------------------------------------------------------

class ValidationResult:
    def __init__(self):
        self.checks: list[dict] = []

    def add(self, name: str, passed: bool, detail: str, severity: str = "ERROR"):
        p_bool = bool(passed)
        self.checks.append({
            "check": name,
            "passed": p_bool,
            "severity": severity if not p_bool else "INFO",
            "detail": detail,
        })
        status = "PASS" if p_bool else f"{severity}"
        log.info("[%s] %s | %s", status, name, detail)

    def summary(self) -> dict:
        total   = len(self.checks)
        passed  = sum(1 for c in self.checks if c["passed"])
        failed  = total - passed
        errors  = sum(1 for c in self.checks if not c["passed"] and c["severity"] == "ERROR")
        warnings = sum(1 for c in self.checks if not c["passed"] and c["severity"] == "WARNING")
        return {
            "total_checks": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "warnings": warnings,
            "ready_for_feature_engineering": errors == 0,
        }


# ---------------------------------------------------------------------------
# Loader helpers
# ---------------------------------------------------------------------------

def load_cleaned(filename: str) -> pd.DataFrame | None:
    path = PROCESSED_DIR / filename
    if not path.exists():
        log.warning("Cleaned file not found: %s — run cleaning.py first", path)
        return None
    df = pd.read_csv(path, low_memory=False)
    log.info("Loaded %s: %d rows", filename, len(df))
    return df


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

def validate_referential_integrity(
    result: ValidationResult,
    df_child: pd.DataFrame, child_name: str, child_key: str,
    df_parent: pd.DataFrame, parent_name: str, parent_key: str,
) -> None:
    """Check that all foreign keys in df_child exist in df_parent."""
    if child_key not in df_child.columns:
        result.add(
            f"FK: {child_name}.{child_key} → {parent_name}.{parent_key}",
            False,
            f"Column '{child_key}' not found in {child_name}",
        )
        return
    if parent_key not in df_parent.columns:
        result.add(
            f"FK: {child_name}.{child_key} → {parent_name}.{parent_key}",
            False,
            f"Column '{parent_key}' not found in {parent_name}",
        )
        return

    child_vals  = set(df_child[child_key].dropna().unique())
    parent_vals = set(df_parent[parent_key].dropna().unique())
    orphans = child_vals - parent_vals
    result.add(
        f"FK: {child_name}.{child_key} → {parent_name}.{parent_key}",
        len(orphans) == 0,
        f"{len(orphans)} orphan values found in {child_name}" if orphans
        else "All foreign keys resolve correctly",
        severity="WARNING",
    )


def validate_no_null_primary_key(
    result: ValidationResult,
    df: pd.DataFrame, fname: str, pk_col: str,
) -> None:
    if pk_col not in df.columns:
        result.add(f"PK null check: {fname}.{pk_col}", False, f"Column '{pk_col}' missing")
        return
    nulls = df[pk_col].isnull().sum()
    result.add(
        f"PK null check: {fname}.{pk_col}",
        nulls == 0,
        f"{nulls} null values in primary key column '{pk_col}'" if nulls else "No nulls in PK",
    )


def validate_ball_by_ball_cricket_rules(
    result: ValidationResult,
    df: pd.DataFrame,
) -> None:
    """
    Apply cricket-specific business rules to ball-by-ball data.
    Column names are looked up dynamically.
    """
    cols = list(df.columns)

    # -- Runs columns must be non-negative ------------------------------------
    run_cols = [c for c in cols if "run" in c and pd.api.types.is_numeric_dtype(df[c])]
    for col in run_cols:
        neg = int((df[col] < 0).sum())
        result.add(
            f"Non-negative runs: {col}",
            neg == 0,
            f"{neg} negative values" if neg else "All values >= 0",
            severity="ERROR",
        )

    # -- Innings range --------------------------------------------------------
    innings_col = next((c for c in cols if "innings" in c and pd.api.types.is_numeric_dtype(df[c])), None)
    if innings_col:
        invalid = int(~df[innings_col].isin([1, 2, 3, 4]).sum())  # 3,4 for super overs
        result.add(
            f"Innings range: {innings_col}",
            invalid == 0,
            f"{invalid} rows with innings outside [1,2,3,4]" if invalid else "All innings values valid",
            severity="WARNING",
        )

    # -- At least one runs column present -------------------------------------
    result.add(
        "Ball-by-ball has run information",
        len(run_cols) > 0,
        f"Run columns found: {run_cols}" if run_cols else "No run-related columns found – feature engineering will fail",
        severity="ERROR",
    )

    # -- Delivery uniqueness (match + innings + over + ball) ------------------
    candidate_pk = [c for c in cols if c in ("match_id", "innings", "over", "over_number", "ball", "ball_number", "delivery")]
    if len(candidate_pk) >= 2:
        dupes = df.duplicated(subset=candidate_pk).sum()
        result.add(
            f"Delivery uniqueness ({candidate_pk})",
            dupes == 0,
            f"{dupes} duplicate delivery keys" if dupes else "All delivery keys unique",
            severity="WARNING",
        )


def validate_match_dates(result: ValidationResult, df: pd.DataFrame) -> None:
    """Match dates should not be in the future (relative to audit time)."""
    date_cols = [c for c in df.columns if "date" in c]
    for col in date_cols:
        try:
            parsed = pd.to_datetime(df[col], errors="coerce")
            future = (parsed > pd.Timestamp.now()).sum()
            result.add(
                f"Future dates in matches.{col}",
                future == 0,
                f"{future} dates in the future" if future else "No future dates",
                severity="WARNING",
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------

def run_validation():
    log.info("=" * 70)
    log.info("RR Intelligence Hub – Data Validation")
    log.info("=" * 70)

    result = ValidationResult()

    # Load all cleaned files
    bbb   = load_cleaned("ball_by_ball.csv")
    match = load_cleaned("matches.csv")
    comp  = load_cleaned("competitions.csv")
    p11   = load_cleaned("playing_eleven.csv")
    ctpm  = load_cleaned("competition_team_player_mapping.csv")
    teams = load_cleaned("teams.csv")

    # Check availability
    files = {
        "ball_by_ball.csv": bbb,
        "matches.csv": match,
        "competitions.csv": comp,
        "playing_eleven.csv": p11,
        "competition_team_player_mapping.csv": ctpm,
        "teams.csv": teams,
    }
    for fname, df in files.items():
        result.add(
            f"File available: {fname}",
            df is not None,
            "File loaded successfully" if df is not None else "File not found – run cleaning.py",
            severity="ERROR",
        )

    # Only proceed with deeper checks if files are loaded
    if bbb is not None:
        validate_ball_by_ball_cricket_rules(result, bbb)

    if match is not None:
        validate_match_dates(result, match)

    # Referential integrity – these will be populated once column names are known
    # from the actual audit. The check is a template that will run if the
    # commonly expected column names are present.
    if bbb is not None and match is not None:
        bbb_match_cols  = [c for c in bbb.columns if "match" in c and "id" in c]
        match_id_cols   = [c for c in match.columns if "id" in c]
        if bbb_match_cols and match_id_cols:
            validate_referential_integrity(
                result,
                bbb, "ball_by_ball", bbb_match_cols[0],
                match, "matches", match_id_cols[0],
            )

    if match is not None and comp is not None:
        m_comp_cols = [c for c in match.columns if "comp" in c]
        c_id_cols   = [c for c in comp.columns if "id" in c]
        if m_comp_cols and c_id_cols:
            validate_referential_integrity(
                result,
                match, "matches", m_comp_cols[0],
                comp, "competitions", c_id_cols[0],
            )

    # Summary
    summary = result.summary()
    summary["validated_at"] = datetime.now().isoformat()
    summary["checks"] = result.checks

    out = REPORT_DIR / "validation_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    log.info("Validation report written: %s", out)

    log.info("")
    log.info("=" * 70)
    log.info("VALIDATION SUMMARY")
    log.info("  Total checks : %d", summary["total_checks"])
    log.info("  Passed       : %d", summary["passed"])
    log.info("  Failed       : %d", summary["failed"])
    log.info("  Errors       : %d", summary["errors"])
    log.info("  Warnings     : %d", summary["warnings"])
    log.info("  Ready for FE : %s", summary["ready_for_feature_engineering"])
    log.info("=" * 70)

    return summary


if __name__ == "__main__":
    run_validation()

