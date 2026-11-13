"""
training/train_models.py
=========================
RR Intelligence Hub – ML Model Training Pipeline
Trains actual Scikit-learn regression models for:
1. Batting Runs Prediction (RandomForestRegressor, GradientBoostingRegressor, Ridge)
2. Bowling Wickets Prediction (RandomForestRegressor, GradientBoostingRegressor, Ridge)

Saves trained models via joblib to models/batting/ and models/bowling/.
Saves genuine evaluation reports (MAE, RMSE, R2, cross-validation) to models/ and reports/.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("training")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"

BATTING_MODEL_DIR = MODELS_DIR / "batting"
BOWLING_MODEL_DIR = MODELS_DIR / "bowling"
BATTING_MODEL_DIR.mkdir(parents=True, exist_ok=True)
BOWLING_MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def build_batting_dataset():
    """Extract match-level batting performances and engineer features."""
    log.info("Loading processed data for batting feature engineering...")
    bbb = pd.read_csv(PROCESSED_DIR / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(PROCESSED_DIR / "matches.csv", low_memory=False)

    # Filter out super overs for cleaner training
    bbb = bbb[bbb["is_super_over"] == 0]

    # Aggregate by match, innings, striker
    bat_match = bbb.groupby(
        ["match_id", "innings", "striker_id", "striker_name"], as_index=False
    ).agg(
        runs=("batter_runs", "sum"),
        balls=("is_legal_delivery", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
        batting_order=("batting_order", "min"),
    )

    # Merge match metadata
    matches_sub = matches[["match_id", "match_date", "is_knockout", "stage"]].copy()
    matches_sub["match_date"] = pd.to_datetime(matches_sub["match_date"], errors="coerce")
    bat_match = bat_match.merge(matches_sub, on="match_id", how="left")
    bat_match = bat_match.sort_values(["striker_id", "match_date"])

    # Calculate rolling and historical metrics per striker
    records = []
    for striker_id, group in bat_match.groupby("striker_id"):
        group = group.copy()
        if len(group) < 3:
            # Need at least 3 matches to establish historical form
            continue

        group["cum_runs"] = group["runs"].shift(1).cumsum()
        group["cum_balls"] = group["balls"].shift(1).cumsum()
        group["cum_matches"] = np.arange(len(group))
        
        # Historical career avg & strike rate prior to this match
        group["career_avg"] = group["cum_runs"] / group["cum_matches"].replace(0, np.nan)
        group["career_sr"] = (group["cum_runs"] / group["cum_balls"].replace(0, np.nan)) * 100

        # Rolling 5 matches form
        group["recent_5_avg"] = group["runs"].shift(1).rolling(5, min_periods=1).mean()
        group["recent_5_sr"] = (
            group["runs"].shift(1).rolling(5, min_periods=1).sum()
            / group["balls"].shift(1).rolling(5, min_periods=1).sum().replace(0, np.nan)
        ) * 100

        # Pressure index approximation (innings 2, knockout match, late order)
        group["pressure_situation"] = (
            (group["innings"] == 2).astype(int) * 1.5
            + group["is_knockout"].fillna(0).astype(int) * 1.5
            + (group["batting_order"] >= 5).astype(int) * 1.0
        )

        records.append(group.iloc[1:])  # drop first match where historical stats are NaN

    df_bat = pd.concat(records, ignore_index=True)
    df_bat["career_avg"] = df_bat["career_avg"].fillna(df_bat["runs"])
    df_bat["career_sr"] = df_bat["career_sr"].fillna(120.0)
    df_bat["recent_5_avg"] = df_bat["recent_5_avg"].fillna(df_bat["career_avg"])
    df_bat["recent_5_sr"] = df_bat["recent_5_sr"].fillna(df_bat["career_sr"])
    df_bat["batting_order"] = df_bat["batting_order"].fillna(4.0)

    features = [
        "career_avg",
        "career_sr",
        "recent_5_avg",
        "recent_5_sr",
        "batting_order",
        "innings",
        "pressure_situation",
    ]
    target = "runs"

    X = df_bat[features]
    y = df_bat[target]
    log.info("Batting dataset ready: %d samples, %d features", len(X), len(features))
    return X, y, features


def build_bowling_dataset():
    """Extract match-level bowling performances and engineer features."""
    log.info("Loading processed data for bowling feature engineering...")
    bbb = pd.read_csv(PROCESSED_DIR / "ball_by_ball.csv", low_memory=False)
    matches = pd.read_csv(PROCESSED_DIR / "matches.csv", low_memory=False)

    bbb = bbb[bbb["is_super_over"] == 0]

    # Aggregate by match, innings, bowler
    bowl_match = bbb.groupby(
        ["match_id", "innings", "bowler_id", "bowler_name"], as_index=False
    ).agg(
        wickets=("is_bowler_wicket", "sum"),
        legal_balls=("is_legal_delivery", "sum"),
        runs_conceded=("runs", "sum"),
        dots=("batter_runs", lambda s: (s == 0).sum()),
    )

    matches_sub = matches[["match_id", "match_date", "is_knockout"]].copy()
    matches_sub["match_date"] = pd.to_datetime(matches_sub["match_date"], errors="coerce")
    bowl_match = bowl_match.merge(matches_sub, on="match_id", how="left")
    bowl_match = bowl_match.sort_values(["bowler_id", "match_date"])

    records = []
    for bowler_id, group in bowl_match.groupby("bowler_id"):
        group = group.copy()
        if len(group) < 3:
            continue

        group["cum_wickets"] = group["wickets"].shift(1).cumsum()
        group["cum_balls"] = group["legal_balls"].shift(1).cumsum()
        group["cum_runs_conceded"] = group["runs_conceded"].shift(1).cumsum()
        group["cum_matches"] = np.arange(len(group))

        # Career stats prior to match
        group["career_economy"] = (
            group["cum_runs_conceded"] / (group["cum_balls"].replace(0, np.nan) / 6.0)
        )
        group["career_sr"] = (
            group["cum_balls"] / group["cum_wickets"].replace(0, np.nan)
        )

        # Recent 5 matches form
        group["recent_5_wkts"] = group["wickets"].shift(1).rolling(5, min_periods=1).mean()
        group["recent_5_econ"] = (
            group["runs_conceded"].shift(1).rolling(5, min_periods=1).sum()
            / (group["legal_balls"].shift(1).rolling(5, min_periods=1).sum() / 6.0).replace(0, np.nan)
        )

        group["pressure_situation"] = (
            (group["innings"] == 1).astype(int) * 1.0
            + group["is_knockout"].fillna(0).astype(int) * 2.0
        )

        records.append(group.iloc[1:])

    df_bowl = pd.concat(records, ignore_index=True)
    df_bowl["career_economy"] = df_bowl["career_economy"].fillna(8.2)
    df_bowl["career_sr"] = df_bowl["career_sr"].fillna(24.0)
    df_bowl["recent_5_wkts"] = df_bowl["recent_5_wkts"].fillna(1.0)
    df_bowl["recent_5_econ"] = df_bowl["recent_5_econ"].fillna(df_bowl["career_economy"])

    features = [
        "career_economy",
        "career_sr",
        "recent_5_wkts",
        "recent_5_econ",
        "innings",
        "pressure_situation",
    ]
    target = "wickets"

    X = df_bowl[features]
    y = df_bowl[target]
    log.info("Bowling dataset ready: %d samples, %d features", len(X), len(features))
    return X, y, features


def train_and_evaluate(X, y, model_type="batting"):
    """Benchmark multiple algorithms, pick the best, fit, evaluate, and save."""
    log.info(f"--- Training {model_type.upper()} Models ---")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    candidate_models = {
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=100, max_depth=8, min_samples_split=6, random_state=42, n_jobs=-1
        ),
        "GradientBoostingRegressor": GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.08, max_depth=4, random_state=42
        ),
        "RidgeRegressor": Ridge(alpha=1.0),
    }

    comparison = {}
    best_name = None
    best_score = float("inf")  # minimize RMSE
    best_model = None

    kf = KFold(n_splits=5, shuffle=True, random_state=42)

    for name, model in candidate_models.items():
        # Cross validation negative MSE
        cv_scores = cross_val_score(
            model, X_train_scaled, y_train, cv=kf, scoring="neg_root_mean_squared_error"
        )
        cv_rmse = float(-cv_scores.mean())
        
        # Fit on train and evaluate on test
        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_test_scaled)

        mae = float(mean_absolute_error(y_test, preds))
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        r2 = float(r2_score(y_test, preds))

        log.info(f"[{name}] CV RMSE: {cv_rmse:.4f} | Test MAE: {mae:.4f} | Test RMSE: {rmse:.4f} | Test R2: {r2:.4f}")

        comparison[name] = {
            "cv_rmse": round(cv_rmse, 4),
            "test_mae": round(mae, 4),
            "test_rmse": round(rmse, 4),
            "test_r2": round(r2, 4),
        }

        if rmse < best_score:
            best_score = rmse
            best_name = name
            best_model = model

    log.info(f"Best model for {model_type}: {best_name} (RMSE: {best_score:.4f})")

    # Feature importances if available
    feat_importances = {}
    if hasattr(best_model, "feature_importances_"):
        for f, imp in zip(X.columns, best_model.feature_importances_):
            feat_importances[f] = round(float(imp), 4)

    # Save artifacts
    save_dir = BATTING_MODEL_DIR if model_type == "batting" else BOWLING_MODEL_DIR
    model_path = save_dir / f"{model_type}_model.joblib"
    scaler_path = save_dir / f"{model_type}_scaler.joblib"

    joblib.dump(best_model, model_path)
    joblib.dump(scaler, scaler_path)

    metrics = {
        "model_type": model_type,
        "selected_algorithm": best_name,
        "version": "1.0.0",
        "trained_at": datetime.now().isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "features": list(X.columns),
        "feature_importances": feat_importances,
        "metrics": {
            "mae": comparison[best_name]["test_mae"],
            "rmse": comparison[best_name]["test_rmse"],
            "r2": comparison[best_name]["test_r2"],
            "cv_rmse": comparison[best_name]["cv_rmse"],
        },
        "model_comparison": comparison,
        "model_path": str(model_path.resolve()),
        "status": "TRAINED_AND_VERIFIED",
    }

    metrics_path = save_dir / f"{model_type}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    report_path = REPORTS_DIR / f"{model_type}_training_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    log.info(f"Saved {model_type} model & metadata to {save_dir}")
    return metrics


def main():
    log.info("Starting RR Intelligence ML Model Training...")
    
    # 1. Batting Model
    X_bat, y_bat, _ = build_batting_dataset()
    bat_metrics = train_and_evaluate(X_bat, y_bat, "batting")

    # 2. Bowling Model
    X_bowl, y_bowl, _ = build_bowling_dataset()
    bowl_metrics = train_and_evaluate(X_bowl, y_bowl, "bowling")

    log.info("All ML models successfully trained and persisted!")
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE SUMMARY:")
    print(f"Batting Model: {bat_metrics['selected_algorithm']} | MAE: {bat_metrics['metrics']['mae']} | RMSE: {bat_metrics['metrics']['rmse']} | R2: {bat_metrics['metrics']['r2']}")
    print(f"Bowling Model: {bowl_metrics['selected_algorithm']} | MAE: {bowl_metrics['metrics']['mae']} | RMSE: {bowl_metrics['metrics']['rmse']} | R2: {bowl_metrics['metrics']['r2']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
