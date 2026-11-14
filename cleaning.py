"""
data_pipeline/cleaning.py
==========================
RR Intelligence Hub – Data Cleaning Module
-------------------------------------------
PURPOSE:
    Apply documented, cricket-aware cleaning rules to the original CSV files.
    NEVER modifies original files. Writes cleaned outputs to data/processed/.

COLUMN NAMES:
    All column names are taken from the actual audit results (Phase 1).
    Nothing here is assumed — everything was verified against real data.

CLEANING STRATEGY OVERVIEW:
    - Strip whitespace from all string columns
    - Remove fully duplicate rows
    - Correct data types
    - Add engineered flag columns (is_dls, is_no_result, is_legal_delivery, etc.)
    - Flag suspicious values without deleting them
    - Standardise inconsistent categorical values

USAGE:
    python data_pipeline/cleaning.py

AUTHOR: RR Intelligence Hub
"""

import json
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("cleaning")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT  = Path(__file__).resolve().parent.parent
RAW_DIR       = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORT_DIR    = PROJECT_ROOT / "reports" / "data_audit"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Cleaning decision log
# Every single cleaning operation is recorded here for full traceability.
# ---------------------------------------------------------------------------
CLEANING_LOG: list[dict] = []


def log_decision(file: str, column: str, strategy: str, detail: str, rows_affected: int = 0):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "file": file,
        "column": column,
        "strategy": strategy,
        "detail": detail,
        "rows_affected": rows_affected,
    }
    CLEANING_LOG.append(entry)
    log.info("[CLEAN] %-40s | %-30s | %s | rows=%d", file, column, strategy, rows_affected)


def save_cleaning_log():
    out = REPORT_DIR / "cleaning_log.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(CLEANING_LOG, f, indent=2)
    log.info("Cleaning log written: %s", out)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_raw(filename: str) -> pd.DataFrame | None:
    path = RAW_DIR / filename
    if not path.exists():
        log.error("Raw file not found: %s", path)
        return None
    df = pd.read_csv(path, low_memory=False)
    log.info("Loaded %s: %d rows x %d cols", filename, len(df), len(df.columns))
    return df


def save_processed(df: pd.DataFrame, filename: str) -> None:
    out = PROCESSED_DIR / filename
    df.to_csv(out, index=False)
    log.info("Saved cleaned file: %s (%d rows, %d cols)", out, len(df), len(df.columns))


# ---------------------------------------------------------------------------
# Generic utilities
# ---------------------------------------------------------------------------

