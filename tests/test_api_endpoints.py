"""
tests/test_api_endpoints.py
===========================
Verifies that all API endpoints return real status and data.
"""

import sys
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    print("PASS: /api/health", data)


def test_stats_overview():
    res = client.get("/api/stats/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_players"] > 1000
    assert data["total_matches"] == 883
    print("PASS: /api/stats/overview", f"Players: {data['total_players']}, Matches: {data['total_matches']}")


def test_players_list():
    res = client.get("/api/players?page=1&page_size=5")
    assert res.status_code == 200
    data = res.json()
    assert len(data["players"]) == 5
    print("PASS: /api/players list", f"Returned {len(data['players'])} records")


def test_player_detail():
    res = client.get("/api/players?page=1&page_size=1")
    player_id = res.json()["players"][0]["player_id"]
    res_detail = client.get(f"/api/players/{player_id}")
    assert res_detail.status_code == 200
    p = res_detail.json()
    assert p["name"]
    assert "radar_metrics" in p
    print("PASS: /api/players/{id}", f"Player: {p['name']}, Role: {p['primary_role']}")


def test_rankings():
    res_bat = client.get("/api/rankings/batting?limit=5")
    assert res_bat.status_code == 200
    assert len(res_bat.json()["rankings"]) == 5

    res_bowl = client.get("/api/rankings/bowling?limit=5")
    assert res_bowl.status_code == 200
    assert len(res_bowl.json()["rankings"]) == 5

    res_ov = client.get("/api/rankings/overall?limit=5")
    assert res_ov.status_code == 200
    assert len(res_ov.json()["rankings"]) == 5
    print("PASS: /api/rankings (batting, bowling, overall)")


def test_player_comparison():
    res = client.get("/api/players?page=1&page_size=2")
    pids = [p["player_id"] for p in res.json()["players"]]
    res_cmp = client.post("/api/players/compare", json={"player_ids": pids})
    assert res_cmp.status_code == 200
    data = res_cmp.json()
    assert len(data["players"]) == 2
    print("PASS: /api/players/compare", f"Compared {pids}")


def test_predictions():
    # Batting prediction
    bat_payload = {
        "career_avg": 35.5,
        "career_sr": 142.0,
        "recent_5_avg": 38.0,
        "recent_5_sr": 148.0,
        "batting_order": 3,
        "innings": 2,
        "pressure_situation": 2.5
    }
    res_bat = client.post("/api/predict/batting", json=bat_payload)
    assert res_bat.status_code == 200
    pred_bat = res_bat.json()
    assert pred_bat["predicted_value"] > 0
    print("PASS: /api/predict/batting", pred_bat)

    # Bowling prediction
    bowl_payload = {
        "career_economy": 7.8,
        "career_sr": 19.5,
        "recent_5_wkts": 1.4,
        "recent_5_econ": 7.5,
        "innings": 1,
        "pressure_situation": 1.5
    }
    res_bowl = client.post("/api/predict/bowling", json=bowl_payload)
    assert res_bowl.status_code == 200
    pred_bowl = res_bowl.json()
    assert "predicted_value" in pred_bowl
    print("PASS: /api/predict/bowling", pred_bowl)


def test_pressure_and_suitability():
    res_p = client.get("/api/pressure/analysis?limit=5")
    assert res_p.status_code == 200
    assert len(res_p.json()["batting_pressure_rankings"]) > 0

    res_s = client.get("/api/suitability/Finisher?limit=5")
    assert res_s.status_code == 200
    assert len(res_s.json()["candidates"]) > 0

    res_rec = client.get("/api/selector/recommendations?role=Finisher&limit=5")
    assert res_rec.status_code == 200
    assert len(res_rec.json()["recommendations"]) > 0
    print("PASS: /api/pressure/analysis, /api/suitability, /api/selector/recommendations")


def test_datasets_and_models():
    res_d = client.get("/api/datasets/status")
    assert res_d.status_code == 200
    assert res_d.json()["total_datasets"] == 6

    res_m = client.get("/api/models/status")
    assert res_m.status_code == 200
    assert res_m.json()["total_models"] == 2
    print("PASS: /api/datasets/status, /api/models/status")


if __name__ == "__main__":
    test_health()
    test_stats_overview()
    test_players_list()
    test_player_detail()
    test_rankings()
    test_player_comparison()
    test_predictions()
    test_pressure_and_suitability()
    test_datasets_and_models()
    print("\nALL BACKEND API TESTS PASSED SUCCESSFULLY!")
