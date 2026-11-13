"""
data_pipeline/audit.py
======================
RR Intelligence Hub – Dataset Audit Module
-------------------------------------------
PURPOSE:
    Inspect the six original cricket CSV files WITHOUT modifying them.
    Generate a full data dictionary and audit reports.

OUTPUTS:
    reports/data_audit/audit_summary.json
    reports/data_audit/missing_values.csv
    reports/data_audit/duplicate_report.csv
    reports/data_audit/validation_report.json
    reports/data_audit/data_dictionary.json

USAGE:
    python data_pipeline/audit.py

AUTHOR: RR Intelligence Hub
"""

import os
import sys
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("audit")

# ---------------------------------------------------------------------------
# Path configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR  = PROJECT_ROOT / "data" / "raw"
REPORT_DIR    = PROJECT_ROOT / "reports" / "data_audit"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Expected CSV files and their expected roles
# ---------------------------------------------------------------------------
EXPECTED_FILES = {
    "ball_by_ball.csv": "Delivery-level records (the core fact table)",
    "matches.csv": "Match metadata – dates, venues, results",
    "competitions.csv": "Competition / tournament metadata",
    "playing_eleven.csv": "Playing eleven for each match",
    "competition_team_player_mapping.csv": "Player-team-competition mapping",
    "teams.csv": "Team reference data",
}

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def file_hash_md5(filepath: Path) -> str:
    """Return MD5 hash of file for change tracking."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def infer_id_columns(df: pd.DataFrame) -> list[str]:
    """Heuristic: columns whose name contains 'id' (case-insensitive)."""
    return [c for c in df.columns if "id" in c.lower()]


def missing_value_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Return per-column missing value statistics."""
    total = len(df)
    missing = df.isnull().sum()
    pct = (missing / total * 100).round(2)
    dtype = df.dtypes.astype(str)
    unique = df.nunique()
    return pd.DataFrame({
        "missing_count": missing,
        "missing_pct": pct,
        "dtype": dtype,
        "unique_values": unique,
        "total_rows": total,
    })


def duplicate_profile(df: pd.DataFrame, filename: str) -> dict:
    """Return duplicate row statistics."""
    n_dupes = df.duplicated().sum()
    return {
        "file": filename,
        "total_rows": len(df),
        "duplicate_rows": int(n_dupes),
        "duplicate_pct": round(n_dupes / len(df) * 100, 2) if len(df) > 0 else 0,
    }


def describe_column_values(series: pd.Series, max_samples: int = 10) -> dict:
    """Return basic descriptive stats plus sample values for a column."""
    result: dict = {
        "dtype": str(series.dtype),
        "non_null_count": int(series.count()),
        "null_count": int(series.isnull().sum()),
        "unique_count": int(series.nunique()),
    }
    # Numeric extras
    if pd.api.types.is_numeric_dtype(series):
        result.update({
            "min": float(series.min()) if series.count() else None,
            "max": float(series.max()) if series.count() else None,
            "mean": round(float(series.mean()), 4) if series.count() else None,
            "median": float(series.median()) if series.count() else None,
            "std": round(float(series.std()), 4) if series.count() else None,
            "negative_count": int((series < 0).sum()),
        })
    # Categorical / string extras
    else:
        top_values = series.value_counts().head(max_samples).to_dict()
        result["top_values"] = {str(k): int(v) for k, v in top_values.items()}

    sample_vals = series.dropna().unique()[:max_samples].tolist()
    result["sample_values"] = [str(v) for v in sample_vals]
    return result


# ---------------------------------------------------------------------------
# Core audit function
# ---------------------------------------------------------------------------

