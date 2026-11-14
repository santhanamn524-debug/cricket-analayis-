"""
backend/routes/players.py
=========================
RR Intelligence Hub – Player Intelligence & Comparison Endpoints
"""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc

from database.connection import get_db
from database.models import Player
from backend.schemas.player import PlayerSummary, PlayerDetail, CompareRequest

router = APIRouter(tags=["Player Intelligence"])


def format_player_detail(player: Player) -> dict:
    """Format ORM Player into full dictionary with deserialized JSONs."""
    return {
        "player_id": player.player_id,
        "name": player.name,
        "batting_style": player.batting_style,
        "bowling_style": player.bowling_style,
        "primary_role": player.primary_role,
        "secondary_role": player.secondary_role,
        "matches_played": player.matches_played,
        "innings_batted": player.innings_batted,
        "total_runs": player.total_runs,
        "highest_score": player.highest_score,
        "batting_avg": player.batting_avg,
        "strike_rate": player.strike_rate,
        "fifties": player.fifties,
        "hundreds": player.hundreds,
        "fours": player.fours,
        "sixes": player.sixes,
        "overs_bowled": player.overs_bowled,
        "runs_conceded": player.runs_conceded,
        "total_wickets": player.total_wickets,
        "bowling_avg": player.bowling_avg,
        "bowling_economy": player.bowling_economy,
        "bowling_sr": player.bowling_sr,
        "four_wkt_hauls": player.four_wkt_hauls,
        "five_wkt_hauls": player.five_wkt_hauls,
        "consistency_score": player.consistency_score,
        "pressure_score": player.pressure_score,
        "clutch_rating": player.clutch_rating,
        "overall_impact_score": player.overall_impact_score,
        "primary_suitability_score": player.primary_suitability_score,
        "role_scores": json.loads(player.role_scores_json or "{}"),
        "role_explanations": json.loads(player.role_explanations_json or "{}"),
        "strengths": json.loads(player.strengths_json or "[]"),
        "radar_metrics": json.loads(player.radar_metrics_json or "{}"),
        "pressure_evidence": json.loads(player.pressure_evidence_json or "[]"),
        "recent_performances": json.loads(player.recent_performances_json or "[]"),
    }


