"""
intelligence/pressure_engine.py
================================
RR Intelligence Hub – Pressure Situation Intelligence Engine
Calculates granular pressure percentages, batting/bowling situational metrics,
clutch classifications, sample-size protection warnings, and performance trends.
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


class PressureEngine:
    _instance = None
    _bbb_df = None
    _matches_df = None

    @classmethod
    def get_data(cls):
        """Lazy singleton loader for ball_by_ball and matches data."""
        if cls._bbb_df is None:
            bbb_path = PROCESSED_DIR / "ball_by_ball.csv"
            matches_path = PROCESSED_DIR / "matches.csv"
            if bbb_path.exists():
                cls._bbb_df = pd.read_csv(bbb_path, low_memory=False)
            if matches_path.exists():
                cls._matches_df = pd.read_csv(matches_path, low_memory=False)
        return cls._bbb_df, cls._matches_df

    def __init__(self, bbb_df: Optional[pd.DataFrame] = None, matches_df: Optional[pd.DataFrame] = None):
        if bbb_df is not None:
            self.bbb = bbb_df
        else:
            self.bbb, _ = self.get_data()

        if matches_df is not None:
            self.matches = matches_df
        else:
            _, self.matches = self.get_data()

    def get_classification(self, score: float) -> tuple[str, str]:
        """Convert 0-100 percentage score into standard RR classification band."""
        if score >= 85.0:
            return "Elite", "85–100%"
        elif score >= 70.0:
            return "Strong", "70–84%"
        elif score >= 55.0:
            return "Competitive", "55–69%"
        elif score >= 40.0:
            return "Developing", "40–54%"
        else:
            return "Needs Improvement", "<40%"

    def analyze_player_pressure(self, player_id: int, player_role: str = "Top Order Anchor") -> Dict[str, Any]:
        """
        Deep, delivery-level pressure percentage analysis for an individual player.
        Calculates distinct batting, bowling, all-rounder weighting, trend, and sample warnings.
        """
        bbb, matches = self.get_data()
        if bbb is None or bbb.empty:
            return self._empty_response(player_id)

        # 1. Batting Deliveries
        bat_deliv = bbb[bbb["striker_id"] == player_id]
        # Pressure batting criteria: Overs 16-20 OR Innings 2 run chases
        bat_pressure = bat_deliv[(bat_deliv["overid"] >= 16) | (bat_deliv["innings"] == 2)]
        
        # 2. Bowling Deliveries
        bowl_deliv = bbb[bbb["bowler_id"] == player_id]
        # Pressure bowling criteria: Overs 16-20 OR tight second innings defense
        bowl_pressure = bowl_deliv[(bowl_deliv["overid"] >= 16) | (bowl_deliv["innings"] == 2)]

        # --- Batting Metrics ---
        bat_runs = int(bat_pressure["batter_runs"].sum()) if not bat_pressure.empty else 0
        bat_balls = int(bat_pressure["is_legal_delivery"].sum()) if not bat_pressure.empty else 0
        bat_fours = int(bat_pressure["is_four"].sum()) if not bat_pressure.empty else 0
        bat_sixes = int(bat_pressure["is_six"].sum()) if not bat_pressure.empty else 0
        bat_outs = int(bat_pressure["is_wicket"].sum()) if not bat_pressure.empty else 0
        bat_matches = int(bat_pressure["match_id"].nunique()) if not bat_pressure.empty else 0

        # Qualifying matches: matches where batter faced >= 5 pressure balls
        qual_bat_matches = 0
        if not bat_pressure.empty:
            match_ball_counts = bat_pressure.groupby("match_id")["is_legal_delivery"].sum()
            qual_bat_matches = int((match_ball_counts >= 5).sum())

        bat_sr = round(float((bat_runs / bat_balls) * 100), 2) if bat_balls > 0 else 0.0
        bat_avg = round(float(bat_runs / bat_outs), 2) if bat_outs > 0 else float(bat_runs)
        bat_bnd_pct = round(float(((bat_fours + bat_sixes) / bat_balls) * 100), 2) if bat_balls > 0 else 0.0

        # Sample size safety checks
        bat_sample_warning = bat_balls < 20 or qual_bat_matches < 3
        bat_sample_status = "Limited Sample Warning" if bat_sample_warning else "Robust Sample"

        # Batting Pressure Percentage Score (0 - 100%)
        # Benchmarks: SR 155+ -> 50 pts, Avg 35+ -> 50 pts
        if bat_balls >= 10:
            sr_comp = min(50.0, (bat_sr / 160.0) * 50.0)
            avg_comp = min(50.0, (bat_avg / 36.0) * 50.0)
            bat_score_pct = round(max(15.0, min(99.0, sr_comp + avg_comp)), 1)
        elif bat_balls > 0:
            bat_score_pct = 50.0  # neutral regression for tiny sample
        else:
            bat_score_pct = 0.0

        # --- Bowling Metrics ---
        bowl_legal = int(bowl_pressure["is_legal_delivery"].sum()) if not bowl_pressure.empty else 0
        bowl_runs = int(bowl_pressure["runs"].sum()) if not bowl_pressure.empty else 0
        bowl_wkts = int(bowl_pressure["is_bowler_wicket"].sum()) if not bowl_pressure.empty else 0
        bowl_dots = int((bowl_pressure["batter_runs"] == 0).sum()) if not bowl_pressure.empty else 0
        bowl_matches = int(bowl_pressure["match_id"].nunique()) if not bowl_pressure.empty else 0

        qual_bowl_matches = 0
        if not bowl_pressure.empty:
            match_legal_counts = bowl_pressure.groupby("match_id")["is_legal_delivery"].sum()
            qual_bowl_matches = int((match_legal_counts >= 6).sum())

        bowl_overs = round(float(bowl_legal / 6.0), 1)
        bowl_econ = round(float(bowl_runs / (bowl_legal / 6.0)), 2) if bowl_legal >= 6 else (9.5 if bowl_wkts > 0 else 0.0)
        bowl_dot_pct = round(float((bowl_dots / bowl_legal) * 100), 2) if bowl_legal > 0 else 0.0
        bowl_wkt_rate = round(float(bowl_legal / bowl_wkts), 2) if bowl_wkts > 0 else 0.0

        bowl_sample_warning = bowl_legal < 24 or qual_bowl_matches < 3
        bowl_sample_status = "Limited Sample Warning" if bowl_sample_warning else "Robust Sample"

        # Bowling Pressure Percentage Score (0 - 100%)
        # Benchmarks: Economy < 7.8 -> 55 pts, Dot ball > 42% -> 45 pts
        if bowl_legal >= 12:
            econ_comp = max(0.0, min(55.0, (12.0 - bowl_econ) * 12.0))
            dot_comp = min(45.0, (bowl_dot_pct / 45.0) * 45.0)
            bowl_score_pct = round(max(15.0, min(99.0, econ_comp + dot_comp)), 1)
        elif bowl_legal > 0:
            bowl_score_pct = 50.0
        else:
            bowl_score_pct = 0.0

        # --- All-Rounder & Overall Pressure Percentage ---
        is_all_rounder = (
            "All-Rounder" in player_role or
            (bat_balls >= 30 and bowl_legal >= 24)
        )

        if is_all_rounder and bat_score_pct > 0 and bowl_score_pct > 0:
            bat_w = 0.55
            bowl_w = 0.45
            weighting_method = "Dual Impact: 55% Batting Pressure + 45% Bowling Pressure"
            overall_pct = round(float(bat_score_pct * bat_w + bowl_score_pct * bowl_w), 1)
            stronger_skill = (
                "Batting Under Pressure" if bat_score_pct > bowl_score_pct else "Bowling Under Pressure"
            )
        elif bowl_legal >= 24 and (bat_balls < 20 or "Bowler" in player_role or "Specialist" in player_role):
            bat_w = 0.0
            bowl_w = 1.0
            weighting_method = "Specialist Bowling Pressure (100%)"
            overall_pct = bowl_score_pct
            stronger_skill = "Bowling Under Pressure"
        else:
            bat_w = 1.0
            bowl_w = 0.0
            weighting_method = "Specialist Batting Pressure (100%)"
            overall_pct = bat_score_pct
            stronger_skill = "Batting Under Pressure"

        # Fallback if both scores are 0
        if overall_pct <= 0:
            overall_pct = 50.0
            overall_classification = "Developing"
            overall_band = "40–54%"
        else:
            overall_classification, overall_band = self.get_classification(overall_pct)

        # --- Situational Breakdown ---
        # 1. Death Overs (overid >= 16)
        death_b = bat_deliv[bat_deliv["overid"] >= 16]
        death_bw = bowl_deliv[bowl_deliv["overid"] >= 16]
        d_runs = int(death_b["batter_runs"].sum()) if not death_b.empty else 0
        d_balls = int(death_b["is_legal_delivery"].sum()) if not death_b.empty else 0
        d_sr = round(float((d_runs / d_balls) * 100), 1) if d_balls > 0 else 0.0
        d_wkts = int(death_bw["is_bowler_wicket"].sum()) if not death_bw.empty else 0
        d_bw_legal = int(death_bw["is_legal_delivery"].sum()) if not death_bw.empty else 0
        d_econ = round(float(death_bw["runs"].sum() / (d_bw_legal / 6.0)), 2) if d_bw_legal >= 6 else 0.0

        # 2. Innings 2 Chasing
        chase_b = bat_deliv[bat_deliv["innings"] == 2]
        chase_bw = bowl_deliv[bowl_deliv["innings"] == 2]
        c_runs = int(chase_b["batter_runs"].sum()) if not chase_b.empty else 0
        c_balls = int(chase_b["is_legal_delivery"].sum()) if not chase_b.empty else 0
        c_sr = round(float((c_runs / c_balls) * 100), 1) if c_balls > 0 else 0.0
        c_wkts = int(chase_bw["is_bowler_wicket"].sum()) if not chase_bw.empty else 0
        c_bw_legal = int(chase_bw["is_legal_delivery"].sum()) if not chase_bw.empty else 0
        c_econ = round(float(chase_bw["runs"].sum() / (c_bw_legal / 6.0)), 2) if c_bw_legal >= 6 else 0.0

        # --- Pressure Performance Trend (Last 8 Matches) ---
        trend_points = []
        if not bat_pressure.empty:
            m_groups = bat_pressure.groupby("match_id").agg(
                m_runs=("batter_runs", "sum"),
                m_balls=("is_legal_delivery", "sum")
            ).reset_index().tail(8)
            for _, r in m_groups.iterrows():
                m_sr = round(float((r["m_runs"] / r["m_balls"]) * 100), 1) if r["m_balls"] > 0 else 0.0
                trend_points.append({
                    "match_id": int(r["match_id"]),
                    "runs": int(r["m_runs"]),
                    "balls": int(r["m_balls"]),
                    "metric": m_sr,
                    "label": f"Match #{int(r['match_id'])}"
                })

        # --- Explainable Rationale ---
        total_qualifying_matches = max(qual_bat_matches, qual_bowl_matches)
        if total_qualifying_matches >= 8:
            sample_reliability = f"Sample size is robust ({bat_balls + bowl_legal} pressure deliveries across {total_qualifying_matches} qualifying matches)."
        elif total_qualifying_matches >= 3:
            sample_reliability = f"Moderate sample size ({bat_balls + bowl_legal} pressure deliveries across {total_qualifying_matches} qualifying matches). Generalizable with reasonable confidence."
        else:
            sample_reliability = f"⚠️ Limited sample size ({bat_balls + bowl_legal} pressure deliveries). Interpret percentage score provisionally."

        effectiveness = (
            f"Demonstrates {overall_classification.lower()} clutch execution ({overall_pct}%) under challenging match conditions."
            f" Strongest capability: {stronger_skill}."
        )

        return {
            "player_id": player_id,
            "overall_pressure_percentage": overall_pct,
            "classification": overall_classification,
            "classification_band": overall_band,
            "batting_pressure": {
                "pressure_score_pct": bat_score_pct,
                "pressure_strike_rate": bat_sr,
                "pressure_average": bat_avg,
                "pressure_runs": bat_runs,
                "pressure_balls_faced": bat_balls,
                "pressure_boundary_pct": bat_bnd_pct,
                "pressure_match_count": bat_matches,
                "qualifying_match_count": qual_bat_matches,
                "sample_status": bat_sample_status,
                "sample_warning": bat_sample_warning,
            },
            "bowling_pressure": {
                "pressure_score_pct": bowl_score_pct,
                "pressure_economy": bowl_econ,
                "pressure_wickets": bowl_wkts,
                "pressure_balls_bowled": bowl_legal,
                "pressure_dot_ball_pct": bowl_dot_pct,
                "pressure_wicket_rate": bowl_wkt_rate,
                "pressure_match_count": bowl_matches,
                "qualifying_match_count": qual_bowl_matches,
                "sample_status": bowl_sample_status,
                "sample_warning": bowl_sample_warning,
            },
            "all_rounder": {
                "is_all_rounder": is_all_rounder,
                "batting_weight": bat_w,
                "bowling_weight": bowl_w,
                "weighting_method": weighting_method,
            },
            "situational_breakdown": {
                "death_overs": {
                    "runs": d_runs,
                    "balls_faced": d_balls,
                    "strike_rate": d_sr,
                    "wickets": d_wkts,
                    "overs_bowled": round(float(d_bw_legal / 6.0), 1),
                    "economy": d_econ
                },
                "chase_innings_2": {
                    "runs": c_runs,
                    "balls_faced": c_balls,
                    "strike_rate": c_sr,
                    "wickets": c_wkts,
                    "overs_bowled": round(float(c_bw_legal / 6.0), 1),
                    "economy": c_econ
                }
            },
            "trend": trend_points,
            "explanation": {
                "effectiveness": effectiveness,
                "stronger_skill": stronger_skill,
                "qualifying_matches": total_qualifying_matches,
                "sample_reliability": sample_reliability,
            }
        }

    def _empty_response(self, player_id: int) -> Dict[str, Any]:
        return {
            "player_id": player_id,
            "overall_pressure_percentage": 50.0,
            "classification": "Developing",
            "classification_band": "40–54%",
            "batting_pressure": {
                "pressure_score_pct": 50.0,
                "pressure_strike_rate": 0.0,
                "pressure_average": 0.0,
                "pressure_runs": 0,
                "pressure_balls_faced": 0,
                "pressure_boundary_pct": 0.0,
                "pressure_match_count": 0,
                "qualifying_match_count": 0,
                "sample_status": "Limited Sample Warning",
                "sample_warning": True
            },
            "bowling_pressure": {
                "pressure_score_pct": 50.0,
                "pressure_economy": 0.0,
                "pressure_wickets": 0,
                "pressure_balls_bowled": 0,
                "pressure_dot_ball_pct": 0.0,
                "pressure_wicket_rate": 0.0,
                "pressure_match_count": 0,
                "qualifying_match_count": 0,
                "sample_status": "Limited Sample Warning",
                "sample_warning": True
            },
            "all_rounder": {
                "is_all_rounder": False,
                "batting_weight": 1.0,
                "bowling_weight": 0.0,
                "weighting_method": "Default Baseline"
            },
            "situational_breakdown": {
                "death_overs": {"runs": 0, "balls_faced": 0, "strike_rate": 0.0, "wickets": 0, "overs_bowled": 0.0, "economy": 0.0},
                "chase_innings_2": {"runs": 0, "balls_faced": 0, "strike_rate": 0.0, "wickets": 0, "overs_bowled": 0.0, "economy": 0.0}
            },
            "trend": [],
            "explanation": {
                "effectiveness": "Insufficient delivery records available.",
                "stronger_skill": "Undetermined",
                "qualifying_matches": 0,
                "sample_reliability": "No pressure sample recorded."
            }
        }
