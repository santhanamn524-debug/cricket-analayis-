"""
intelligence/suitability_engine.py
==================================
RR Intelligence Hub – Player Role Suitability Engine
Evaluates player suitability for specific tactical T20/IPL roles:
- Top Order Anchor
- Explosive Opener
- Middle Order Stabilizer
- Finisher / Death-Overs Specialist
- Powerplay Bowler
- Middle-Overs Enforcer
- Death-Overs Specialist
- All-Rounder
"""

from typing import Dict, Any, List


class SuitabilityEngine:
    @staticmethod
    def evaluate_player(player_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate player suitability across all 8 roles.
        player_stats contains:
            batting_avg, strike_rate, total_runs, matches_played,
            bowling_economy, bowling_avg, total_wickets,
            consistency_score, pressure_score,
            pp_strike_rate, death_strike_rate, pp_economy, death_economy
        """
        b_avg = float(player_stats.get("batting_avg") or 0.0)
        b_sr = float(player_stats.get("strike_rate") or 0.0)
        b_runs = int(player_stats.get("total_runs") or 0)
        m_played = int(player_stats.get("matches_played") or 1)
        
        bw_econ = float(player_stats.get("bowling_economy") or 9.5)
        bw_avg = float(player_stats.get("bowling_avg") or 35.0)
        bw_wkts = int(player_stats.get("total_wickets") or 0)

        consistency = float(player_stats.get("consistency_score") or 50.0)
        pressure = float(player_stats.get("pressure_score") or 50.0)

        pp_sr = float(player_stats.get("pp_strike_rate") or b_sr)
        death_sr = float(player_stats.get("death_strike_rate") or b_sr)
        pp_econ = float(player_stats.get("pp_economy") or bw_econ)
        death_econ = float(player_stats.get("death_economy") or bw_econ)

        scores = {}
        explanations = {}

        # 1. Top Order Anchor (High average, consistency, solid SR 125-140)
        anchor_score = (
            min(100.0, (b_avg / 38.0) * 45) +
            min(100.0, (consistency / 80.0) * 35) +
            min(100.0, (b_sr / 135.0) * 20)
        ) if b_runs >= 150 else 20.0
        scores["Top Order Anchor"] = round(min(98.0, anchor_score), 1)
        explanations["Top Order Anchor"] = (
            f"Batting average of {b_avg:.1f} with consistency rating of {consistency:.1f} provides high innings longevity."
        )

        # 2. Explosive Opener (Very high SR > 145, powerplay boundary hitting)
        exp_score = (
            min(100.0, (pp_sr / 155.0) * 55) +
            min(100.0, (b_avg / 30.0) * 25) +
            min(100.0, (b_sr / 150.0) * 20)
        ) if b_runs >= 100 else 15.0
        scores["Explosive Opener"] = round(min(98.0, exp_score), 1)
        explanations["Explosive Opener"] = (
            f"Powerplay intent indicated by {pp_sr:.1f} strike-rate and career boundary generation capacity."
        )

        # 3. Middle Order Stabilizer (Handles spin, rotates strike, recovers collapses)
        middle_score = (
            min(100.0, (b_avg / 34.0) * 40) +
            min(100.0, (b_sr / 135.0) * 30) +
            min(100.0, (pressure / 75.0) * 30)
        ) if b_runs >= 120 else 20.0
        scores["Middle Order Stabilizer"] = round(min(98.0, middle_score), 1)
        explanations["Middle Order Stabilizer"] = (
            f"Solid pressure tolerance ({pressure:.1f}) and adaptable tempo control in overs 7-15."
        )

        # 4. Finisher / Death-Overs Specialist (Death SR > 160, high clutch factor)
        finisher_score = (
            min(100.0, (death_sr / 175.0) * 50) +
            min(100.0, (pressure / 80.0) * 35) +
            min(100.0, (b_sr / 145.0) * 15)
        ) if b_runs >= 80 else 15.0
        scores["Finisher"] = round(min(98.0, finisher_score), 1)
        explanations["Finisher"] = (
            f"Accelerates at {death_sr:.1f} SR at the death with a pressure score of {pressure:.1f}."
        )

        # 5. Powerplay Strike Bowler (Tight PP economy < 7.2, early wicket capacity)
        pp_bowl_score = (
            max(0.0, min(100.0, (10.0 - pp_econ) * 18.0)) * 0.55 +
            max(0.0, min(100.0, (35.0 - bw_avg) * 3.5)) * 0.45
        ) if bw_wkts >= 5 else 15.0
        scores["Powerplay Bowler"] = round(min(98.0, pp_bowl_score), 1)
        explanations["Powerplay Bowler"] = (
            f"Restricts early overs with {pp_econ:.2f} PP economy and reliable new-ball penetration."
        )

        # 6. Middle-Overs Enforcer (Bowling SR < 20, wicket taker in middle overs)
        mid_bowl_score = (
            max(0.0, min(100.0, (30.0 - min(30.0, bw_avg)) * 3.8)) * 0.50 +
            max(0.0, min(100.0, (9.5 - bw_econ) * 18.0)) * 0.35 +
            min(100.0, (consistency / 75.0) * 15)
        ) if bw_wkts >= 8 else 15.0
        scores["Middle-Overs Enforcer"] = round(min(98.0, mid_bowl_score), 1)
        explanations["Middle-Overs Enforcer"] = (
            f"Controls middle phase with career bowling average of {bw_avg:.1f} and economy {bw_econ:.2f}."
        )

        # 7. Death-Overs Specialist Bowler (Low death economy, yorker execution under pressure)
        death_bowl_score = (
            max(0.0, min(100.0, (12.0 - death_econ) * 17.0)) * 0.50 +
            min(100.0, (pressure / 78.0) * 35) +
            max(0.0, min(100.0, (28.0 - bw_avg) * 3.0)) * 0.15
        ) if bw_wkts >= 6 else 15.0
        scores["Death-Overs Specialist"] = round(min(98.0, death_bowl_score), 1)
        explanations["Death-Overs Specialist"] = (
            f"Executes under high stakes with death economy of {death_econ:.2f} and {pressure:.1f} pressure resilience."
        )

        # 8. All-Rounder (Dual threat: runs and wickets)
        all_rounder_score = (
            (min(100.0, (b_runs / 400.0) * 40) + min(100.0, (b_sr / 130.0) * 15)) * 0.50 +
            (min(100.0, (bw_wkts / 15.0) * 40) + max(0.0, (9.5 - bw_econ) * 12.0)) * 0.50
        ) if (b_runs >= 60 and bw_wkts >= 4) else 15.0
        scores["All-Rounder"] = round(min(98.0, all_rounder_score), 1)
        explanations["All-Rounder"] = (
            f"Dual contribution: {b_runs} runs (SR {b_sr:.1f}) paired with {bw_wkts} wickets (Econ {bw_econ:.2f})."
        )

        # Determine Primary and Secondary Best Roles
        sorted_roles = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary_role, top_score = sorted_roles[0]
        secondary_role, sec_score = sorted_roles[1]

        # Key strengths summary
        strengths = []
        if b_sr >= 140:
            strengths.append(f"High-impact boundary striking (SR {b_sr:.1f})")
        if b_avg >= 30:
            strengths.append(f"Reliable run accumulator (Avg {b_avg:.1f})")
        if consistency >= 65:
            strengths.append(f"Exceptional match-to-match consistency ({consistency:.1f})")
        if pressure >= 70:
            strengths.append(f"High-stakes clutch performer ({pressure:.1f} pressure rating)")
        if bw_wkts >= 10:
            strengths.append(f"Proven wicket-taking threat ({bw_wkts} wickets)")
        if bw_econ <= 8.0 and bw_wkts >= 5:
            strengths.append(f"Economical bowling control ({bw_econ:.2f} economy)")

        if not strengths:
            strengths.append("Developing squad asset with targeted growth metrics")

        return {
            "primary_role": primary_role,
            "primary_suitability_score": top_score,
            "secondary_role": secondary_role,
            "secondary_suitability_score": sec_score,
            "role_scores": scores,
            "role_explanations": explanations,
            "strengths": strengths,
            "radar_metrics": {
                "Batting Power": min(99, int(b_sr * 0.65)),
                "Batting Consistency": min(99, int(consistency)),
                "Pressure Temperament": min(99, int(pressure)),
                "Bowling Control": min(99, int(max(10, (11.0 - bw_econ) * 16.0))),
                "Wicket Threat": min(99, int(min(99, bw_wkts * 4.5))),
            }
        }