@router.get("/players")
def list_players(
    query: Optional[str] = Query(None, description="Search by player name"),
    role: Optional[str] = Query(None, description="Filter by primary tactical role"),
    min_matches: int = Query(0, ge=0),
    sort_by: str = Query("total_runs", description="total_runs, total_wickets, batting_avg, strike_rate, pressure_score, consistency_score"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List and search players with dynamic filtering and pagination."""
    q = db.query(Player)

    # Handle Query defaults when called directly as function
    if hasattr(query, "default"): query = query.default
    if hasattr(role, "default"): role = role.default
    if hasattr(min_matches, "default"): min_matches = min_matches.default
    if hasattr(sort_by, "default"): sort_by = sort_by.default
    if hasattr(order, "default"): order = order.default
    if hasattr(page, "default"): page = page.default
    if hasattr(page_size, "default"): page_size = page_size.default

    if query:
        q = q.filter(Player.name.ilike(f"%{query.strip()}%"))

    if role and role != "All":
        q = q.filter(Player.primary_role == role)

    if min_matches > 0:
        q = q.filter(Player.matches_played >= min_matches)

    # Sorting
    valid_sorts = {
        "total_runs": Player.total_runs,
        "total_wickets": Player.total_wickets,
        "batting_avg": Player.batting_avg,
        "strike_rate": Player.strike_rate,
        "pressure_score": Player.pressure_score,
        "consistency_score": Player.consistency_score,
        "overall_impact_score": Player.overall_impact_score,
        "matches_played": Player.matches_played,
    }
    sort_column = valid_sorts.get(sort_by, Player.total_runs)
    q = q.order_by(desc(sort_column) if order == "desc" else asc(sort_column))

    total_records = q.count()
    players = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for p in players:
        items.append({
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
            "overall_impact_score": p.overall_impact_score,
            "clutch_rating": p.clutch_rating,
        })

    return {
        "page": page,
        "page_size": page_size,
        "total_pages": (total_records + page_size - 1) // page_size if total_records > 0 else 1,
        "total_records": total_records,
        "players": items
    }


@router.get("/players/options")
def get_player_options(db: Session = Depends(get_db)):
    """Lightweight player list for UI dropdowns and search auto-completers."""
    players = (
        db.query(Player.player_id, Player.name, Player.primary_role, Player.total_runs, Player.total_wickets)
        .order_by(asc(Player.name))
        .all()
    )
    return [
        {
            "player_id": p.player_id,
            "name": p.name,
            "primary_role": p.primary_role,
            "total_runs": p.total_runs,
            "total_wickets": p.total_wickets,
        }
        for p in players
    ]


@router.get("/players/{player_id}")
def get_player(player_id: int, db: Session = Depends(get_db)):
    """Retrieve full intelligence profile for a specific player."""
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player with ID {player_id} not found.")

    return format_player_detail(player)


@router.post("/players/compare")
def compare_players(req: CompareRequest, db: Session = Depends(get_db)):
    """Compare 2 to 5 players head-to-head with comparison metrics."""
    players = db.query(Player).filter(Player.player_id.in_(req.player_ids)).all()
    if not players:
        raise HTTPException(status_code=404, detail="None of the requested players were found.")

    formatted = [format_player_detail(p) for p in players]

    # Compute comparative benchmarks
    metrics_comparison = {
        "Batting Average": {p["name"]: p["batting_avg"] for p in formatted},
        "Strike Rate": {p["name"]: p["strike_rate"] for p in formatted},
        "Total Runs": {p["name"]: p["total_runs"] for p in formatted},
        "Total Wickets": {p["name"]: p["total_wickets"] for p in formatted},
        "Bowling Economy": {p["name"]: p["bowling_economy"] for p in formatted},
        "Bowling Average": {p["name"]: p["bowling_avg"] for p in formatted},
        "Consistency Score": {p["name"]: p["consistency_score"] for p in formatted},
        "Pressure Score": {p["name"]: p["pressure_score"] for p in formatted},
        "Overall Impact": {p["name"]: p["overall_impact_score"] for p in formatted},
    }

    # Generate comparative insights based on real stats
    best_batter = max(formatted, key=lambda x: (x["batting_avg"] * 0.5 + x["strike_rate"] * 0.5) if x["total_runs"] >= 50 else x["total_runs"])
    best_bowler = max(formatted, key=lambda x: (x["total_wickets"] * 2.0 - x["bowling_economy"]) if x["total_wickets"] >= 3 else x["total_wickets"])
    best_clutch = max(formatted, key=lambda x: x["pressure_score"])
    best_consistency = max(formatted, key=lambda x: x["consistency_score"])
    best_impact = max(formatted, key=lambda x: x["overall_impact_score"])

    insights = {
        "batting_leader": {
            "name": best_batter["name"],
            "reason": f"Dominates batting output with {best_batter['total_runs']} career runs (Avg {best_batter['batting_avg']}, SR {best_batter['strike_rate']})."
        },
        "bowling_leader": {
            "name": best_bowler["name"],
            "reason": f"Offers premier ball-in-hand potency with {best_bowler['total_wickets']} wickets at {best_bowler['bowling_economy']} economy."
        },
        "clutch_leader": {
            "name": best_clutch["name"],
            "reason": f"Top high-stakes performer with pressure rating of {best_clutch['pressure_score']} ({best_clutch['clutch_rating']})."
        },
        "consistency_leader": {
            "name": best_consistency["name"],
            "reason": f"Most reliable match-to-match asset with {best_consistency['consistency_score']} consistency score."
        },
        "overall_recommendation": {
            "name": best_impact["name"],
            "reason": f"Highest overall team value ({best_impact['overall_impact_score']}/100) combining dual-facet contributions and pressure temper."
        }
    }

    return {
        "count": len(formatted),
        "players": formatted,
        "comparison_matrix": metrics_comparison,
        "insights": insights
    }
