"""
intelligence/smart_selector.py
==============================
RR Intelligence Hub – RR Smart Selector Engine
Provides explainable recommendation engine for Rajasthan Royals tactical recruitment:
- Multi-criteria candidate ranking: Role Suitability (40%), Consistency (20%), Pressure Rating (20%), Form/Impact (20%)
- Explains why a player is recommended
- Highlights trade-offs and team tactical fit
"""

from typing import List, Dict, Any


class SmartSelector:
    @staticmethod
    def select_candidates(
        players: List[Dict[str, Any]],
        role: str = "All",
        min_matches: int = 5,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Filter, rank, and provide explainable recommendations for candidates."""
        candidates = []

        for p in players:
            matches = p.get("matches_played", 0)
            if matches < min_matches:
                continue

            role_scores = p.get("role_scores", {})
            primary_role = p.get("primary_role", "Top Order Anchor")
            
            # Check role match
            if role != "All" and role not in role_scores:
                continue

            target_role_score = role_scores.get(role, p.get("primary_suitability_score", 50.0)) if role != "All" else p.get("primary_suitability_score", 50.0)
            
            consistency = float(p.get("consistency_score") or 50.0)
            pressure = float(p.get("pressure_score") or 50.0)
            impact = float(p.get("overall_impact_score") or 50.0)

            # Composite recruitment index
            composite_score = round(
                (target_role_score * 0.40) +
                (consistency * 0.20) +
                (pressure * 0.20) +
                (impact * 0.20),
                1
            )

            # Generate explainability reasoning
            reasons = []
            if target_role_score >= 75:
                reasons.append(f"High role benchmark ({target_role_score:.1f}/100) for {role if role != 'All' else primary_role}")
            if pressure >= 70:
                reasons.append(f"Clutch pressure resilience rating of {pressure:.1f} in critical phases")
            if consistency >= 65:
                reasons.append(f"High match-to-match reliability with {consistency:.1f} consistency score")
            if impact >= 75:
                reasons.append(f"Proven match-winner with overall impact score of {impact:.1f}")

            if not reasons:
                reasons.append(f"Solid balanced squad option with tactical upside in {primary_role}")

            candidates.append({
                "player_id": p.get("player_id"),
                "name": p.get("name"),
                "batting_style": p.get("batting_style"),
                "bowling_style": p.get("bowling_style"),
                "primary_role": primary_role,
                "matches_played": matches,
                "total_runs": p.get("total_runs"),
                "batting_avg": p.get("batting_avg"),
                "strike_rate": p.get("strike_rate"),
                "total_wickets": p.get("total_wickets"),
                "bowling_economy": p.get("bowling_economy"),
                "bowling_avg": p.get("bowling_avg"),
                "consistency_score": consistency,
                "pressure_score": pressure,
                "suitability_score": target_role_score,
                "composite_score": composite_score,
                "clutch_rating": p.get("clutch_rating", "Solid"),
                "recommendation_reasons": reasons,
                "tactical_fit": f"Optimal for {role if role != 'All' else primary_role} with {p.get('batting_style', 'Batting')} skillset."
            })

        # Rank by composite score
        candidates.sort(key=lambda x: x["composite_score"], reverse=True)
        
        # Add rank
        for i, c in enumerate(candidates[:limit], 1):
            c["rank"] = i

        return candidates[:limit]
