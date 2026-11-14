/**
 * frontend/js/api.js
 * RR Intelligence Hub – Modern Asynchronous API Service
 */

const API_BASE = window.location.origin.includes(":5500")
  ? "http://localhost:8000/api"
  : "/api";

const API = {
  // 1. Health & Overview
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error("Health check failed");
    return res.json();
  },

  async getOverview() {
    const res = await fetch(`${API_BASE}/stats/overview`);
    if (!res.ok) throw new Error("Failed to load overview statistics");
    return res.json();
  },

  // 2. Player Intelligence
  async getPlayerOptions() {
    const res = await fetch(`${API_BASE}/players/options`);
    if (!res.ok) throw new Error("Failed to load player options");
    return res.json();
  },

  async getPlayers({ query = "", role = "All", minMatches = 0, sortBy = "total_runs", order = "desc", page = 1, pageSize = 15 }) {
    const params = new URLSearchParams({
      query,
      role,
      min_matches: minMatches,
      sort_by: sortBy,
      order,
      page,
      page_size: pageSize
    });
    const res = await fetch(`${API_BASE}/players?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to retrieve player database");
    return res.json();
  },

  async getPlayerDetail(playerId) {
    const res = await fetch(`${API_BASE}/players/${playerId}`);
    if (!res.ok) throw new Error(`Player ${playerId} not found`);
    return res.json();
  },

  // 3. Comparison
  async comparePlayers(playerIds) {
    const res = await fetch(`${API_BASE}/players/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ player_ids: playerIds })
    });
    if (!res.ok) throw new Error("Failed to compare players");
    return res.json();
  },

  // 4. Rankings
  async getBattingRankings(limit = 25, sortBy = "total_runs") {
    const res = await fetch(`${API_BASE}/rankings/batting?limit=${limit}&sort_by=${sortBy}`);
    if (!res.ok) throw new Error("Failed to load batting rankings");
    return res.json();
  },

  async getBowlingRankings(limit = 25, sortBy = "total_wickets") {
    const res = await fetch(`${API_BASE}/rankings/bowling?limit=${limit}&sort_by=${sortBy}`);
    if (!res.ok) throw new Error("Failed to load bowling rankings");
    return res.json();
  },

  async getOverallRankings(limit = 25) {
    const res = await fetch(`${API_BASE}/rankings/overall?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to load overall rankings");
    return res.json();
  },

  // 5. Predictions
  async predictBatting(payload) {
    const res = await fetch(`${API_BASE}/predict/batting`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Batting prediction request failed");
    return res.json();
  },

  async predictBowling(payload) {
    const res = await fetch(`${API_BASE}/predict/bowling`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Bowling prediction request failed");
    return res.json();
  },

  // 6. Pressure Engine
  async getPlayerPressureAnalysis(playerId, format = "All") {
    const res = await fetch(`${API_BASE}/pressure/player/${playerId}?format=${encodeURIComponent(format)}`);
    if (!res.ok) throw new Error(`Failed to load pressure analysis for player ${playerId}`);
    return res.json();
  },

  async getPressureAnalysis(limit = 20) {
    const res = await fetch(`${API_BASE}/pressure/analysis?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to load pressure intelligence");
    return res.json();
  },

  // 7. Suitability Engine
  async getRoleSuitability(role, limit = 15) {
    const res = await fetch(`${API_BASE}/suitability/${encodeURIComponent(role)}?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to load suitability for role: ${role}`);
    return res.json();
  },

  // 8. Smart Selector
  async getSelectorRecommendations(role = "All", limit = 10, minMatches = 5) {
    const res = await fetch(`${API_BASE}/selector/recommendations?role=${encodeURIComponent(role)}&limit=${limit}&min_matches=${minMatches}`);
    if (!res.ok) throw new Error("Failed to load selector recommendations");
    return res.json();
  },

  // 9. Dataset Management
  async getDatasetsStatus() {
    const res = await fetch(`${API_BASE}/datasets/status`);
    if (!res.ok) throw new Error("Failed to load datasets status");
    return res.json();
  },

  // 10. ML Model Status & Training Controller
  async getModelsStatus() {
    const res = await fetch(`${API_BASE}/models/status`);
    if (!res.ok) throw new Error("Failed to load ML models status");
    return res.json();
  },

  async triggerTraining(payload) {
    const res = await fetch(`${API_BASE}/train`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Training trigger failed");
    }
    return res.json();
  },

  async getTrainingStatus() {
    const res = await fetch(`${API_BASE}/train/status`);
    if (!res.ok) throw new Error("Failed to fetch training status");
    return res.json();
  },

  async getTrainingHistory() {
    const res = await fetch(`${API_BASE}/train/history`);
    if (!res.ok) throw new Error("Failed to fetch training history");
    return res.json();
  }
};
