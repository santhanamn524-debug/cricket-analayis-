"""
tests/quick_verification.py
===========================
Focused verification of Database, Models, APIs, Pressure Engine, and Frontend assets.
Executes in under 3 seconds.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import SessionLocal
from database.models import Player, Match, DatasetStatus, MLModelStatus
from backend.routes.predictions import predict_batting_runs, predict_bowling_wickets, BattingPredictRequest, BowlingPredictRequest
from backend.routes.intelligence import get_selector_recommendations, get_player_pressure_analyzer
from backend.routes.players import list_players, compare_players, CompareRequest
from backend.routes.health import get_overview_stats, get_health

def run_quick_checks():
    print("=" * 60)
    print("RR INTELLIGENCE HUB — FAST VERIFICATION CHECKS")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Health check & DB connection
        health = get_health(db=db)
        p_count = db.query(Player).count()
        m_count = db.query(Match).count()
        d_count = db.query(DatasetStatus).count()
        ml_count = db.query(MLModelStatus).count()

        assert p_count > 1000, f"Expected >1000 players, got {p_count}"
        assert m_count == 883, f"Expected 883 matches, got {m_count}"
        assert d_count == 6, f"Expected 6 datasets, got {d_count}"
        assert ml_count >= 2, f"Expected >=2 ML models, got {ml_count}"
        print(f"[PASS] 1. Backend & DB Health: Status '{health['status']}' | DB '{health['database_type']}' ({p_count} players, {m_count} matches).")

        # 2. Overview Stats API
        overview = get_overview_stats(db=db)
        assert overview["database_ready"] is True
        print(f"[PASS] 2. Overview Stats API: Top scorer {overview['highlights']['top_run_scorer']['name']} ({overview['highlights']['top_run_scorer']['runs']} runs).")

        # 3. Player Search API
        search_res = list_players(query="Kohli", page=1, page_size=5, db=db)
        assert len(search_res["players"]) > 0, "No players found matching 'Kohli'"
        top_found = search_res["players"][0]
        print(f"[PASS] 3. Player Search Endpoint: Found '{top_found['name']}' (Role: {top_found['primary_role']}, Runs: {top_found['total_runs']}).")

        # 4. Player Comparison Endpoint
        comp_req = CompareRequest(player_ids=[47, 8])
        comp_res = compare_players(req=comp_req, db=db)
        assert comp_res["count"] == 2
        print(f"[PASS] 4. Player Comparison Endpoint: Successfully compared {comp_res['count']} players ({comp_res['players'][0]['name']} vs {comp_res['players'][1]['name']}).")
        print(f"       Insights: Batting Leader => {comp_res['insights']['batting_leader']['name']} | Clutch Leader => {comp_res['insights']['clutch_leader']['name']}")

        # 5. Pressure Analytics Percentage Analyzer
        press_res = get_player_pressure_analyzer(player_id=47, format="All", db=db)
        assert press_res["overall_pressure_percentage"] > 0
        bp = press_res["batting_pressure"]
        bwp = press_res["bowling_pressure"]
        print(f"[PASS] 5. Pressure Percentage Analyzer: {press_res['player_name']} => {press_res['overall_pressure_percentage']}% ({press_res['classification']})")
        print(f"       Batting Pressure: {bp['pressure_runs']} runs, SR {bp['pressure_strike_rate']}, {bp['pressure_balls_faced']} balls ({bp['sample_status']})")
        print(f"       Bowling Pressure: {bwp['pressure_balls_bowled']} balls ({bwp['sample_status']})")

        # 6. Smart Selector Check
        selector_res = get_selector_recommendations(role="Finisher", limit=3, min_matches=5, db=db)
        assert len(selector_res["recommendations"]) > 0
        top_rec = selector_res["recommendations"][0]
        print(f"[PASS] 6. RR Smart Selector: Top Finisher => '{top_rec['name']}' (RR Match Index: {top_rec['composite_score']}/100).")

        # 7. Model Prediction Checks
        bat_res = predict_batting_runs(
            req=BattingPredictRequest(
                career_avg=38.8,
                career_sr=155.0,
                recent_5_avg=45.0,
                recent_5_sr=160.0,
                batting_order=3,
                innings=2,
                pressure_situation=2.5
            ),
            db=db
        )
        assert bat_res["predicted_value"] > 0
        print(f"[PASS] 7. ML Batting Prediction ({bat_res['model_algorithm']}): Expected {bat_res['predicted_value']} runs (CI: {bat_res['confidence_interval']['lower']}–{bat_res['confidence_interval']['upper']}).")

        # 8. Frontend Assets & All 9 Modules Check
        front_dir = PROJECT_ROOT / "frontend"
        index_file = front_dir / "index.html"
        assert index_file.exists(), "index.html missing"
        assert (front_dir / "css" / "styles.css").exists(), "styles.css missing"
        assert (front_dir / "js" / "api.js").exists(), "api.js missing"
        assert (front_dir / "js" / "app.js").exists(), "app.js missing"

        html_text = index_file.read_text(encoding="utf-8")
        modules = [
            ("Command Centre", "tab-executive"),
            ("Player Database", "tab-players"),
            ("Smart Selector", "tab-selector"),
            ("Batter Rankings", "tab-batting"),
            ("Bowler Rankings", "tab-bowling"),
            ("Player Comparison", "tab-comparison"),
            ("Pressure Analytics", "tab-pressure"),
            ("ML Training Monitor", "tab-training-monitor"),
            ("Model Evaluation", "tab-model-eval"),
        ]
        for name, tag in modules:
            assert tag in html_text, f"Module '{name}' ({tag}) missing from frontend/index.html"

        print(f"[PASS] 8. Frontend Integrity: All 9 active modules and vertical sidebar templates verified.")

        print("=" * 60)
        print("ALL VERIFICATION CHECKS PASSED WITH 0 ERRORS!")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    run_quick_checks()
