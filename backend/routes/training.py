"""
backend/routes/training.py
==========================
RR Intelligence Hub – Interactive ML Training Controller Endpoints
Allows user to configure hyperparameters, trigger retraining, track progress,
and record training history.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, KFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

from database.connection import get_db
from database.models import MLModelStatus
from training.train_models import build_batting_dataset, build_bowling_dataset

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("training_api")

router = APIRouter(tags=["ML Training Controller"])

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
REPORTS_DIR = PROJECT_ROOT / "reports"
HISTORY_FILE = REPORTS_DIR / "training_history.json"

# In-memory training status tracker
TRAINING_STATE = {
    "is_training": False,
    "current_task": None,
    "progress_percent": 100,
    "status_message": "Idle",
    "latest_result": None,
}


class TrainRequest(BaseModel):
    model_type: str = Field("batting", description="'batting' or 'bowling'")
    algorithm: str = Field("RandomForestRegressor", description="'RandomForestRegressor', 'GradientBoostingRegressor', or 'Ridge'")
    n_estimators: int = Field(100, ge=10, le=500)
    max_depth: Optional[int] = Field(6, ge=1, le=25)
    learning_rate: float = Field(0.08, ge=0.001, le=1.0)
    test_size: float = Field(0.2, ge=0.1, le=0.4)
    cross_validation_folds: int = Field(5, ge=2, le=10)


def load_training_history() -> List[Dict[str, Any]]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_training_history(entry: Dict[str, Any]):
    history = load_training_history()
    history.insert(0, entry)
    # Keep last 50 runs
    history = history[:50]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def execute_training(req: TrainRequest):
    global TRAINING_STATE
    TRAINING_STATE["is_training"] = True
    TRAINING_STATE["current_task"] = f"Training {req.model_type} ({req.algorithm})"
    TRAINING_STATE["progress_percent"] = 15
    TRAINING_STATE["status_message"] = "Preparing dataset & feature matrices..."

    try:
        if req.model_type == "batting":
            X, y, features = build_batting_dataset()
            save_dir = MODELS_DIR / "batting"
        else:
            X, y, features = build_bowling_dataset()
            save_dir = MODELS_DIR / "bowling"

        save_dir.mkdir(parents=True, exist_ok=True)

        TRAINING_STATE["progress_percent"] = 40
        TRAINING_STATE["status_message"] = f"Splitting data and scaling {len(features)} features..."

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=req.test_size, random_state=42
        )
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # Build chosen algorithm
        if req.algorithm == "RandomForestRegressor":
            model = RandomForestRegressor(
                n_estimators=req.n_estimators,
                max_depth=req.max_depth,
                random_state=42,
                n_jobs=-1,
            )
        elif req.algorithm == "GradientBoostingRegressor":
            model = GradientBoostingRegressor(
                n_estimators=req.n_estimators,
                learning_rate=req.learning_rate,
                max_depth=req.max_depth or 3,
                random_state=42,
            )
        else:
            model = Ridge(alpha=1.0)

        TRAINING_STATE["progress_percent"] = 60
        TRAINING_STATE["status_message"] = f"Executing {req.cross_validation_folds}-fold Cross Validation..."

        kf = KFold(n_splits=req.cross_validation_folds, shuffle=True, random_state=42)
        cv_scores = cross_val_score(
            model, X_train_scaled, y_train, cv=kf, scoring="neg_root_mean_squared_error"
        )
        cv_rmse = float(-cv_scores.mean())

        TRAINING_STATE["progress_percent"] = 80
        TRAINING_STATE["status_message"] = "Fitting final model on full training set..."

        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_test_scaled)

        mae = float(mean_absolute_error(y_test, preds))
        rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
        r2 = float(r2_score(y_test, preds))

        feat_importances = {}
        if hasattr(model, "feature_importances_"):
            for f, imp in zip(features, model.feature_importances_):
                feat_importances[f] = round(float(imp), 4)

        # Save model artifacts
        model_path = save_dir / f"{req.model_type}_model.joblib"
        scaler_path = save_dir / f"{req.model_type}_scaler.joblib"
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)

        metrics = {
            "model_type": req.model_type,
            "selected_algorithm": req.algorithm,
            "version": "1.1.0",
            "trained_at": datetime.now().isoformat(),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "features": features,
            "feature_importances": feat_importances,
            "hyperparameters": {
                "n_estimators": req.n_estimators,
                "max_depth": req.max_depth,
                "learning_rate": req.learning_rate,
                "test_size": req.test_size,
                "cv_folds": req.cross_validation_folds,
            },
            "metrics": {
                "mae": round(mae, 4),
                "rmse": round(rmse, 4),
                "r2": round(r2, 4),
                "cv_rmse": round(cv_rmse, 4),
            },
            "model_path": str(model_path.resolve()),
            "status": "TRAINED_AND_VERIFIED",
        }

        with open(save_dir / f"{req.model_type}_metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        # Record history
        history_entry = {
            "id": f"{req.model_type}-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model_type": req.model_type,
            "algorithm": req.algorithm,
            "hyperparameters": metrics["hyperparameters"],
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "r2": round(r2, 4),
            "cv_rmse": round(cv_rmse, 4),
            "samples": len(X),
        }
        save_training_history(history_entry)

        TRAINING_STATE["latest_result"] = metrics
        TRAINING_STATE["progress_percent"] = 100
        TRAINING_STATE["status_message"] = f"Training completed successfully! (RMSE: {rmse:.4f}, R2: {r2:.4f})"
    except Exception as e:
        log.exception("Training error")
        TRAINING_STATE["status_message"] = f"Error during training: {str(e)}"
    finally:
        TRAINING_STATE["is_training"] = False


@router.post("/train")
def start_model_training(req: TrainRequest, background_tasks: BackgroundTasks):
    """Trigger training with custom hyperparameters in background or sync."""
    if TRAINING_STATE["is_training"]:
        raise HTTPException(
            status_code=409,
            detail=f"Another training job is currently running: {TRAINING_STATE['current_task']}"
        )
    # Run in background task so UI remains responsive
    background_tasks.add_task(execute_training, req)
    return {
        "status": "QUEUED",
        "message": f"Training initiated for {req.model_type} using {req.algorithm}.",
        "hyperparameters": {
            "n_estimators": req.n_estimators,
            "max_depth": req.max_depth,
            "learning_rate": req.learning_rate,
            "test_size": req.test_size,
            "cv_folds": req.cross_validation_folds,
        }
    }


@router.get("/train/status")
def get_training_status():
    """Poll live training status, progress percent, and latest evaluation result."""
    return TRAINING_STATE


@router.get("/train/history")
def get_training_history():
    """Retrieve history of all training runs."""
    history = load_training_history()
    return {"total_runs": len(history), "history": history}