def audit_file(filename: str, description: str) -> dict:
    """
    Audit a single CSV file.

    Returns a dictionary containing:
        - file metadata
        - schema info
        - missing value summary
        - duplicate summary
        - per-column data dictionary
        - cricket-specific observations
    """
    filepath = RAW_DATA_DIR / filename
    report: dict = {
        "filename": filename,
        "description": description,
        "audit_timestamp": datetime.now().isoformat(),
        "status": "NOT_FOUND",
    }

    if not filepath.exists():
        log.warning("MISSING: %s", filepath)
        return report

    # ---- Basic file metadata ------------------------------------------------
    file_size_kb = round(filepath.stat().st_size / 1024, 2)
    report["status"] = "FOUND"
    report["file_size_kb"] = file_size_kb
    report["md5_hash"] = file_hash_md5(filepath)

    log.info("Loading: %s (%.1f KB)", filename, file_size_kb)

    # ---- Load CSV -----------------------------------------------------------
    try:
        df = pd.read_csv(filepath, low_memory=False)
    except Exception as exc:
        report["status"] = "LOAD_ERROR"
        report["load_error"] = str(exc)
        log.error("Failed to load %s: %s", filename, exc)
        return report

    report["rows"] = len(df)
    report["columns"] = len(df.columns)
    report["column_names"] = list(df.columns)
    report["dtypes"] = {col: str(df[col].dtype) for col in df.columns}

    log.info("  Rows: %d  |  Columns: %d", len(df), len(df.columns))
    log.info("  Columns: %s", list(df.columns))

    # ---- Missing values -----------------------------------------------------
    mv = missing_value_profile(df)
    report["missing_value_summary"] = mv.to_dict(orient="index")
    report["columns_with_missing"] = [
        col for col in df.columns if df[col].isnull().any()
    ]
    report["total_missing_cells"] = int(df.isnull().sum().sum())

    # ---- Duplicates ---------------------------------------------------------
    report["duplicate_info"] = duplicate_profile(df, filename)

    # ---- ID columns ---------------------------------------------------------
    id_cols = infer_id_columns(df)
    report["probable_id_columns"] = id_cols
    id_uniqueness: dict = {}
    for col in id_cols:
        if col in df.columns:
            total = len(df)
            unique = df[col].nunique()
            id_uniqueness[col] = {
                "total_values": total,
                "unique_values": unique,
                "is_unique_key": total == unique,
                "null_count": int(df[col].isnull().sum()),
            }
    report["id_column_uniqueness"] = id_uniqueness

    # ---- Data dictionary (per-column profile) --------------------------------
    data_dict: dict = {}
    for col in df.columns:
        data_dict[col] = describe_column_values(df[col])
    report["data_dictionary"] = data_dict

    # ---- Cricket-specific observations (file-aware) --------------------------
    observations: list[str] = []

    if filename == "ball_by_ball.csv":
        # Look for delivery-related columns
        col_lower = {c.lower(): c for c in df.columns}
        checks = [
            ("wide", "Wide deliveries"),
            ("noball", "No-ball deliveries"),
            ("no_ball", "No-ball deliveries"),
            ("extra", "Extras"),
            ("run", "Runs"),
            ("wicket", "Wickets"),
            ("innings", "Innings"),
            ("over", "Over numbers"),
            ("ball", "Ball numbers"),
        ]
        for key, label in checks:
            matched = [c for c in col_lower if key in c]
            if matched:
                observations.append(f"FOUND {label} column(s): {[col_lower[m] for m in matched]}")
            else:
                observations.append(f"NOT FOUND: Expected column related to '{label}'")

        # Negative runs check
        for col in df.columns:
            if "run" in col.lower() and pd.api.types.is_numeric_dtype(df[col]):
                neg = int((df[col] < 0).sum())
                if neg > 0:
                    observations.append(f"WARNING: {neg} negative values in '{col}'")

        # Innings range check
        for col in df.columns:
            if "innings" in col.lower() and pd.api.types.is_numeric_dtype(df[col]):
                valid = df[col].isin([1, 2, 3, 4]).all()
                uniq = sorted(df[col].dropna().unique().tolist())
                observations.append(
                    f"Innings values: {uniq} | All in [1,2,3,4]: {valid}"
                )

    elif filename == "matches.csv":
        for keyword in ["date", "venue", "result", "winner", "toss"]:
            matched = [c for c in df.columns if keyword in c.lower()]
            if matched:
                observations.append(f"FOUND match metadata column: {matched}")
            else:
                observations.append(f"NOT FOUND: Expected column related to '{keyword}'")

    elif filename == "competitions.csv":
        for keyword in ["competition", "season", "year", "name"]:
            matched = [c for c in df.columns if keyword in c.lower()]
            if matched:
                observations.append(f"FOUND competition metadata column: {matched}")

    elif filename == "playing_eleven.csv":
        for keyword in ["player", "match", "team", "squad"]:
            matched = [c for c in df.columns if keyword in c.lower()]
            if matched:
                observations.append(f"FOUND playing eleven column: {matched}")

    report["cricket_observations"] = observations

    # ---- Top-level summary log -----------------------------------------------
    log.info(
        "  Missing cells: %d | Duplicate rows: %d | ID cols: %s",
        report["total_missing_cells"],
        report["duplicate_info"]["duplicate_rows"],
        id_cols,
    )

    return report