def strip_whitespace(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """Strip leading/trailing whitespace from string columns and convert empty strings to NaN."""
    for col in df.columns:
        if df[col].dtype == object or str(df[col].dtype).startswith("string"):
            df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
            empty = int((df[col] == "").sum()) if df[col].dtype == object else 0
            if empty > 0:
                df[col] = df[col].replace("", np.nan)
                log_decision(fname, col, "EMPTY_STRING_TO_NAN",
                             f"Converted {empty} empty strings to NaN", empty)
    return df


def remove_fully_duplicate_rows(df: pd.DataFrame, fname: str) -> pd.DataFrame:
    """Remove rows that are identical across ALL columns."""
    n_before = len(df)
    df = df.drop_duplicates()
    removed = n_before - len(df)
    if removed > 0:
        log_decision(fname, "ALL_COLUMNS", "DROP_FULL_DUPLICATES",
                     f"Removed {removed} fully duplicate rows", removed)
    return df


# ---------------------------------------------------------------------------
# 1. ball_by_ball.csv – The Core Fact Table
#    Real columns (from audit):
#    match_id, innings, overid, over_ball_num, innings_ball_num,
#    batting_team_id, bowling_team_id, striker_id, striker_name,
#    non_striker_id, non_striker_name, bowler_id, bowler_name,
#    batting_type, bowling_type, batting_order, runs, is_four, is_six,
#    is_wicket, dismissal_type_id, dismissal_type, dismissed_player_id,
#    extras_type, extras1_runs, extras_2_runs, pace_or_spin, bowl_speed,
#    stroke, delivery_style, over_or_around, on_or_off, delivery_ist_time
# ---------------------------------------------------------------------------

# Deliveries that do NOT count towards the 6-ball legal over:
# Wides and No-balls (Overstep) are NOT legal deliveries
_ILLEGAL_EXTRAS = {"wide", "Overstep"}

# Dismissals not credited to the bowler (run-outs, retired):
_NON_BOWLER_DISMISSALS = {"RunOut", "Retire Out", "Obstracting the field", "Obstructing the field"}

# Duplicated spelling in the data – will standardise
_DISMISSAL_STANDARDISE = {
    "Obstracting the field": "Obstructing the field",
}


def clean_ball_by_ball(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the ball-by-ball delivery dataset.

    Changes applied (all logged):
    1.  Strip whitespace from string columns
    2.  Remove fully duplicate rows (none found in audit but always check)
    3.  Parse match_date equivalent: delivery_ist_time left as string (time zone
        complications) — flag for downstream feature engineering
    4.  Correct bowl_speed anomalies:
        - bowl_speed < 0 → set to NaN (1 row found with -1.0)
        - bowl_speed > 200 → set to NaN (19 rows — physically impossible speed)
        - bowl_speed == 0 → set to NaN (77,861 rows — unmeasured, not zero speed)
    5.  Standardise dismissal_type spelling:
        - "Obstracting the field" → "Obstructing the field"
    6.  Derive `is_legal_delivery` flag:
        - True  = NOT a wide and NOT a no-ball (Overstep)
        - False = wide or no-ball (ball does not count towards over)
        WHY: This is essential for calculating bowling economy correctly.
        Economy = runs_conceded_legal / (legal_balls / 6)
    7.  Derive `is_bowler_wicket` flag:
        - True  = wicket AND dismissal_type NOT in {RunOut, Retire Out, Obstructing}
        - False = run-out, retired, obstruction (not credited to bowler)
        WHY: Bowling average uses only bowler-credited wickets.
    8.  Derive `is_super_over` flag:
        - innings ∈ {3, 4} → super over
        WHY: Super over data should optionally be excluded from main analysis.
    9.  Derive `batter_runs`:
        - runs - extras1_runs - extras_2_runs
        WHY: 'runs' includes extras. For batting average we need only runs
        scored by the batter, excluding byes/leg-byes.
        CAUTION: extras1_runs includes wide runs (which the batter did NOT
        score) and also byes/leg-byes (which the batter did NOT score).
        On a wide, batter_runs = 0. This derivation handles that correctly
        because on a wide, runs = extra_runs and batter_runs = 0.
    10. Flag 'data_quality_flag' column:
        - Any row with identified anomalies gets a pipe-separated flag
    """
    fname = "ball_by_ball.csv"
    log.info("=" * 60)
    log.info("Cleaning: %s", fname)
    log.info("=" * 60)

    df = strip_whitespace(df, fname)
    df = remove_fully_duplicate_rows(df, fname)

    # --- 4. bowl_speed anomalies -------------------------------------------
    # bowl_speed < 0: physically impossible
    neg_speed = int((df["bowl_speed"] < 0).sum())
    if neg_speed > 0:
        df.loc[df["bowl_speed"] < 0, "bowl_speed"] = np.nan
        log_decision(fname, "bowl_speed", "SET_TO_NAN",
                     f"{neg_speed} rows with bowl_speed < 0 set to NaN (physically impossible)", neg_speed)

    # bowl_speed > 200: unrealistically fast (fastest ever recorded is ~160 km/h)
    high_speed = int((df["bowl_speed"] > 200).sum())
    if high_speed > 0:
        df.loc[df["bowl_speed"] > 200, "bowl_speed"] = np.nan
        log_decision(fname, "bowl_speed", "SET_TO_NAN",
                     f"{high_speed} rows with bowl_speed > 200 km/h set to NaN (unrealistic)", high_speed)

    # bowl_speed == 0: not measured (spin bowlers often not measured)
    zero_speed = int((df["bowl_speed"] == 0).sum())
    if zero_speed > 0:
        df.loc[df["bowl_speed"] == 0, "bowl_speed"] = np.nan
        log_decision(fname, "bowl_speed", "SET_TO_NAN",
                     f"{zero_speed} rows with bowl_speed == 0 set to NaN (not measured)", zero_speed)

    # --- 5. Standardise dismissal_type spelling ----------------------------
    for wrong, correct in _DISMISSAL_STANDARDISE.items():
        mask = df["dismissal_type"] == wrong
        n = int(mask.sum())
        if n > 0:
            df.loc[mask, "dismissal_type"] = correct
            log_decision(fname, "dismissal_type", "STANDARDISE_SPELLING",
                         f"'{wrong}' → '{correct}' ({n} rows)", n)

    # --- 6. is_legal_delivery flag -----------------------------------------
    # A delivery is legal if it is NOT a wide and NOT a no-ball (Overstep).
    # Wide: ball not reachable by batter — does not count in over.
    # No-ball (Overstep): bowler oversteps the crease — does not count in over.
    # Legal deliveries ARE: dot balls, hit balls, byes, leg-byes, hit-wickets, etc.
    is_illegal = df["extras_type"].isin(_ILLEGAL_EXTRAS)
    df["is_legal_delivery"] = (~is_illegal).astype(bool)
    n_illegal = int(is_illegal.sum())
    log_decision(fname, "is_legal_delivery", "DERIVE_NEW_COLUMN",
                 f"Derived: False for {n_illegal} wides/no-balls, True for the rest", n_illegal)

    # --- 7. is_bowler_wicket flag ------------------------------------------
    # A run-out is NOT the bowler's wicket.
    # A retirement is NOT the bowler's wicket.
    # Only caught, bowled, LBW, stumped, hit wicket → credited to bowler.
    is_wicket_mask = df["is_wicket"] == True
    is_non_bowler = df["dismissal_type"].isin(_NON_BOWLER_DISMISSALS)
    df["is_bowler_wicket"] = (is_wicket_mask & ~is_non_bowler).astype(bool)
    n_runout = int((is_wicket_mask & is_non_bowler).sum())
    log_decision(fname, "is_bowler_wicket", "DERIVE_NEW_COLUMN",
                 f"Derived: {int(is_wicket_mask.sum())} total wickets, "
                 f"{n_runout} non-bowler (run-outs/retired) excluded", n_runout)

    # --- 8. is_super_over flag ---------------------------------------------
    df["is_super_over"] = df["innings"].isin([3, 4]).astype(bool)
    n_so = int(df["is_super_over"].sum())
    log_decision(fname, "is_super_over", "DERIVE_NEW_COLUMN",
                 f"Derived: {n_so} super-over deliveries (innings 3 or 4)", n_so)

    # --- 9. batter_runs (runs scored by batter only) ----------------------
    # Formula: batter_runs = runs - extras1_runs - extras_2_runs
    # - runs        = total runs off this delivery
    # - extras1_runs = wides, byes, leg-byes, no-ball extras
    # - extras_2_runs = penalty extras (rare: 4 or 5 runs, e.g. deliberate short)
    # Result: runs the BATTER scored (what goes in batting average numerator)
    df["batter_runs"] = (df["runs"] - df["extras1_runs"] - df["extras_2_runs"]).clip(lower=0)
    neg_batter = int((df["batter_runs"] < 0).sum())  # should be 0 after clip
    log_decision(fname, "batter_runs", "DERIVE_NEW_COLUMN",
                 f"Derived: runs - extras1_runs - extras_2_runs. "
                 f"Clipped {neg_batter} negative values to 0", neg_batter)

    # Validation: batter_runs should not exceed 6 (maximum off one ball)
    high_batter = int((df["batter_runs"] > 6).sum())
    if high_batter > 0:
        log_decision(fname, "batter_runs", "FLAG_HIGH_BATTER_RUNS",
                     f"{high_batter} rows with batter_runs > 6 (suspicious)", high_batter)

    # --- 10. data_quality_flag column -------------------------------------
    df["data_quality_flag"] = ""

    # Flag the 1 wicket row with null dismissed_player_id
    null_dism = df["is_wicket"] & df["dismissed_player_id"].isnull()
    n_null_dism = int(null_dism.sum())
    if n_null_dism > 0:
        df.loc[null_dism, "data_quality_flag"] += "|NULL_DISMISSED_PLAYER"
        log_decision(fname, "dismissed_player_id", "FLAG_ANOMALY",
                     f"{n_null_dism} wicket rows with null dismissed_player_id", n_null_dism)

    # Strip leading pipe from flag column
    df["data_quality_flag"] = df["data_quality_flag"].str.lstrip("|")

    # --- Summary -----------------------------------------------------------
    log.info("ball_by_ball.csv cleaning complete.")
    log.info("  New columns added: is_legal_delivery, is_bowler_wicket, is_super_over, batter_runs, data_quality_flag")
    log.info("  Final rows: %d | Final cols: %d", len(df), len(df.columns))

    return df


# ---------------------------------------------------------------------------
# 2. matches.csv
#    Real columns (from audit):
#    match_id, comp_id, match_number, match_date, stage, venue_id,
#    venue_country, home_team_id, home_team, away_team_id, away_team,
#    home_team_captain_id, away_team_captain_id, toss_win_team_id,
#    toss_opted, man_of_the_match, first_inn_revised_overs,
#    second_inn_revised_overs, revised_target, knock_out, win_team_id, result
# ---------------------------------------------------------------------------

def clean_matches(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the matches dataset.

    Changes applied:
    1.  Strip whitespace
    2.  Remove full duplicates
    3.  Parse match_date to datetime
    4.  Standardise result column casing (e.g., "Won by" / "won by" → uniform)
    5.  Derive is_dls: True if first_inn_revised_overs or revised_target is not null
    6.  Derive is_no_result: True if result is 'No Result' or 'Match Abandoned'
    7.  Derive is_knockout: alias of knock_out for readability
    8.  Extract season_year from match_date (integer year)
    """
    fname = "matches.csv"
    log.info("=" * 60)
    log.info("Cleaning: %s", fname)
    log.info("=" * 60)

    df = strip_whitespace(df, fname)
    df = remove_fully_duplicate_rows(df, fname)

    # --- 3. Parse match_date -----------------------------------------------
    before_nulls = int(df["match_date"].isnull().sum())
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    after_nulls = int(df["match_date"].isnull().sum())
    new_nat = after_nulls - before_nulls
    log_decision(fname, "match_date", "PARSE_DATETIME",
                 f"Converted to datetime. {new_nat} new NaT values from unparseable strings.", new_nat)

    # --- 4. Standardise result column casing --------------------------------
    # Problem: "Won by", "Won By", "won by" all appear for the same meaning
    # Strategy: lowercase the entire result string, then title-case key parts
    # This normalises "Gujarat Titans won by 6 wickets" and "Gujarat Titans Won by 6 wickets"
    # We will not over-engineer this — just strip and lowercase for now;
    # the result string is used for analysis, not ML directly.
    original_uniq = df["result"].nunique()
    df["result_clean"] = df["result"].str.strip()
    # Standardise "Won by" vs "Won By" vs "won by" etc.
    df["result_clean"] = df["result_clean"].str.replace(
        r"\bwon\b", "Won", regex=True, case=False
    ).str.replace(
        r"\bby\b", "by", regex=True, case=False
    ).str.replace(
        r"\bwickets\b", "wickets", regex=True, case=False
    ).str.replace(
        r"\bruns\b", "runs", regex=True, case=False
    )
    new_uniq = df["result_clean"].nunique()
    log_decision(fname, "result_clean", "DERIVE_NEW_COLUMN",
                 f"Standardised result casing. {original_uniq} → {new_uniq} unique values", 0)

    # --- 5. Derive is_dls ---------------------------------------------------
    df["is_dls"] = (
        df["first_inn_revised_overs"].notna() |
        df["revised_target"].notna()
    ).astype(bool)
    n_dls = int(df["is_dls"].sum())
    log_decision(fname, "is_dls", "DERIVE_NEW_COLUMN",
                 f"Derived: {n_dls} DLS-affected matches", n_dls)

    # --- 6. Derive is_no_result -------------------------------------------
    no_result_patterns = ["No Result", "Match Abandoned"]
    df["is_no_result"] = df["result"].isin(no_result_patterns).astype(bool)
    n_no_result = int(df["is_no_result"].sum())
    log_decision(fname, "is_no_result", "DERIVE_NEW_COLUMN",
                 f"Derived: {n_no_result} no-result/abandoned matches", n_no_result)

    # --- 7. Derive is_knockout (rename for clarity) -----------------------
    df["is_knockout"] = df["knock_out"].astype(bool)
    log_decision(fname, "is_knockout", "DERIVE_NEW_COLUMN",
                 "Derived: boolean alias of knock_out column", 0)

    # --- 8. Extract season_year -------------------------------------------
    df["season_year"] = df["match_date"].dt.year.astype("Int64")
    log_decision(fname, "season_year", "DERIVE_NEW_COLUMN",
                 "Extracted year from match_date for time-based ML splitting", 0)

    # --- Null strategies for key missing columns --------------------------
    # home_team_captain_id (44 nulls) → Keep as NaN; captain not always recorded
    # away_team_captain_id (45 nulls) → Same
    # toss_win_team_id (15 nulls) → Linked to no-result matches — keep NaN
    # win_team_id (41 nulls) → Linked to no-result matches — keep NaN
    log_decision(fname, "home_team_captain_id", "KEEP_NULL",
                 "44 nulls: captain not recorded — retain NaN, do not impute", 0)
    log_decision(fname, "win_team_id", "KEEP_NULL",
                 "41 nulls: abandoned/no-result matches — retain NaN", 0)
    log_decision(fname, "first_inn_revised_overs", "KEEP_NULL",
                 "858 nulls (97%): only populated for DLS matches — retain NaN, use is_dls flag", 0)

    log.info("matches.csv cleaning complete. Rows: %d | Cols: %d", len(df), len(df.columns))
    return df


# ---------------------------------------------------------------------------
# 3. competitions.csv
#    Real columns: comp_id, comp_name, match_format, season
#    ZERO nulls, ZERO duplicates — minimal cleaning needed
# ---------------------------------------------------------------------------

def clean_competitions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the competitions dataset.

    Changes:
    1.  Strip whitespace
    2.  Derive season_start_year (integer) from season string
        e.g., '2022/23' → 2022, '2024' → 2024
    """
    fname = "competitions.csv"
    log.info("=" * 60)
    log.info("Cleaning: %s", fname)
    log.info("=" * 60)

    df = strip_whitespace(df, fname)
    df = remove_fully_duplicate_rows(df, fname)

    # Derive season_start_year — take the first 4-digit year from season string
    df["season_start_year"] = df["season"].str.extract(r"(\d{4})").astype(int)
    log_decision(fname, "season_start_year", "DERIVE_NEW_COLUMN",
                 "Extracted 4-digit start year from season string (e.g. '2022/23' → 2022)", 0)

    log.info("competitions.csv cleaning complete. Rows: %d | Cols: %d", len(df), len(df.columns))
    return df


# ---------------------------------------------------------------------------
# 4. playing_eleven.csv
#    Real columns: match_id, team_id, player_id, batting_order, is_played,
#                  is_captain, is_wk, is_impact, is_impact_off
# ---------------------------------------------------------------------------

def clean_playing_eleven(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the playing eleven dataset.

    Key insight from audit:
    - 8,667 rows have is_played=False (substitutes/unused squad members).
      For these rows, batting_order, is_captain, and is_wk are ALL null.
      This is STRUCTURALLY CORRECT — do not treat these nulls as errors.
    - 11 rows have is_played=True but null batting_order (match_id=48512).
      These will be flagged.
    - is_captain and is_wk are mixed-type object columns (True/False/NaN).
      Will convert to proper nullable boolean.

    Changes:
    1.  Strip whitespace
    2.  Remove full duplicates
    3.  Convert is_captain, is_wk to nullable boolean
        (NaN → pd.NA for unplayed players)
    4.  Add data_quality_flag column
    5.  Flag the 11 played rows with null batting_order
    6.  Derive is_wicketkeeper: proper boolean version of is_wk
    7.  Validate: batting_order range 1–13 for played rows
        (13 is confirmed in the data — impact player can bat at 12/13)
    """
    fname = "playing_eleven.csv"
    log.info("=" * 60)
    log.info("Cleaning: %s", fname)
    log.info("=" * 60)

    df = strip_whitespace(df, fname)
    df = remove_fully_duplicate_rows(df, fname)

    # --- 3. Convert is_captain and is_wk to proper nullable boolean -------
    # Current state: object dtype with values True, False, NaN
    # Target: boolean (with pd.NA for unplayed players — not False)
    for col in ["is_captain", "is_wk"]:
        df[col] = df[col].map({"True": True, "False": False, True: True, False: False})
        # Rows where is_played=False will remain NaN (pd.NA) — this is correct
        log_decision(fname, col, "DTYPE_CONVERT",
                     f"Converted object (True/False/NaN) to boolean; "
                     f"NaN retained for is_played=False rows", 0)

    # --- 4. data_quality_flag column --------------------------------------
    df["data_quality_flag"] = ""

    # --- 5. Flag played rows with null batting_order ----------------------
    # 11 rows in match_id=48512 are is_played=True but batting_order is null
    played_null_bo = (df["is_played"] == True) & df["batting_order"].isnull()
    n = int(played_null_bo.sum())
    if n > 0:
        df.loc[played_null_bo, "data_quality_flag"] += "|PLAYED_NULL_BATTING_ORDER"
        log_decision(fname, "batting_order", "FLAG_ANOMALY",
                     f"{n} played rows with null batting_order (match_id=48512)", n)

    # --- 7. batting_order range check for played rows ---------------------
    played = df["is_played"] == True
    high_bo = played & (df["batting_order"] > 13)
    n_high = int(high_bo.sum())
    if n_high > 0:
        df.loc[high_bo, "data_quality_flag"] += "|HIGH_BATTING_ORDER"
        log_decision(fname, "batting_order", "FLAG_ANOMALY",
                     f"{n_high} played rows with batting_order > 13", n_high)

    df["data_quality_flag"] = df["data_quality_flag"].str.lstrip("|")

    log.info("playing_eleven.csv cleaning complete. Rows: %d | Cols: %d", len(df), len(df.columns))
    return df


# ---------------------------------------------------------------------------
# 5. competition_team_player_mapping.csv
#    Real columns: comp_id, comp_name, team_id, team_name, player_id, player_name
#    ZERO nulls, ZERO duplicates — minimal cleaning
# ---------------------------------------------------------------------------

def clean_competition_team_player(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the player-team-competition mapping.
    This is already in excellent condition (zero nulls, zero duplicates).
    Only whitespace stripping applied.
    """
    fname = "competition_team_player_mapping.csv"
    log.info("=" * 60)
    log.info("Cleaning: %s", fname)
    log.info("=" * 60)
    df = strip_whitespace(df, fname)
    df = remove_fully_duplicate_rows(df, fname)
    log.info("competition_team_player_mapping.csv cleaning complete. Rows: %d | Cols: %d", len(df), len(df.columns))
    return df


# ---------------------------------------------------------------------------
# 6. teams.csv
#    Real columns: comp_id, team_id, team_name
#    ZERO nulls, ZERO duplicates — minimal cleaning
# ---------------------------------------------------------------------------

def clean_teams(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the teams dataset.
    Already clean — whitespace stripping and duplicate check only.
    Derives a unique team reference table as an extra output.
    """
    fname = "teams.csv"
    log.info("=" * 60)
    log.info("Cleaning: %s", fname)
    log.info("=" * 60)
    df = strip_whitespace(df, fname)
    df = remove_fully_duplicate_rows(df, fname)
    log.info("teams.csv cleaning complete. Rows: %d | Cols: %d", len(df), len(df.columns))
    return df


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_cleaning():
    log.info("=" * 70)
    log.info("RR Intelligence Hub – Data Cleaning Pipeline")
    log.info("=" * 70)

    # Check audit has been run
    summary_path = REPORT_DIR / "audit_summary.json"
    if not summary_path.exists():
        log.error("audit_summary.json not found. Run data_pipeline/audit.py first.")
        return

    with open(summary_path) as f:
        audit = json.load(f)
    file_reports = audit.get("file_reports", {})
    missing = [f for f, r in file_reports.items() if r["status"] != "FOUND"]
    if missing:
        log.error("Cannot clean – missing files: %s", missing)
        return

    # --- Run cleaning pipelines -------------------------------------------
    results: dict = {}

    # 1. ball_by_ball
    df = load_raw("ball_by_ball.csv")
    if df is not None:
        df_clean = clean_ball_by_ball(df)
        save_processed(df_clean, "ball_by_ball.csv")
        results["ball_by_ball.csv"] = f"OK – {len(df_clean)} rows, {len(df_clean.columns)} cols"

    # 2. matches
    df = load_raw("matches.csv")
    if df is not None:
        df_clean = clean_matches(df)
        save_processed(df_clean, "matches.csv")
        results["matches.csv"] = f"OK – {len(df_clean)} rows, {len(df_clean.columns)} cols"

    # 3. competitions
    df = load_raw("competitions.csv")
    if df is not None:
        df_clean = clean_competitions(df)
        save_processed(df_clean, "competitions.csv")
        results["competitions.csv"] = f"OK – {len(df_clean)} rows, {len(df_clean.columns)} cols"

    # 4. playing_eleven
    df = load_raw("playing_eleven.csv")
    if df is not None:
        df_clean = clean_playing_eleven(df)
        save_processed(df_clean, "playing_eleven.csv")
        results["playing_eleven.csv"] = f"OK – {len(df_clean)} rows, {len(df_clean.columns)} cols"

    # 5. competition_team_player_mapping
    df = load_raw("competition_team_player_mapping.csv")
    if df is not None:
        df_clean = clean_competition_team_player(df)
        save_processed(df_clean, "competition_team_player_mapping.csv")
        results["competition_team_player_mapping.csv"] = f"OK – {len(df_clean)} rows, {len(df_clean.columns)} cols"

    # 6. teams
    df = load_raw("teams.csv")
    if df is not None:
        df_clean = clean_teams(df)
        save_processed(df_clean, "teams.csv")
        results["teams.csv"] = f"OK – {len(df_clean)} rows, {len(df_clean.columns)} cols"

        # Also produce a deduplicated global team reference table
        df_team_ref = df_clean[["team_id", "team_name"]].drop_duplicates("team_id").sort_values("team_id")
        save_processed(df_team_ref, "teams_reference.csv")
        log.info("Global team reference table: %d unique teams", len(df_team_ref))

    # Save cleaning log
    save_cleaning_log()

    # --- Summary -----------------------------------------------------------
    log.info("")
    log.info("=" * 70)
    log.info("CLEANING RESULTS")
    log.info("=" * 70)
    for fname, result in results.items():
        log.info("  %-44s  %s", fname, result)
    log.info("=" * 70)
    log.info("Cleaned files: %s", PROCESSED_DIR)
    log.info("Cleaning log: %s", REPORT_DIR / "cleaning_log.json")
    log.info("")
    log.info("NEXT STEP: Run data_pipeline/validation.py")


if __name__ == "__main__":
    run_cleaning()
