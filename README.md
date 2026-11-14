# RR INTELLIGENCE HUB
### *BUILD. ANALYSE. SELECT. WIN.*
**Professional Cricket Intelligence, Predictive Analytics & Squad Recruitment Platform for Rajasthan Royals**

---

## 1. System Overview

The **RR Intelligence Hub** is an elite, full-stack cricket analytics platform engineered to deliver data-backed tactical intelligence, machine-learning-driven match predictions, pressure performance evaluations, and squad recruitment decisions for Rajasthan Royals franchise leadership.

### Architecture Highlights:
- **Backend**: Python 3.14, FastAPI, Pydantic, SQLAlchemy.
- **Database**: PostgreSQL support with seamless automated fallback to high-performance local SQLite (`database/rr_intelligence.db`).
- **Data Pipeline**: Cleaned, standardised, and verified records from 6 relational CSV datasets totaling **237,170 records** (200,999 delivery-level balls, 883 matches, 141 competitions, 28,381 playing XI entries, 38 teams).
- **Machine Learning**: Persisted Scikit-learn regression models (`joblib`) for Batting Runs Prediction and Bowling Wickets Prediction with cross-validation and feature scaling.
- **Frontend**: Professional dark navy & gold UI built with HTML5, CSS3, Vanilla JavaScript, and Plotly.js charts (no heavy frontend frameworks like React/Angular/Vue/Streamlit).

---

## 2. Dashboard Modules

The single-page web dashboard provides 10 integrated modules:

1. **Executive Command Centre**: High-level tournament KPIs (1,084 players, 883 matches, 141 competitions), Top 10 Overall Impact Leaderboard, and Impact vs. Pressure distribution charts.
2. **Player Intelligence Database**: Searchable database of 1,084 players with role filtering, multi-metric sorting, and detailed player profile modals with 5-axis Radar attribute charts.
3. **RR Smart Selector**: Tactical recruitment tool matching players to tactical roles (Finisher, Explosive Opener, Death-Overs Specialist, Powerplay Bowler, All-Rounder) with explainable recommendations and composite match ratings.
4. **Batter Rankings**: Filterable rankings table with interactive Average vs. Strike Rate quadrant analysis.
5. **Bowler Rankings**: Filterable rankings table with Economy vs. Strike Rate control analysis.
6. **Player Head-to-Head Comparison**: Multi-player comparison matrix with side-by-side radar and grouped bar chart benchmarking.
7. **Pressure Engine**: Evaluation of clutch players across 4 documented pressure situations (Death overs 16–20, Innings 2 chasing, Knockout matches, Powerplay collapse) with historical match evidence.
8. **ML Training Monitor**: Interactive training console allowing users to select algorithms (Random Forest, Gradient Boosting, Ridge), tune hyperparameters (`n_estimators`, `max_depth`, `learning_rate`, `cv_folds`), trigger execution, and review training history.
9. **Model Evaluation & Prediction Sandbox**: Verified MAE, RMSE, R² scores, algorithm benchmark charts, and a live scenario sandbox predicting runs and wickets with confidence intervals.
10. **System Health & Datasets**: Relational dataset audit status, row counts, cleaning logs, and API health status.

---

#
## 3.. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service and database health check |
| `GET` | `/api/stats/overview` | Command centre overview KPIs and highlights |
| `GET` | `/api/players` | Search, filter, sort, and paginate players |
| `GET` | `/api/players/options` | Complete list of 1,084 players for dropdown selectors |
| `GET` | `/api/players/{player_id}` | Full player profile, radar metrics, and history |
| `POST` | `/api/players/compare` | Head-to-head comparison with automated insights |
| `GET` | `/api/rankings/batting` | Official batting leaderboard |
| `GET` | `/api/rankings/bowling` | Official bowling leaderboard |
| `GET` | `/api/rankings/overall` | Overall player impact rankings |
| `POST` | `/api/predict/batting` | ML-driven runs prediction with confidence intervals |
| `POST` | `/api/predict/bowling` | ML-driven wickets prediction with confidence intervals |
| `GET` | `/api/pressure/analysis` | Pressure rankings and historical match evidence |
| `GET` | `/api/suitability/{role}` | Player suitability scores for specific roles |
| `GET` | `/api/selector/recommendations` | Smart Selector recruitment recommendations |
| `POST` | `/api/train` | Trigger user-configured ML training run |
| `GET` | `/api/train/status` | Poll live training progress & status message |
| `GET` | `/api/train/history` | Retrieve full history of training iterations |
| `GET` | `/api/datasets/status` | Status of all 6 datasets, cleaning logs, validation |
| `GET` | `/api/models/status` | Current ML models evaluation metrics and versions |

---

## 4. Machine Learning Models Summary

- **Batting Predictor**:
  - Selected Algorithm: `RidgeRegressor` (with options for `RandomForestRegressor` and `GradientBoostingRegressor`)
  - Features: Career Average, Career Strike Rate, Recent 5-Match Average, Recent 5-Match Strike Rate, Batting Order, Innings, Pressure Situation
  - Test RMSE: ~20.60 runs (CV RMSE: 20.37)
- **Bowling Predictor**:
  - Selected Algorithm: `RidgeRegressor`
  - Features: Career Economy, Career Strike Rate, Recent 5-Match Wickets, Recent 5-Match Economy, Innings, Pressure Situation
  - Test RMSE: ~1.03 wickets (CV RMSE: 1.04)

---

## 5. Verification & Quality Assurance

To run the verification suite:
```powershell
python tests/quick_verification.py


6.SITE IS LIVE AT
Your site is live at https://santhanamn524-debug.github.io/cricket-analayis-/
Last deployed by @santhanamn524-debug santhanamn524-debug 1 minute ago