# ---------------------------------------------------------------------------
# Cross-file relationship analysis
# ---------------------------------------------------------------------------

def analyse_relationships(all_reports: dict) -> dict:
    """
    Attempt to identify join keys and referential integrity across files.
    Only runs if all files were loaded successfully.
    """
    relationships: dict = {"status": "SKIPPED", "details": []}
    loaded = {
        fname: rep
        for fname, rep in all_reports.items()
        if rep.get("status") == "FOUND"
    }
    if not loaded:
        return relationships

    # Load each found file for join analysis
    dfs: dict[str, pd.DataFrame] = {}
    for fname in loaded:
        try:
            dfs[fname] = pd.read_csv(RAW_DATA_DIR / fname, low_memory=False)
        except Exception:
            pass

    relationships["status"] = "ANALYSED"
    details: list[dict] = []

    # Ball-by-ball ↔ matches
    if "ball_by_ball.csv" in dfs and "matches.csv" in dfs:
        bbb = dfs["ball_by_ball.csv"]
        matches = dfs["matches.csv"]
        bbb_match_cols = [c for c in bbb.columns if "match" in c.lower() and "id" in c.lower()]
        match_id_cols  = [c for c in matches.columns if "id" in c.lower()]
        details.append({
            "relationship": "ball_by_ball ↔ matches",
            "ball_by_ball_match_cols": bbb_match_cols,
            "matches_id_cols": match_id_cols,
            "note": "Inspect these columns to confirm the foreign key.",
        })

    # Matches ↔ competitions
    if "matches.csv" in dfs and "competitions.csv" in dfs:
        matches = dfs["matches.csv"]
        comps   = dfs["competitions.csv"]
        m_comp_cols = [c for c in matches.columns if "comp" in c.lower() or "tournament" in c.lower()]
        c_id_cols   = [c for c in comps.columns if "id" in c.lower()]
        details.append({
            "relationship": "matches ↔ competitions",
            "matches_competition_cols": m_comp_cols,
            "competitions_id_cols": c_id_cols,
        })

    # Playing eleven ↔ matches
    if "playing_eleven.csv" in dfs and "matches.csv" in dfs:
        p11 = dfs["playing_eleven.csv"]
        m   = dfs["matches.csv"]
        p11_match = [c for c in p11.columns if "match" in c.lower()]
        m_id      = [c for c in m.columns if "id" in c.lower()]
        details.append({
            "relationship": "playing_eleven ↔ matches",
            "playing_eleven_match_cols": p11_match,
            "matches_id_cols": m_id,
        })

    relationships["details"] = details
    return relationships


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_missing_values_csv(all_reports: dict) -> None:
    """Write a consolidated missing-values CSV across all files."""
    rows: list[dict] = []
    for fname, rep in all_reports.items():
        if rep.get("status") != "FOUND":
            continue
        mv = rep.get("missing_value_summary", {})
        for col, stats in mv.items():
            rows.append({
                "file": fname,
                "column": col,
                "dtype": stats.get("dtype", ""),
                "missing_count": stats.get("missing_count", 0),
                "missing_pct": stats.get("missing_pct", 0),
                "unique_values": stats.get("unique_values", 0),
                "total_rows": stats.get("total_rows", 0),
            })
    if rows:
        df_mv = pd.DataFrame(rows)
        out = REPORT_DIR / "missing_values.csv"
        df_mv.to_csv(out, index=False)
        log.info("Written: %s", out)


def generate_duplicate_report_csv(all_reports: dict) -> None:
    """Write a consolidated duplicate-rows CSV."""
    rows = [
        rep["duplicate_info"]
        for rep in all_reports.values()
        if rep.get("status") == "FOUND"
    ]
    if rows:
        df_dup = pd.DataFrame(rows)
        out = REPORT_DIR / "duplicate_report.csv"
        df_dup.to_csv(out, index=False)
        log.info("Written: %s", out)


