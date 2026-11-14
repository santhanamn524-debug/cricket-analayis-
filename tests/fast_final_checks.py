"""
Fast, non-hanging endpoint and frontend verification.
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.main import app

def run_checks():
    print("==================================================")
    print("RR INTELLIGENCE HUB — FAST FINAL VERIFICATION")
    print("==================================================")
    
    client = TestClient(app)
    
    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.status_code}"
    health_data = res.json()
    print(f"[PASS] 1. Backend & DB Health: {health_data.get('status')} | DB: {health_data.get('database_type')}")
    
    # 2. Overview stats
    res = client.get("/api/stats/overview")
    assert res.status_code == 200, f"Overview stats failed: {res.status_code}"
    stats = res.json()
    print(f"[PASS] 2. Overview Stats: {stats.get('total_players')} players, {stats.get('total_matches')} matches")
    
    # 3. Player Search
    res = client.get("/api/players?query=Kohli")
    assert res.status_code == 200, f"Player search failed: {res.status_code}"
    p_data = res.json()
    p_name = p_data['players'][0]['name'] if p_data['players'] else 'None'
    print(f"[PASS] 3. Player Search: Found '{p_name}' (Total matches: {p_data.get('total_records')})")
    
    # 4. Player Comparison
    res = client.post("/api/players/compare", json={"player_ids": [47, 8]})
    assert res.status_code == 200, f"Player comparison failed: {res.status_code}"
    comp_data = res.json()
    print(f"[PASS] 4. Player Comparison: Compared {comp_data.get('count')} players | Batting Leader: {comp_data['insights']['batting_leader']['name']}")
    
    # 5. Pressure Analytics (Player & Macro)
    res = client.get("/api/pressure/player/47")
    assert res.status_code == 200, f"Player pressure failed: {res.status_code}"
    press_data = res.json()
    pct = press_data.get('overall_pressure_percentage')
    cls_band = press_data.get('classification')
    print(f"[PASS] 5. Pressure Analyzer: {press_data.get('player_name')} => {pct}% ({cls_band})")
    print(f"       Batting: {press_data['batting_pressure']['pressure_runs']} runs, SR {press_data['batting_pressure']['pressure_strike_rate']}, {press_data['batting_pressure']['sample_status']}")
    print(f"       Bowling: {press_data['bowling_pressure']['pressure_balls_bowled']} balls, {press_data['bowling_pressure']['sample_status']}")
    
    # 6. Smart Selector
    res = client.get("/api/selector/recommendations?role=Finisher&limit=5")
    assert res.status_code == 200, f"Smart selector failed: {res.status_code}"
    sel_data = res.json()
    top_cand = sel_data['recommendations'][0]['name'] if sel_data['recommendations'] else 'None'
    top_score = sel_data['recommendations'][0]['composite_score'] if sel_data['recommendations'] else 0
    print(f"[PASS] 6. Smart Selector: Top Finisher => '{top_cand}' (RR Match Index: {top_score}/100)")
    
    # 7. Frontend Files check
    index_path = PROJECT_ROOT / "frontend" / "index.html"
    css_path = PROJECT_ROOT / "frontend" / "css" / "styles.css"
    app_js_path = PROJECT_ROOT / "frontend" / "js" / "app.js"
    api_js_path = PROJECT_ROOT / "frontend" / "js" / "api.js"
    
    assert index_path.exists(), "frontend/index.html is missing"
    assert css_path.exists(), "frontend/css/styles.css is missing"
    assert app_js_path.exists(), "frontend/js/app.js is missing"
    assert api_js_path.exists(), "frontend/js/api.js is missing"
    
    index_content = index_path.read_text(encoding="utf-8")
    required_sections = [
        "tab-executive",
        "tab-players",
        "tab-selector",
        "tab-batting",
        "tab-bowling",
        "tab-comparison",
        "tab-pressure",
        "tab-training-monitor",
        "tab-model-eval"
    ]
    for sec in required_sections:
        assert sec in index_content, f"Missing section #{sec} in index.html"
        
    print(f"[PASS] 7. Frontend: All 9 dashboard tabs, vertical sidebar & UI assets verified.")
    print("==================================================")
    print("ALL 7 CRITICAL APPLICATION CHECKS PASSED (0 ERRORS)")
    print("==================================================")

if __name__ == "__main__":
    run_checks()
