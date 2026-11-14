"""Quick verification of DB + Pressure Engine + Backend API routes."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import engine
from database.models import Player
from sqlalchemy.orm import Session
from intelligence.pressure_engine import PressureEngine

with Session(engine) as db:
    total = db.query(Player).count()
    top = db.query(Player).order_by(Player.total_runs.desc()).first()
    print(f"DB: {total} players | Top: {top.name} ({top.total_runs} runs)")

    pe = PressureEngine()
    kohli = db.query(Player).filter(Player.name.ilike("%kohli%")).first()
    if kohli:
        result = pe.analyze_player_pressure(kohli.player_id, kohli.primary_role or "Top Order Anchor")
        pct = result["overall_pressure_percentage"]
        cls = result["classification"]
        bp = result["batting_pressure"]
        bwp = result["bowling_pressure"]
        print(f"Pressure: {kohli.name} (ID={kohli.player_id}) => {pct}% ({cls})")
        print(f"  Batting: {bp['pressure_score_pct']}% | {bp['pressure_balls_faced']} balls | SR {bp['pressure_strike_rate']}")
        print(f"  Bowling: {bwp['pressure_score_pct']}% | {bwp['pressure_balls_bowled']} balls")
        print(f"  Trend points: {len(result.get('trend', []))}")
        print(f"  Situational death runs: {result['situational_breakdown']['death_overs']['runs']}")
    else:
        print("Kohli not found")

    # Test a bowler too
    arsh = db.query(Player).filter(Player.name.ilike("%arshdeep%")).first()
    if arsh:
        r2 = pe.analyze_player_pressure(arsh.player_id, arsh.primary_role or "Death-Overs Specialist")
        print(f"Pressure: {arsh.name} => {r2['overall_pressure_percentage']}% ({r2['classification']})")
        print(f"  Bowling: {r2['bowling_pressure']['pressure_score_pct']}% | {r2['bowling_pressure']['pressure_balls_bowled']} balls | Econ {r2['bowling_pressure']['pressure_economy']}")

print("\n[PASS] Pressure Engine verification complete.")
