"""
backend/routes/predictions.py
=============================
RR Intelligence Hub – Machine Learning Predictions Endpoints
Uses genuine Scikit-learn models persisted via Joblib.
"""

import json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import joblib
import numpy as np

from database.connection import get_db
from database.models import Player
from backend.schemas.player import (
    BattingPredictRequest,
    BowlingPredictRequest,
    PredictionResponse,
)

router = APIRouter(tags=["ML Predictions"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BATTING_MODEL_PATH = PROJECT_ROOT / "models" / "batting" / "batting_model.joblib"
BATTING_SCALER_PATH = PROJECT_ROOT / "models" / "batting" / "batting_scaler.joblib"
BATTING_METRICS_PATH = PROJECT_ROOT / "models" / "batting" / "batting_metrics.json"

BOWLING_MODEL_PATH = PROJECT_ROOT / "models" / "bowling" / "bowling_model.joblib"
BOWLING_SCALER_PATH = PROJECT_ROOT / "models" / "bowling" / "bowling_scaler.joblib"
BOWLING_METRICS_PATH = PROJECT_ROOT / "models" / "bowling" / "bowling_metrics.json"

# In-memory cached model singletons
_bat_model = None
_bat_scaler = None
_bat_metrics = None

_bowl_model = None
_bowl_scaler = None
_bowl_metrics = None


def get_batting_model():
    global _bat_model, _bat_scaler, _bat_metrics
    if _bat_model is None:
        if not BATTING_MODEL_PATH.exists():
            raise HTTPException(status_code=500, detail="Batting model not found on disk.")
        _bat_model = joblib.load(BATTING_MODEL_PATH)
        _bat_scaler = joblib.load(BATTING_SCALER_PATH)
        with open(BATTING_METRICS_PATH) as f:
            _bat_metrics = json.load(f)
    return _bat_model, _bat_scaler, _bat_metrics


def get_bowling_model():
    global _bowl_model, _bowl_scaler, _bowl_metrics
    if _bowl_model is None:
        if not BOWLING_MODEL_PATH.exists():
            raise HTTPException(status_code=500, detail="Bowling model not found on disk.")
        _bowl_model = joblib.load(BOWLING_MODEL_PATH)
        _bowl_scaler = joblib.load(BOWLING_SCALER_PATH)
        with open(BOWLING_METRICS_PATH) as f:
            _bowl_metrics = json.load(f)
    return _bowl_model, _bowl_scaler, _bowl_metrics


@router.post("/predict/batting", response_model=PredictionResponse)
def predict_batting_runs(req: BattingPredictRequest, db: Session = Depends(get_db)):
    """Predict expected runs scored in an upcoming match situation."""
    model, scaler, metrics = get_batting_model()

    # If player_id is provided, populate defaults from player profile if fields were zero
    if req.player_id:
        player = db.query(Player).filter(Player.player_id == req.player_id).first()
        if player:
            career_avg = req.career_avg if req.career_avg > 0 else player.batting_avg
            career_sr = req.career_sr if req.career_sr > 0 else player.strike_rate
            recent_avg = req.recent_5_avg if req.recent_5_avg > 0 else player.batting_avg
            recent_sr = req.recent_5_sr if req.recent_5_sr > 0 else player.strike_rate
        else:
            career_avg, career_sr, recent_avg, recent_sr = (
                req.career_avg,
                req.career_sr,
                req.recent_5_avg,
                req.recent_5_sr,
            )
    else:
        career_avg, career_sr, recent_avg, recent_sr = (
            req.career_avg,
            req.career_sr,
            req.recent_5_avg,
            req.recent_5_sr,
        )

    # Features order matching training:
    # ['career_avg', 'career_sr', 'recent_5_avg', 'recent_5_sr', 'batting_order', 'innings', 'pressure_situation']
    raw_features = np.array(
        [[
            career_avg,
            career_sr,
            recent_avg,
            recent_sr,
            req.batting_order,
            req.innings,
            req.pressure_situation,
        ]]
    )

    scaled_features = scaler.transform(raw_features)
    raw_pred = float(model.predict(scaled_features)[0])
    pred_runs = max(0.0, round(raw_pred, 1))

    test_rmse = metrics["metrics"]["rmse"]
    ci_lower = max(0.0, round(pred_runs - (test_rmse * 0.65), 1))
    ci_upper = round(pred_runs + (test_rmse * 0.65), 1)

    drivers = [
        f"Historical batting average of {career_avg:.1f} runs/dismissal",
        f"Recent 5-match form index: {recent_avg:.1f} avg @ {recent_sr:.1f} SR",
        f"Assigned batting position: No. {req.batting_order} in Innings {req.innings}",
        f"Tactical pressure coefficient: {req.pressure_situation:.1f}",
    ]

    return {
        "predicted_value": pred_runs,
        "metric_name": "Expected Runs",
        "confidence_interval": {"lower": ci_lower, "upper": ci_upper},
        "model_algorithm": metrics["selected_algorithm"],
        "model_version": metrics["version"],
        "key_drivers": drivers,
    }


@router.post("/predict/bowling", response_model=PredictionResponse)
def predict_bowling_wickets(req: BowlingPredictRequest, db: Session = Depends(get_db)):
    """Predict expected wickets taken in an upcoming match situation."""
    model, scaler, metrics = get_bowling_model()

    if req.player_id:
        player = db.query(Player).filter(Player.player_id == req.player_id).first()
        if player:
            career_econ = req.career_economy if req.career_economy > 0 else player.bowling_economy
            career_sr = req.career_sr if req.career_sr > 0 else (player.bowling_sr if player.bowling_sr > 0 else 24.0)
            recent_wkts = req.recent_5_wkts if req.recent_5_wkts > 0 else (player.total_wickets / max(1, player.matches_played))
            recent_econ = req.recent_5_econ if req.recent_5_econ > 0 else player.bowling_economy
        else:
            career_econ, career_sr, recent_wkts, recent_econ = (
                req.career_economy,
                req.career_sr,
                req.recent_5_wkts,
                req.recent_5_econ,
            )
    else:
        career_econ, career_sr, recent_wkts, recent_econ = (
            req.career_economy,
            req.career_sr,
            req.recent_5_wkts,
            req.recent_5_econ,
        )

    # Features:
    # ['career_economy', 'career_sr', 'recent_5_wkts', 'recent_5_econ', 'innings', 'pressure_situation']
    raw_features = np.array(
        [[
            career_econ,
            career_sr,
            recent_wkts,
            recent_econ,
            req.innings,
            req.pressure_situation,
        ]]
    )

    scaled_features = scaler.transform(raw_features)
    raw_pred = float(model.predict(scaled_features)[0])
    pred_wkts = max(0.0, round(raw_pred, 2))

    test_rmse = metrics["metrics"]["rmse"]
    ci_lower = max(0.0, round(pred_wkts - (test_rmse * 0.5), 1))
    ci_upper = round(pred_wkts + (test_rmse * 0.5), 1)

    drivers = [
        f"Career economy rate of {career_econ:.2f} RPO with {career_sr:.1f} balls/wicket",
        f"Recent wicket frequency: {recent_wkts:.1f} wkts/match in current block",
        f"Defending/Bowling condition: Innings {req.innings}",
        f"Target match pressure level: {req.pressure_situation:.1f}",
    ]

    return {
        "predicted_value": pred_wkts,
        "metric_name": "Expected Wickets",
        "confidence_interval": {"lower": ci_lower, "upper": ci_upper},
        "model_algorithm": metrics["selected_algorithm"],
        "model_version": metrics["version"],
        "key_drivers": drivers,
    }
