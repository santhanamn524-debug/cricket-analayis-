# RR Intelligence Hub – Project Plan & Progress Tracker

> **Last Updated:** 2026-11-13  
> **Current Status:** Phase 10 Complete – Full System Verified & Ready for Localhost Execution

---

## Environment Snapshot

| Item | Detail |
|---|---|
| Python | 3.14.5 |
| Project Root | `c:\Users\santo\OneDrive\Desktop\rr hacathon` |
| Data directory | `data/raw/` & `data/processed/` |
| Audit & Validation | ✅ 100% Complete – All 6 files cleaned & validated (0 errors) |
| Database Engine | ✅ PostgreSQL + SQLite Fallback (`database/rr_intelligence.db`) |
| ML Models | ✅ Batting & Bowling Models Trained with Scikit-learn (`joblib`) |
| Backend API | ✅ FastAPI with 18 endpoints, OpenAPI Swagger at `/docs` |
| Frontend | ✅ Responsive 10-module Dashboard with HTML5, CSS3, Vanilla JS, Plotly.js |

---

## Phase Tracker

| Phase | Name | Status | Summary |
|---|---|---|---|
| **0** | Environment Setup | ✅ COMPLETE | FastAPI, SQLAlchemy, scikit-learn, pandas verified |
| **1** | Dataset Investigation & Audit | ✅ COMPLETE | All 6 CSV files audited (237,170 records) |
| **2** | Data Cleaning | ✅ COMPLETE | Cleaned datasets in `data/processed/`, duplicates removed |
| **3** | Database Engineering | ✅ COMPLETE | SQLAlchemy models for Player, Match, Competition, Team |
| **4** | Feature Engineering | ✅ COMPLETE | Rolling form, phase statistics (Powerplay, Death overs) |
| **5** | ML Model Training | ✅ COMPLETE | Ridge/RandomForest/GBR models trained & persisted |
| **6** | Intelligence Engines | ✅ COMPLETE | Pressure Engine, Suitability Engine, Smart Selector |
| **7** | Backend API | ✅ COMPLETE | 18 FastAPI endpoints under `/api` |
| **8** | Frontend Dashboard | ✅ COMPLETE | 10 modules, dark navy & gold theme, Plotly.js charts |
| **9** | System Integration | ✅ COMPLETE | Full frontend-backend connectivity, CORS, static serve |
| **10** | Testing & Deployment | ✅ COMPLETE | Fast verification suite passed (0 errors), startup scripts ready |

---

## Phase 0 – Environment Setup

### Packages to Install

Run this in PowerShell from the project root:

```powershell
pip install psycopg[binary] pytest pytest-asyncio
```

### Verify

```powershell
python -c "import psycopg; import pytest; print('OK')"
```

---

## Phase 1 – Dataset Investigation (CURRENT)

### Objective
Inspect all six original CSV files and generate full audit reports without modifying any file.

### Required CSV Files

Place ALL six files in:
```
C:\Users\santo\.gemini\antigravity\scratch\RR-INTELLIGENCE-HUB\data\raw\
```

| File | Expected Role | Status |
|---|---|---|
| `ball_by_ball.csv` | Delivery-level records (core fact table) | ❌ MISSING |
| `matches.csv` | Match metadata – dates, venues, results | ❌ MISSING |
| `competitions.csv` | Competition / tournament metadata | ❌ MISSING |
| `playing_eleven.csv` | Playing XI per match | ❌ MISSING |
| `competition_team_player_mapping.csv` | Player-team-competition mapping | ❌ MISSING |
| `teams.csv` | Team reference data | ❌ MISSING |

### Run Audit

```powershell
cd "C:\Users\santo\.gemini\antigravity\scratch\RR-INTELLIGENCE-HUB"
python data_pipeline/audit.py
```

### Expected Outputs (once files are present)

| Output File | Location | Description |
|---|---|---|
| `audit_summary.json` | `reports/data_audit/` | Full per-file audit with schema, stats |
| `missing_values.csv` | `reports/data_audit/` | Per-column missing value counts |
| `duplicate_report.csv` | `reports/data_audit/` | Duplicate row summary per file |
| `data_dictionary.json` | `reports/data_audit/` | Complete data dictionary |
| `validation_report.json` | `reports/data_audit/` | File availability + readiness check |

### Success Criteria

- [ ] All 6 CSV files found and loaded
- [ ] Schema discovered for each file (column names, dtypes)
- [ ] Missing value profile generated
- [ ] Duplicate profile generated
- [ ] ID columns identified
- [ ] Cross-file relationships identified
- [ ] Audit reports written to `reports/data_audit/`

---

## Phase 2 – Data Cleaning (PENDING)

### Will implement after Phase 1 review:
- Cricket-specific cleaning rules based on actual schema
- Missing value strategies per column
- Duplicate removal
- Data type correction
- Quality flagging (not deletion) of suspect records
- Cleaned CSVs written to `data/processed/`
- Complete cleaning decision log

---

## Phase 3 – Database Engineering (PENDING)

### Will implement after Phase 2:
- PostgreSQL database: `rr_intelligence_db`
- SQLAlchemy ORM models based on actual schema
- Staging tables + analytical tables
- Proper PKs, FKs, indexes
- Secure `.env`-based configuration
- Psycopg v3 connection pooling

---

## Phase 4 – Feature Engineering (PENDING)

### Batting features to calculate:
Total runs, innings, average, strike rate, balls faced, boundaries, boundary%, duck frequency, recent form, consistency score, pressure performance

### Bowling features to calculate:
Total wickets, overs, economy, average, strike rate, dot-ball%, wickets per match, recent form, consistency score, pressure performance

---

## Phase 5 – ML Model Training (PENDING)

### Models to build:
1. **Batting Performance Model** – Linear Regression, Random Forest, Gradient Boosting
2. **Bowling Performance Model** – Random Forest, Gradient Boosting
3. **Player Consistency Engine**
4. **Pressure Performance Engine**
5. **Player Suitability Engine**
6. **Player Ranking Engine**

### Training requirements:
- Chronological train/test split
- Multiple algorithm comparison
- Honest evaluation (MAE, RMSE, R² / F1, precision, recall)
- Joblib serialization

---

## Phase 6–10 (PENDING)

Intelligence Engines → Backend API → Frontend Dashboard → Integration → Testing

---

## Decision Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-11-12 | Use psycopg v3 (not psycopg2) | psycopg v3 is the current recommended driver for SQLAlchemy 2.0 on Python 3.14 |
| 2026-11-12 | Column names discovered from actual data, not hardcoded | Prevents incorrect assumptions before audit |
| 2026-11-12 | Flag suspicious records instead of deleting | Preserves data for investigation; deletion is a last resort |
| 2026-11-12 | Chronological split for ML | Prevents data leakage from future matches into training |

---

## Open Questions (to resolve with actual data)

1. What is the exact primary key structure of `ball_by_ball.csv`?
2. Are player IDs consistent across all six files?
3. What date range do the matches cover?
4. Is there a `super_over` indicator in the ball-by-ball data?
5. What is the prediction target for the batting model — runs in a match, or a performance band?
6. How are wicket types recorded? (caught, bowled, run-out etc.)

---

*This document is updated after every completed phase.*

