"""
backend/routes/rankings.py
==========================
RR Intelligence Hub – Official Player Rankings Endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.connection import get_db
from database.models import Player

router = APIRouter(tags=["Rankings"])


@router.get("/rankings/batting")
def get_batting_rankings(
    min_runs: int = Query(100, ge=0),
    sort_by: str = Query("total_runs", description="total_runs, batting_avg, strike_rate, consistency_score"),
    limit: int = Query(25, ge=5, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve batting rankings sorted by performance metrics."""
    q = db.query(Player).filter(Player.total_runs >= min_runs)

    sort_map = {
        "total_runs": Player.total_runs,
        "batting_avg": Player.batting_avg,
        "strike_rate": Player.strike_rate,
        "consistency_score": Player.consistency_score,
        "fifties": Player.fifties,
        "hundreds": Player.hundreds,
    }
    sort_col = sort_map.get(sort_by, Player.total_runs)
    players = q.order_by(desc(sort_col)).limit(limit).all()

    ranks = []
    for i, p in enumerate(players, 1):
        ranks.append({
            "rank": i,
            "player_id": p.player_id,
            "name": p.name,
            "primary_role": p.primary_role,
            "matches_played": p.matches_played,
            "innings_batted": p.innings_batted,
            "total_runs": p.total_runs,
            "batting_avg": p.batting_avg,
            "strike_rate": p.strike_rate,
            "highest_score": p.highest_score,
            "fifties": p.fifties,
            "hundreds": p.hundreds,
            "fours": p.fours,
            "sixes": p.sixes,
            "consistency_score": p.consistency_score,
            "pressure_score": p.pressure_score,
        })
    return {"category": "Batting", "count": len(ranks), "rankings": ranks}


@router.get("/rankings/bowling")
def get_bowling_rankings(
    min_wickets: int = Query(5, ge=0),
    sort_by: str = Query("total_wickets", description="total_wickets, bowling_economy, bowling_avg, bowling_sr"),
    limit: int = Query(25, ge=5, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve bowling rankings sorted by performance metrics."""
    q = db.query(Player).filter(Player.total_wickets >= min_wickets)

    if sort_by in ["bowling_economy", "bowling_avg", "bowling_sr"]:
        players = q.filter(Player.overs_bowled >= 10).order_by(getattr(Player, sort_by).asc()).limit(limit).all()
    else:
        players = q.order_by(desc(Player.total_wickets)).limit(limit).all()

    ranks = []
    for i, p in enumerate(players, 1):
        ranks.append({
            "rank": i,
            "player_id": p.player_id,
            "name": p.name,
            "bowling_style": p.bowling_style,
            "primary_role": p.primary_role,
            "matches_played": p.matches_played,
            "overs_bowled": p.overs_bowled,
            "total_wickets": p.total_wickets,
            "bowling_economy": p.bowling_economy,
            "bowling_avg": p.bowling_avg,
            "bowling_sr": p.bowling_sr,
            "four_wkt_hauls": p.four_wkt_hauls,
            "five_wkt_hauls": p.five_wkt_hauls,
            "consistency_score": p.consistency_score,
            "pressure_score": p.pressure_score,
        })
    return {"category": "Bowling", "count": len(ranks), "rankings": ranks}


@router.get("/rankings/overall")
def get_overall_rankings(
    min_matches: int = Query(5, ge=0),
    limit: int = Query(25, ge=5, le=100),
    db: Session = Depends(get_db)
):
    """Retrieve overall player rankings based on multi-dimensional impact score."""
    players = (
        db.query(Player)
        .filter(Player.matches_played >= min_matches)
        .order_by(desc(Player.overall_impact_score))
        .limit(limit)
        .all()
    )

    ranks = []
    for i, p in enumerate(players, 1):
        ranks.append({
            "rank": i,
            "player_id": p.player_id,
            "name": p.name,
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
    return {"category": "Overall Impact", "count": len(ranks), "rankings": ranks}
