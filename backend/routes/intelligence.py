"""
backend/routes/intelligence.py
==============================
RR Intelligence Hub – Advanced Intelligence & Smart Selector Endpoints
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.connection import get_db
from database.models import Player
from intelligence.smart_selector import SmartSelector
from intelligence.pressure_engine import PressureEngine

router = APIRouter(tags=["Intelligence Engines"])
pressure_engine_instance = PressureEngine()


@router.get("/pressure/player/{player_id}")
def get_player_pressure_analyzer(
    player_id: int,
    format: str = Query("All", description="Format filter: 'All', 'IPL', 'T20I'"),
    db: Session = Depends(get_db)
):
    """Deep Player Pressure Percentage Analyzer for any individual player."""
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found")

    analysis = pressure_engine_instance.analyze_player_pressure(
        player_id=player.player_id,
        player_role=player.primary_role or "Top Order Anchor"
    )

    analysis["player_name"] = player.name
    analysis["primary_role"] = player.primary_role
    analysis["batting_style"] = player.batting_style
    analysis["bowling_style"] = player.bowling_style
    analysis["matches_played"] = player.matches_played
    analysis["career_runs"] = player.total_runs
    analysis["career_wickets"] = player.total_wickets
    analysis["career_batting_avg"] = player.batting_avg
    analysis["career_strike_rate"] = player.strike_rate
    analysis["career_bowling_economy"] = player.bowling_economy
    analysis["format_filter"] = format

    return analysis


@router.get("/pressure/analysis")
def get_pressure_analysis(
    min_matches: int = Query(8, ge=1),
    limit: int = Query(20, ge=5, le=50),
    db: Session = Depends(get_db)
):
    """Module 6: Pressure rankings, clutch ratings, and verified match evidence."""
    # Top Batting Pressure Performers
    bat_pressure = (
        db.query(Player)
        .filter(Player.matches_played >= min_matches, Player.total_runs >= 150)
        .order_by(desc(Player.pressure_score))
        .limit(limit)
        .all()
    )

    # Top Bowling Pressure Performers
    bowl_pressure = (
        db.query(Player)
        .filter(Player.matches_played >= min_matches, Player.total_wickets >= 10)
        .order_by(desc(Player.pressure_score))
        .limit(limit)
        .all()
    )

    def serialize_pressure(p: Player):
        evidence = json.loads(p.pressure_evidence_json or "[]")
        return {
            "player_id": p.player_id,
            "name": p.name,
            "primary_role": p.primary_role,
            "matches_played": p.matches_played,
            "total_runs": p.total_runs,
            "strike_rate": p.strike_rate,
            "total_wickets": p.total_wickets,
            "bowling_economy": p.bowling_economy,
            "pressure_score": p.pressure_score,
            "clutch_rating": p.clutch_rating,
            "evidence": evidence,
        }

    return {
        "batting_pressure_rankings": [serialize_pressure(p) for p in bat_pressure],
        "bowling_pressure_rankings": [serialize_pressure(p) for p in bowl_pressure],
        "pressure_criteria": [
            "Innings 2 run-chases (required run rate > 9.0 RPO)",
            "Death overs (overs 16 to 20 in both innings)",
            "Powerplay collapse recovery situations (early top-order wickets)",
            "Knockout / Playoff match pressure situations"
        ]
    }


@router.get("/suitability/{role}")
def get_role_suitability(
    role: str,
    min_matches: int = Query(5, ge=1),
    limit: int = Query(15, ge=5, le=50),
    db: Session = Depends(get_db)
):
    """Module 7: Evaluate player suitability for a specific tactical role."""
    players = db.query(Player).filter(Player.matches_played >= min_matches).all()

    scored_players = []
    for p in players:
        role_scores = json.loads(p.role_scores_json or "{}")
        explanations = json.loads(p.role_explanations_json or "{}")
        score = role_scores.get(role, 0.0)
        if score > 0:
            scored_players.append({
                "player_id": p.player_id,
                "name": p.name,
                "batting_style": p.batting_style,
                "bowling_style": p.bowling_style,
                "primary_role": p.primary_role,
                "matches_played": p.matches_played,
                "total_runs": p.total_runs,
                "batting_avg": p.batting_avg,
                "strike_rate": p.strike_rate,
                "total_wickets": p.total_wickets,
                "bowling_economy": p.bowling_economy,
                "consistency_score": p.consistency_score,
                "pressure_score": p.pressure_score,
                "suitability_score": score,
                "role_explanation": explanations.get(role, "Evaluated against role benchmarks"),
                "strengths": json.loads(p.strengths_json or "[]"),
                "radar_metrics": json.loads(p.radar_metrics_json or "{}"),
            })

    scored_players.sort(key=lambda x: x["suitability_score"], reverse=True)
    return {
        "role": role,
        "total_evaluated": len(scored_players),
        "candidates": scored_players[:limit]
    }


@router.get("/selector/recommendations")
def get_selector_recommendations(
    role: str = Query("All", description="Target role e.g. 'Finisher', 'Powerplay Bowler', 'All'"),
    min_matches: int = Query(5, ge=1),
    limit: int = Query(10, ge=3, le=25),
    db: Session = Depends(get_db)
):
    """Module 8: RR Smart Selector – Tactical player recommendations with explainability."""
    players = db.query(Player).filter(Player.matches_played >= min_matches).all()

    player_dicts = []
    for p in players:
        player_dicts.append({
            "player_id": p.player_id,
            "name": p.name,
            "batting_style": p.batting_style,
            "bowling_style": p.bowling_style,
            "primary_role": p.primary_role,
            "matches_played": p.matches_played,
            "total_runs": p.total_runs,
            "batting_avg": p.batting_avg,
            "strike_rate": p.strike_rate,
            "total_wickets": p.total_wickets,
            "bowling_economy": p.bowling_economy,
            "bowling_avg": p.bowling_avg,
            "consistency_score": p.consistency_score,
            "pressure_score": p.pressure_score,
            "overall_impact_score": p.overall_impact_score,
            "primary_suitability_score": p.primary_suitability_score,
            "clutch_rating": p.clutch_rating,
            "role_scores": json.loads(p.role_scores_json or "{}"),
        })

    recommendations = SmartSelector.select_candidates(
        player_dicts,
        role=role,
        min_matches=min_matches,
        limit=limit
    )

    return {
        "target_role": role,
        "criteria_weights": {
            "role_suitability": 0.40,
            "consistency": 0.20,
            "pressure_rating": 0.20,
            "overall_impact": 0.20
        },
        "count": len(recommendations),
        "recommendations": recommendations
    }
