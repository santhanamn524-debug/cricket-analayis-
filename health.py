"""
backend/routes/health.py
========================
RR Intelligence Hub – System Health & Overview Endpoints
"""

import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.connection import get_db, SQLITE_PATH
from database.models import Player, Match, Competition, Team, MLModelStatus, DatasetStatus

router = APIRouter(tags=["Health & Overview"])


@router.get("/health")
def get_health(db: Session = Depends(get_db)):
    """Comprehensive system health status check."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "CONNECTED"
    except Exception as e:
        db_status = f"ERROR: {str(e)}"

    return {
        "status": "ONLINE",
        "service": "RR Intelligence Hub API",
        "database_status": db_status,
        "database_type": "SQLite" if SQLITE_PATH.exists() else "PostgreSQL",
        "version": "1.0.0",
        "timestamp": "2026-11-13T22:45:00"
    }


@router.get("/stats/overview")
def get_overview_stats(db: Session = Depends(get_db)):
    """High-level statistics for the Command Centre."""
    total_players = db.query(Player).count()
    total_matches = db.query(Match).count()
    total_competitions = db.query(Competition).count()
    total_teams = db.query(Team).count()
    total_datasets = db.query(DatasetStatus).count()
    total_models = db.query(MLModelStatus).count()

    top_run_scorer = db.query(Player).order_by(Player.total_runs.desc()).first()
    top_wicket_taker = db.query(Player).order_by(Player.total_wickets.desc()).first()
    top_clutch_player = db.query(Player).filter(Player.matches_played >= 10).order_by(Player.pressure_score.desc()).first()

    return {
        "total_players": total_players,
        "total_matches": total_matches,
        "total_competitions": total_competitions,
        "total_teams": total_teams,
        "total_datasets": total_datasets,
        "total_models": total_models,
        "database_ready": True,
        "ml_ready": total_models >= 2,
        "highlights": {
            "top_run_scorer": {
                "name": top_run_scorer.name if top_run_scorer else "N/A",
                "runs": top_run_scorer.total_runs if top_run_scorer else 0,
                "avg": top_run_scorer.batting_avg if top_run_scorer else 0.0,
                "sr": top_run_scorer.strike_rate if top_run_scorer else 0.0,
            },
            "top_wicket_taker": {
                "name": top_wicket_taker.name if top_wicket_taker else "N/A",
                "wickets": top_wicket_taker.total_wickets if top_wicket_taker else 0,
                "economy": top_wicket_taker.bowling_economy if top_wicket_taker else 0.0,
            },
            "top_clutch_player": {
                "name": top_clutch_player.name if top_clutch_player else "N/A",
                "pressure_score": top_clutch_player.pressure_score if top_clutch_player else 0.0,
                "clutch_rating": top_clutch_player.clutch_rating if top_clutch_player else "N/A",
            }
        }
    }
