"""
database/models.py
==================
RR Intelligence Hub – Database ORM Models
Defines relational models with comprehensive indexes for player stats, matches,
rankings, datasets, and ML model statuses.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, Index
try:
    from .connection import Base
except ImportError:
    from database.connection import Base


class Player(Base):
    __tablename__ = "players"

    player_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), index=True, nullable=False)
    batting_style = Column(String(64), nullable=True)
    bowling_style = Column(String(64), nullable=True)
    primary_role = Column(String(64), index=True, nullable=True)
    secondary_role = Column(String(64), nullable=True)

    # Career Batting
    matches_played = Column(Integer, default=0, index=True)
    innings_batted = Column(Integer, default=0)
    total_runs = Column(Integer, default=0, index=True)
    highest_score = Column(Integer, default=0)
    batting_avg = Column(Float, default=0.0, index=True)
    strike_rate = Column(Float, default=0.0, index=True)
    fifties = Column(Integer, default=0)
    hundreds = Column(Integer, default=0)
    fours = Column(Integer, default=0)
    sixes = Column(Integer, default=0)

    # Career Bowling
    overs_bowled = Column(Float, default=0.0)
    maidens = Column(Integer, default=0)
    runs_conceded = Column(Integer, default=0)
    total_wickets = Column(Integer, default=0, index=True)
    bowling_avg = Column(Float, default=0.0, index=True)
    bowling_economy = Column(Float, default=0.0, index=True)
    bowling_sr = Column(Float, default=0.0)
    four_wkt_hauls = Column(Integer, default=0)
    five_wkt_hauls = Column(Integer, default=0)

    # Advanced Intelligence Metrics
    consistency_score = Column(Float, default=50.0, index=True)
    pressure_score = Column(Float, default=50.0, index=True)
    clutch_rating = Column(String(32), default="Solid")
    overall_impact_score = Column(Float, default=50.0, index=True)
    primary_suitability_score = Column(Float, default=50.0)
    
    # JSON serialised rich data
    role_scores_json = Column(Text, default="{}")
    role_explanations_json = Column(Text, default="{}")
    strengths_json = Column(Text, default="[]")
    radar_metrics_json = Column(Text, default="{}")
    pressure_evidence_json = Column(Text, default="[]")
    recent_performances_json = Column(Text, default="[]")


class Match(Base):
    __tablename__ = "matches"

    match_id = Column(Integer, primary_key=True, index=True)
    comp_id = Column(Integer, index=True)
    match_date = Column(String(64), index=True)
    stage = Column(String(64))
    venue_country = Column(String(64))
    home_team = Column(String(128))
    away_team = Column(String(128))
    toss_winner = Column(String(128))
    toss_decision = Column(String(32))
    winner = Column(String(128))
    result = Column(String(128))
    is_knockout = Column(Boolean, default=False)
    season_year = Column(Integer)


class Competition(Base):
    __tablename__ = "competitions"

    comp_id = Column(Integer, primary_key=True, index=True)
    comp_name = Column(String(128), nullable=False)
    season_start_year = Column(Integer)


class Team(Base):
    __tablename__ = "teams"

    team_id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String(128), nullable=False)


class DatasetStatus(Base):
    __tablename__ = "dataset_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_name = Column(String(64), unique=True, index=True)
    total_rows = Column(Integer)
    columns = Column(Integer)
    cleaning_status = Column(String(32))
    missing_values = Column(Integer)
    duplicate_count = Column(Integer)
    validation_status = Column(String(32))
    last_updated = Column(String(64))


class MLModelStatus(Base):
    __tablename__ = "ml_model_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column(String(64), unique=True, index=True)
    algorithm = Column(String(64))
    version = Column(String(16))
    training_date = Column(String(64))
    mae = Column(Float)
    rmse = Column(Float)
    r2 = Column(Float)
    status = Column(String(32))
    file_path = Column(String(256))