def generate_data_dictionary_json(all_reports: dict) -> None:
    """Write a combined data dictionary for all files."""
    dd: dict = {}
    for fname, rep in all_reports.items():
        if rep.get("status") == "FOUND":
            dd[fname] = {
                "description": rep.get("description", ""),
                "rows": rep.get("rows", 0),
                "columns": rep.get("columns", 0),
                "column_names": rep.get("column_names", []),
                "data_dictionary": rep.get("data_dictionary", {}),
            }
    out = REPORT_DIR / "data_dictionary.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dd, f, indent=2, default=str)
    log.info("Written: %s", out)


def generate_validation_report(all_reports: dict, relationships: dict) -> None:
    """Write a validation summary JSON."""
    found   = [f for f, r in all_reports.items() if r.get("status") == "FOUND"]
    missing = [f for f, r in all_reports.items() if r.get("status") == "NOT_FOUND"]
    errors  = [f for f, r in all_reports.items() if r.get("status") == "LOAD_ERROR"]

    report = {
        "audit_run_at": datetime.now().isoformat(),
        "files_expected": list(EXPECTED_FILES.keys()),
        "files_found": found,
        "files_missing": missing,
        "files_with_load_errors": errors,
        "all_files_present": len(missing) == 0 and len(errors) == 0,
        "total_rows_across_all_files": sum(
            r.get("rows", 0) for r in all_reports.values() if r.get("status") == "FOUND"
        ),
        "relationships": relationships,
        "readiness_for_cleaning": "YES" if len(found) == len(EXPECTED_FILES) else "NO – Missing files must be provided first",
    }
    out = REPORT_DIR / "validation_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    log.info("Written: %s", out)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_audit() -> dict:
    """
    Run the complete audit pipeline across all six CSV files.
    Returns the combined audit summary dictionary.
    """
    log.info("=" * 70)
    log.info("RR Intelligence Hub – Dataset Audit")
    log.info("Raw data directory: %s", RAW_DATA_DIR)
    log.info("=" * 70)

    all_reports: dict = {}

    for filename, description in EXPECTED_FILES.items():
        log.info("")
        log.info("--- Auditing: %s ---", filename)
        all_reports[filename] = audit_file(filename, description)

    log.info("")
    log.info("--- Analysing cross-file relationships ---")
    relationships = analyse_relationships(all_reports)

    # Build top-level audit summary
    audit_summary = {
        "project": "RR Intelligence Hub",
        "audit_run_at": datetime.now().isoformat(),
        "raw_data_directory": str(RAW_DATA_DIR),
        "python_version": sys.version,
        "file_reports": all_reports,
        "relationship_analysis": relationships,
    }

    # Write audit summary JSON
    out_summary = REPORT_DIR / "audit_summary.json"
    with open(out_summary, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2, default=str)
    log.info("")
    log.info("Written: %s", out_summary)

    # Write individual reports
    generate_missing_values_csv(all_reports)
    generate_duplicate_report_csv(all_reports)
    generate_data_dictionary_json(all_reports)
    generate_validation_report(all_reports, relationships)

    # ---- Console summary table -----------------------------------------------
    log.info("")
    log.info("=" * 70)
    log.info("AUDIT SUMMARY")
    log.info("=" * 70)
    log.info("%-42s  %-10s  %-8s  %-8s", "FILE", "STATUS", "ROWS", "COLS")
    log.info("-" * 70)
    for fname, rep in all_reports.items():
        status = rep.get("status", "UNKNOWN")
        rows   = rep.get("rows", "-")
        cols   = rep.get("columns", "-")
        log.info("%-42s  %-10s  %-8s  %-8s", fname, status, rows, cols)
    log.info("=" * 70)

    missing_files = [f for f, r in all_reports.items() if r["status"] == "NOT_FOUND"]
    if missing_files:
        log.warning("")
        log.warning("ACTION REQUIRED: The following CSV files are MISSING.")
        log.warning("Place them in:  %s", RAW_DATA_DIR)
        log.warning("")
        for f in missing_files:
            log.warning("  MISSING --> %s", f)
        log.warning("")
        log.warning("Data cleaning and ML training cannot begin until all files are present.")
    else:
        log.info("")
        log.info("All six CSV files are present. Ready to review and proceed to cleaning.")

    return audit_summary


if __name__ == "__main__":
    run_audit()

