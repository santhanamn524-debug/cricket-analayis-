"""
backend/schemas/player.py
=========================
RR Intelligence Hub – Pydantic Schemas for Request/Response Validation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PlayerSummary(BaseModel):
    player_id: int
    name: str
    batting_style: Optional[str] = None
    bowling_style: Optional[str] = None
    primary_role: Optional[str] = None
    matches_played: int
    total_runs: int
    batting_avg: float
    strike_rate: float
    total_wickets: int
    bowling_economy: float
    consistency_score: float
    pressure_score: float
    overall_impact_score: float
    clutch_rating: str

    class Config:
        from_attributes = True


class PlayerDetail(PlayerSummary):
    secondary_role: Optional[str] = None
    innings_batted: int
    highest_score: int
    fifties: int
    hundreds: int
    fours: int
    sixes: int
    overs_bowled: float
    runs_conceded: int
    bowling_avg: float
    bowling_sr: float
    four_wkt_hauls: int
    five_wkt_hauls: int
    primary_suitability_score: float
    role_scores: Dict[str, float]
    role_explanations: Dict[str, str]
    strengths: List[str]
    radar_metrics: Dict[str, int]
    pressure_evidence: List[Dict[str, Any]]
    recent_performances: List[Dict[str, Any]]


class CompareRequest(BaseModel):
    player_ids: List[int] = Field(..., min_length=2, max_length=5)


class BattingPredictRequest(BaseModel):
    player_id: Optional[int] = None
    career_avg: float = Field(..., ge=0.0)
    career_sr: float = Field(..., ge=0.0)
    recent_5_avg: float = Field(..., ge=0.0)
    recent_5_sr: float = Field(..., ge=0.0)
    batting_order: int = Field(default=3, ge=1, le=11)
    innings: int = Field(default=1, ge=1, le=2)
    pressure_situation: float = Field(default=1.5, ge=0.0, le=5.0)


class BowlingPredictRequest(BaseModel):
    player_id: Optional[int] = None
    career_economy: float = Field(..., ge=0.0)
    career_sr: float = Field(..., ge=0.0)
    recent_5_wkts: float = Field(..., ge=0.0)
    recent_5_econ: float = Field(..., ge=0.0)
    innings: int = Field(default=1, ge=1, le=2)
    pressure_situation: float = Field(default=1.0, ge=0.0, le=5.0)


class PredictionResponse(BaseModel):
    predicted_value: float
    metric_name: str
    confidence_interval: Dict[str, float]
    model_algorithm: str
    model_version: str
    key_drivers: List[str]
