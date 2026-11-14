/**
 * frontend/js/app.js
 * RR Intelligence Hub – Modern Application Controller & Pressure Percentage Analyzer
 */

document.addEventListener("DOMContentLoaded", () => {
  initApp();
});

let currentTab = "executive";
let allPlayersCache = []; // Global cache of {player_id, name, primary_role, total_runs, total_wickets}

const TAB_TITLES = {
  "executive": "Executive Command Centre",
  "players": "Player Intelligence Database",
  "selector": "RR Smart Selector – Recruitment Engine",
  "batting": "Official Batter Rankings",
  "bowling": "Official Bowler Rankings",
  "comparison": "Player Head-to-Head Comparison",
  "pressure": "Pressure Performance Percentage Analyzer",
  "training-monitor": "ML Training Controller & Monitor",
  "model-eval": "Model Evaluation & Prediction Sandbox"
};

async function initApp() {
  setupNavigation();
  setupEventListeners();
  checkSystemHealth();
  
  // 1. Pre-load all player options for dropdowns
  await preloadPlayerOptions();

  // 2. Load the initial Command Centre view
  loadExecutiveDashboard();
}

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------
function setupNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  currentTab = tabId;
  
  document.querySelectorAll(".nav-tab").forEach(t => {
    t.classList.toggle("active", t.dataset.tab === tabId);
  });
  
  document.querySelectorAll(".tab-pane").forEach(p => {
    p.classList.toggle("active", p.id === `tab-${tabId}`);
  });

  const topTitle = document.getElementById("active-tab-title");
  if (topTitle) {
    topTitle.textContent = TAB_TITLES[tabId] || "RR Intelligence Hub";
  }

  switch (tabId) {
    case "executive":
      loadExecutiveDashboard();
      break;
    case "players":
      loadPlayersList();
      break;
    case "selector":
      loadSmartSelector();
      break;
    case "batting":
      loadBattingRankings();
      break;
    case "bowling":
      loadBowlingRankings();
      break;
    case "comparison":
      renderComparisonWorkspace();
      break;
    case "pressure":
      loadPressureSection();
      break;
    case "training-monitor":
      loadTrainingMonitor();
      break;
    case "model-eval":
      loadModelEvaluation();
      break;
  }
}

// ---------------------------------------------------------------------------
// Preload Player Options for Dropdowns
// ---------------------------------------------------------------------------
async function preloadPlayerOptions() {
  try {
    allPlayersCache = await API.getPlayerOptions();
    populateComparisonDropdowns();
    populatePressurePlayerDropdown();
  } catch (err) {
    console.error("Failed to preload player options:", err);
  }
}

function populateComparisonDropdowns(filterRole = "All") {
  const select1 = document.getElementById("compare-select-1");
  const select2 = document.getElementById("compare-select-2");
  const select3 = document.getElementById("compare-select-3");
  const countBadge = document.getElementById("compare-available-count");

  if (!select1 || !select2) return;

  let filtered = allPlayersCache;
  if (filterRole && filterRole !== "All") {
    filtered = allPlayersCache.filter(p => p.primary_role === filterRole);
  }

  if (countBadge) {
    countBadge.textContent = `${filtered.length} Players Available`;
  }

  const buildOptions = (selectedId, includeNone = false) => {
    let opts = includeNone ? `<option value="">None (Compare 2 Players)</option>` : "";
    filtered.forEach(p => {
      const isSel = p.player_id === selectedId ? "selected" : "";
      opts += `<option value="${p.player_id}" ${isSel}>${escapeHtml(p.name)} (${p.primary_role} • ${p.total_runs}r • ${p.total_wickets}w)</option>`;
    });
    return opts;
  };

  const defaultP1 = filtered.find(p => p.name.includes("Kohli"))?.player_id || filtered[0]?.player_id || 47;
  const defaultP2 = filtered.find(p => p.name.includes("Suryakumar"))?.player_id || filtered[1]?.player_id || 8;

  select1.innerHTML = buildOptions(defaultP1, false);
  select2.innerHTML = buildOptions(defaultP2, false);
  if (select3) {
    select3.innerHTML = buildOptions(null, true);
  }
}

function populatePressurePlayerDropdown(filterRole = "All") {
  const select = document.getElementById("analyzer-player-select");
  const countBadge = document.getElementById("analyzer-available-count");
  if (!select) return;

  let filtered = allPlayersCache;
  if (filterRole && filterRole !== "All") {
    filtered = allPlayersCache.filter(p => p.primary_role === filterRole);
  }

  if (countBadge) {
    countBadge.textContent = `${filtered.length} Players Available`;
  }

  let opts = "";
  // Find Virat Kohli or first player
  const defaultId = filtered.find(p => p.name.includes("Kohli"))?.player_id || filtered[0]?.player_id || 47;

  filtered.forEach(p => {
    const isSel = p.player_id === defaultId ? "selected" : "";
    opts += `<option value="${p.player_id}" ${isSel}>${escapeHtml(p.name)} (${p.primary_role} • ${p.total_runs}r • ${p.total_wickets}w)</option>`;
  });

  select.innerHTML = opts;
}

// ---------------------------------------------------------------------------
// 1. Executive Dashboard (Command Centre)
// ---------------------------------------------------------------------------
async function loadExecutiveDashboard() {
  try {
    const stats = await API.getOverview();
    document.getElementById("kpi-players").textContent = stats.total_players.toLocaleString();
    document.getElementById("kpi-matches").textContent = stats.total_matches.toLocaleString();
    document.getElementById("kpi-competitions").textContent = stats.total_competitions.toLocaleString();
    document.getElementById("kpi-teams").textContent = stats.total_teams.toLocaleString();
    
    if (stats.highlights) {
      document.getElementById("highlight-batsman-name").textContent = stats.highlights.top_run_scorer.name;
      document.getElementById("highlight-batsman-runs").textContent = `${stats.highlights.top_run_scorer.runs} runs (Avg ${stats.highlights.top_run_scorer.avg})`;
      
      document.getElementById("highlight-bowler-name").textContent = stats.highlights.top_wicket_taker.name;
      document.getElementById("highlight-bowler-wkts").textContent = `${stats.highlights.top_wicket_taker.wickets} wickets (Econ ${stats.highlights.top_wicket_taker.economy})`;
      
      document.getElementById("highlight-clutch-name").textContent = stats.highlights.top_clutch_player.name;
      document.getElementById("highlight-clutch-score").textContent = `Score: ${stats.highlights.top_clutch_player.pressure_score} (${stats.highlights.top_clutch_player.clutch_rating})`;
    }

    const overall = await API.getOverallRankings(10);
    const tbody = document.getElementById("exec-rankings-tbody");
    tbody.innerHTML = "";
    overall.rankings.forEach(p => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="rank-badge rank-${p.rank <= 3 ? p.rank : 'other'}">${p.rank}</span></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td><span class="pill pill-normal">${escapeHtml(p.primary_role)}</span></td>
        <td>${p.matches_played}</td>
        <td>${p.total_runs}</td>
        <td>${p.batting_avg}</td>
        <td>${p.strike_rate}</td>
        <td>${p.total_wickets}</td>
        <td>${p.bowling_economy}</td>
        <td><span class="pill pill-${p.clutch_rating.toLowerCase()}">${p.clutch_rating} (${p.pressure_score})</span></td>
        <td><strong style="color: var(--gold);">${p.overall_impact_score}</strong></td>
      `;
      tbody.appendChild(tr);
    });

    renderExecutiveChart(overall.rankings);
  } catch (err) {
    console.error("Executive Dashboard Error:", err);
  }
}

function renderExecutiveChart(players) {
  const chartDiv = document.getElementById("exec-impact-chart");
  if (!chartDiv || typeof Plotly === "undefined") return;

  const names = players.map(p => p.name);
  const impactScores = players.map(p => p.overall_impact_score);
  const pressureScores = players.map(p => p.pressure_score);

  const trace1 = { x: names, y: impactScores, name: "Overall Impact", type: "bar", marker: { color: "#2563eb" } };
  const trace2 = { x: names, y: pressureScores, name: "Pressure Rating", type: "bar", marker: { color: "#f59e0b" } };

  const layout = {
    barmode: "group",
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 20, r: 20, l: 40, b: 80 },
    legend: { orientation: "h", y: 1.15 },
    xaxis: { tickangle: -25 },
    yaxis: { gridcolor: "#1e293b" }
  };

  Plotly.newPlot(chartDiv, [trace1, trace2], layout, { responsive: true, displayModeBar: false });
}

// ---------------------------------------------------------------------------
// 2. Player Database
// ---------------------------------------------------------------------------
let playerPage = 1;
async function loadPlayersList() {
  const query = document.getElementById("player-search-input")?.value || "";
  const role = document.getElementById("player-role-filter")?.value || "All";
  const sortBy = document.getElementById("player-sort-filter")?.value || "total_runs";

  try {
    const data = await API.getPlayers({
      query,
      role,
      sortBy,
      page: playerPage,
      pageSize: 15
    });

    document.getElementById("player-count-label").textContent = `Showing ${data.players.length} of ${data.total_records} players`;
    document.getElementById("player-page-info").textContent = `Page ${data.page} of ${data.total_pages}`;

    const tbody = document.getElementById("players-table-tbody");
    tbody.innerHTML = "";

    data.players.forEach(p => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td><span class="pill pill-normal">${escapeHtml(p.primary_role)}</span></td>
        <td>${p.matches_played}</td>
        <td>${p.total_runs}</td>
        <td>${p.batting_avg}</td>
        <td>${p.strike_rate}</td>
        <td>${p.total_wickets}</td>
        <td>${p.bowling_economy}</td>
        <td>${p.consistency_score}</td>
        <td><span class="pill pill-${p.clutch_rating.toLowerCase()}">${p.clutch_rating} (${p.pressure_score})</span></td>
        <td>
          <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="viewPlayerModal(${p.player_id})">Profile</button>
          <button class="btn btn-gold" style="padding: 4px 10px; font-size: 11px;" onclick="selectForComparison(${p.player_id})">+ Compare</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById("btn-prev-page").disabled = (data.page <= 1);
    document.getElementById("btn-next-page").disabled = (data.page >= data.total_pages);
  } catch (err) {
    console.error("Player Database Error:", err);
  }
}

// ---------------------------------------------------------------------------
// Player Profile Modal
// ---------------------------------------------------------------------------
async function viewPlayerModal(playerId) {
  try {
    const p = await API.getPlayerDetail(playerId);
    document.getElementById("modal-player-name").textContent = p.name;
    document.getElementById("modal-player-role").textContent = `${p.primary_role} • ${p.batting_style} • ${p.bowling_style}`;
    
    document.getElementById("modal-runs").textContent = p.total_runs;
    document.getElementById("modal-avg").textContent = p.batting_avg;
    document.getElementById("modal-sr").textContent = p.strike_rate;
    document.getElementById("modal-hi").textContent = p.highest_score;
    document.getElementById("modal-fifties").textContent = `${p.fifties} / ${p.hundreds}`;
    
    document.getElementById("modal-wkts").textContent = p.total_wickets;
    document.getElementById("modal-econ").textContent = p.bowling_economy;
    document.getElementById("modal-bw-avg").textContent = p.bowling_avg;
    document.getElementById("modal-overs").textContent = p.overs_bowled;
    
    document.getElementById("modal-consistency").textContent = p.consistency_score;
    document.getElementById("modal-pressure").textContent = `${p.pressure_score} (${p.clutch_rating})`;
    document.getElementById("modal-impact").textContent = p.overall_impact_score;

    const strengthsUl = document.getElementById("modal-strengths");
    strengthsUl.innerHTML = "";
    p.strengths.forEach(s => {
      const li = document.createElement("li");
      li.textContent = s;
      li.style.marginBottom = "4px";
      strengthsUl.appendChild(li);
    });

    renderRadarChart(p.radar_metrics, p.name);
    document.getElementById("player-modal").classList.add("active");
  } catch (err) {
    alert("Could not load player profile: " + err.message);
  }
}

function renderRadarChart(metrics, playerName) {
  const chartDiv = document.getElementById("modal-radar-chart");
  if (!chartDiv || typeof Plotly === "undefined") return;

  const categories = Object.keys(metrics);
  const values = Object.values(metrics);

  const data = [{
    type: "scatterpolar",
    r: [...values, values[0]],
    theta: [...categories, categories[0]],
    fill: "toself",
    fillcolor: "rgba(37, 99, 235, 0.3)",
    line: { color: "#f59e0b", width: 2 },
    name: playerName
  }];

  const layout = {
    polar: {
      radialaxis: { visible: true, range: [0, 100], color: "#64748b" },
      angularaxis: { color: "#94a3b8" },
      bgcolor: "transparent"
    },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    margin: { t: 30, r: 30, b: 30, l: 30 },
    showlegend: false
  };

  Plotly.newPlot(chartDiv, data, layout, { responsive: true, displayModeBar: false });
}

// ---------------------------------------------------------------------------
// 3. RR Smart Selector
// ---------------------------------------------------------------------------
async function loadSmartSelector() {
  const role = document.getElementById("selector-role-select")?.value || "Finisher";
  const minMatches = parseInt(document.getElementById("selector-min-matches")?.value || "5", 10);

  try {
    const data = await API.getSelectorRecommendations(role, 8, minMatches);
    const container = document.getElementById("selector-cards-container");
    container.innerHTML = "";

    data.recommendations.forEach(c => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.borderLeft = "4px solid var(--gold)";
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
          <div>
            <span class="rank-badge rank-${c.rank <= 3 ? c.rank : 'other'}" style="margin-right: 8px;">#${c.rank}</span>
            <strong style="font-size: 17px;">${escapeHtml(c.name)}</strong>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">${escapeHtml(c.primary_role)} • ${escapeHtml(c.batting_style)}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 22px; font-weight: 700; color: var(--gold);">${c.composite_score}</div>
            <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">RR Match Index</div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; background: rgba(0,0,0,0.2); padding: 10px; border-radius: var(--radius-sm); margin-bottom: 12px; font-size: 12px;">
          <div><span style="color:var(--text-muted);">Runs:</span> <strong>${c.total_runs}</strong></div>
          <div><span style="color:var(--text-muted);">SR:</span> <strong>${c.strike_rate}</strong></div>
          <div><span style="color:var(--text-muted);">Wkts:</span> <strong>${c.total_wickets}</strong></div>
          <div><span style="color:var(--text-muted);">Pressure:</span> <strong style="color:var(--gold);">${c.pressure_score}</strong></div>
        </div>

        <div style="margin-bottom: 12px;">
          <div style="font-size: 11px; font-weight: 600; color: var(--gold); text-transform: uppercase; margin-bottom: 4px;">Tactical Recruitment Rationale:</div>
          <ul style="padding-left: 18px; font-size: 12px; color: #cbd5e1; line-height: 1.5;">
            ${c.recommendation_reasons.map(r => `<li>${escapeHtml(r)}</li>`).join("")}
          </ul>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 10px;">
          <span style="font-size: 11px; color: var(--text-muted);">${escapeHtml(c.tactical_fit)}</span>
          <div>
            <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="viewPlayerModal(${c.player_id})">Profile</button>
            <button class="btn btn-gold" style="padding: 4px 10px; font-size: 11px;" onclick="selectForComparison(${c.player_id})">+ Compare</button>
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Smart Selector Error:", err);
  }
}

// ---------------------------------------------------------------------------
// 4. Batter Rankings
// ---------------------------------------------------------------------------
async function loadBattingRankings() {
  const sortBy = document.getElementById("batting-sort-select")?.value || "total_runs";
  try {
    const data = await API.getBattingRankings(30, sortBy);
    const tbody = document.getElementById("batting-rankings-tbody");
    tbody.innerHTML = "";

    data.rankings.forEach(p => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="rank-badge rank-${p.rank <= 3 ? p.rank : 'other'}">${p.rank}</span></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td><span class="pill pill-normal">${escapeHtml(p.primary_role)}</span></td>
        <td>${p.matches_played}</td>
        <td>${p.innings_batted}</td>
        <td><strong>${p.total_runs}</strong></td>
        <td>${p.batting_avg}</td>
        <td>${p.strike_rate}</td>
        <td>${p.highest_score}</td>
        <td>${p.fifties} / ${p.hundreds}</td>
        <td>${p.fours} / ${p.sixes}</td>
        <td>${p.consistency_score}</td>
        <td><button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="viewPlayerModal(${p.player_id})">View</button></td>
      `;
      tbody.appendChild(tr);
    });

    renderBattingScatter(data.rankings);
  } catch (err) {
    console.error("Batting Rankings Error:", err);
  }
}

function renderBattingScatter(rankings) {
  const chartDiv = document.getElementById("batting-scatter-chart");
  if (!chartDiv || typeof Plotly === "undefined") return;

  const trace = {
    x: rankings.map(p => p.batting_avg),
    y: rankings.map(p => p.strike_rate),
    text: rankings.map(p => `${p.name} (${p.total_runs} runs)`),
    mode: "markers+text",
    textposition: "top center",
    textfont: { size: 9, color: "#94a3b8" },
    marker: {
      size: rankings.map(p => Math.max(10, Math.sqrt(p.total_runs) * 0.8)),
      color: rankings.map(p => p.strike_rate),
      colorscale: "Viridis",
      showscale: true,
      colorbar: { title: "Strike Rate" }
    }
  };

  const layout = {
    title: "Batting Average vs Strike Rate Efficiency",
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 40, r: 20, l: 40, b: 50 },
    xaxis: { title: "Batting Average", gridcolor: "#1e293b" },
    yaxis: { title: "Strike Rate", gridcolor: "#1e293b" }
  };

  Plotly.newPlot(chartDiv, [trace], layout, { responsive: true, displayModeBar: false });
}

// ---------------------------------------------------------------------------
// 5. Bowler Rankings
// ---------------------------------------------------------------------------
async function loadBowlingRankings() {
  const sortBy = document.getElementById("bowling-sort-select")?.value || "total_wickets";
  try {
    const data = await API.getBowlingRankings(30, sortBy);
    const tbody = document.getElementById("bowling-rankings-tbody");
    tbody.innerHTML = "";

    data.rankings.forEach(p => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="rank-badge rank-${p.rank <= 3 ? p.rank : 'other'}">${p.rank}</span></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td><span class="pill pill-normal">${escapeHtml(p.bowling_style || 'Pace')}</span></td>
        <td>${p.matches_played}</td>
        <td>${p.overs_bowled}</td>
        <td><strong>${p.total_wickets}</strong></td>
        <td>${p.bowling_economy}</td>
        <td>${p.bowling_avg}</td>
        <td>${p.bowling_sr}</td>
        <td>${p.four_wkt_hauls} / ${p.five_wkt_hauls}</td>
        <td>${p.consistency_score}</td>
        <td><button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="viewPlayerModal(${p.player_id})">View</button></td>
      `;
      tbody.appendChild(tr);
    });

    renderBowlingScatter(data.rankings);
  } catch (err) {
    console.error("Bowling Rankings Error:", err);
  }
}

function renderBowlingScatter(rankings) {
  const chartDiv = document.getElementById("bowling-scatter-chart");
  if (!chartDiv || typeof Plotly === "undefined") return;

  const trace = {
    x: rankings.map(p => p.bowling_economy),
    y: rankings.map(p => p.bowling_sr),
    text: rankings.map(p => `${p.name} (${p.total_wickets} wkts)`),
    mode: "markers+text",
    textposition: "top center",
    textfont: { size: 9, color: "#94a3b8" },
    marker: {
      size: rankings.map(p => Math.max(10, Math.sqrt(p.total_wickets) * 3)),
      color: rankings.map(p => p.total_wickets),
      colorscale: "Magma",
      showscale: true,
      colorbar: { title: "Wickets" }
    }
  };

  const layout = {
    title: "Bowling Economy vs Strike Rate (Lower is Better)",
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 40, r: 20, l: 40, b: 50 },
    xaxis: { title: "Economy Rate", gridcolor: "#1e293b" },
    yaxis: { title: "Balls / Wicket (Strike Rate)", gridcolor: "#1e293b" }
  };

  Plotly.newPlot(chartDiv, [trace], layout, { responsive: true, displayModeBar: false });
}

// ---------------------------------------------------------------------------
// 6. Player Comparison
// ---------------------------------------------------------------------------
function selectForComparison(playerId) {
  const select1 = document.getElementById("compare-select-1");
  const select2 = document.getElementById("compare-select-2");
  
  if (select1 && select2) {
    if (!select1.value || select1.value == playerId) {
      select1.value = playerId;
    } else {
      select2.value = playerId;
    }
  }
  switchTab("comparison");
  renderComparisonWorkspace();
}

async function renderComparisonWorkspace() {
  const select1 = document.getElementById("compare-select-1");
  const select2 = document.getElementById("compare-select-2");
  const select3 = document.getElementById("compare-select-3");
  const statusText = document.getElementById("compare-status-text");

  if (!select1.children.length || select1.options[0]?.value === "") {
    if (allPlayersCache.length === 0) {
      await preloadPlayerOptions();
    } else {
      populateComparisonDropdowns();
    }
  }

  const p1 = parseInt(select1.value, 10);
  const p2 = parseInt(select2.value, 10);
  const p3 = select3?.value ? parseInt(select3.value, 10) : null;

  const playerIds = [p1, p2];
  if (p3 && !isNaN(p3) && p3 !== p1 && p3 !== p2) {
    playerIds.push(p3);
  }

  const validIds = playerIds.filter(id => !isNaN(id) && id > 0);
  if (validIds.length < 2) {
    if (statusText) {
      statusText.textContent = "Please select at least 2 distinct players from the dropdowns above.";
      statusText.style.color = "var(--warning)";
    }
    return;
  }

  if (statusText) {
    statusText.textContent = `Analyzing ${validIds.length} players from real database records...`;
    statusText.style.color = "var(--gold)";
  }

  try {
    const data = await API.comparePlayers(validIds);
    const players = data.players;

    if (statusText) {
      statusText.textContent = `Comparing ${players.map(p => p.name).join(" vs ")} across all key metrics.`;
      statusText.style.color = "var(--success)";
    }

    renderComparisonCards(players);

    if (data.insights) {
      renderComparisonInsights(data.insights, players);
    }

    renderComparisonTable(players);
    renderComparisonCharts(players);

  } catch (err) {
    console.error("Comparison Error:", err);
    if (statusText) {
      statusText.textContent = "Error loading player comparison: " + err.message;
      statusText.style.color = "var(--danger)";
    }
  }
}

function renderComparisonCards(players) {
  const container = document.getElementById("comparison-cards-row");
  container.innerHTML = "";

  const colors = ["var(--royal-blue-light)", "var(--gold)", "var(--success)"];

  players.forEach((p, idx) => {
    const card = document.createElement("div");
    card.className = "card";
    card.style.borderLeft = `4px solid ${colors[idx % colors.length]}`;
    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
        <div>
          <span class="pill pill-normal" style="margin-bottom: 4px;">Player ${idx + 1}</span>
          <h3 style="font-size: 19px; font-weight: 700; margin-top: 2px;">${escapeHtml(p.name)}</h3>
          <div style="font-size: 12px; color: var(--gold);">${escapeHtml(p.primary_role)} • ${escapeHtml(p.batting_style)}</div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 24px; font-weight: 800; color: ${colors[idx % colors.length]};">${p.overall_impact_score}</div>
          <div style="font-size: 10px; color: var(--text-muted); text-transform: uppercase;">Impact Score</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; background: rgba(0,0,0,0.25); padding: 12px; border-radius: var(--radius-sm); margin-bottom: 14px; font-size: 12px;">
        <div><span style="color:var(--text-muted);">Matches:</span> <strong>${p.matches_played}</strong></div>
        <div><span style="color:var(--text-muted);">Total Runs:</span> <strong>${p.total_runs}</strong></div>
        <div><span style="color:var(--text-muted);">Batting Avg:</span> <strong>${p.batting_avg}</strong></div>
        <div><span style="color:var(--text-muted);">Strike Rate:</span> <strong>${p.strike_rate}</strong></div>
        <div><span style="color:var(--text-muted);">Total Wickets:</span> <strong>${p.total_wickets}</strong></div>
        <div><span style="color:var(--text-muted);">Economy:</span> <strong>${p.bowling_economy}</strong></div>
        <div><span style="color:var(--text-muted);">Consistency:</span> <strong>${p.consistency_score}</strong></div>
        <div><span style="color:var(--text-muted);">Pressure:</span> <strong style="color:var(--gold);">${p.pressure_score}</strong> <small>(${p.clutch_rating})</small></div>
      </div>

      <div style="font-size: 11px; color: #cbd5e1; line-height: 1.5; border-top: 1px solid var(--border-color); padding-top: 10px;">
        <span style="color:var(--gold); font-weight:600;">Key Strength:</span> ${p.strengths[0] || 'Reliable squad contributor'}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderComparisonInsights(insights, players) {
  const box = document.getElementById("comparison-insights-box");
  const content = document.getElementById("comparison-insights-content");
  box.style.display = "block";
  content.innerHTML = "";

  const items = [
    { title: "🏏 Batting Leader", data: insights.batting_leader, color: "var(--royal-blue-light)" },
    { title: "🎯 Bowling Leader", data: insights.bowling_leader, color: "var(--gold)" },
    { title: "⚡ Pressure / Clutch Leader", data: insights.clutch_leader, color: "var(--success)" },
    { title: "🛡️ Consistency Benchmark", data: insights.consistency_leader, color: "#a855f7" },
    { title: "🏆 RR Tactical Recommendation", data: insights.overall_recommendation, color: "var(--gold-light)" },
  ];

  items.forEach(item => {
    if (!item.data) return;
    const div = document.createElement("div");
    div.style.background = "rgba(0,0,0,0.2)";
    div.style.padding = "12px 14px";
    div.style.borderRadius = "var(--radius-sm)";
    div.style.borderLeft = `3px solid ${item.color}`;
    div.innerHTML = `
      <div style="font-size: 11px; text-transform: uppercase; color: ${item.color}; font-weight: 700; margin-bottom: 4px;">${item.title}</div>
      <div style="font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 4px;">${escapeHtml(item.data.name)}</div>
      <div style="font-size: 12px; color: var(--text-muted); line-height: 1.4;">${escapeHtml(item.data.reason)}</div>
    `;
    content.appendChild(div);
  });
}

function renderComparisonTable(players) {
  const card = document.getElementById("comparison-table-card");
  const thead = document.getElementById("comp-table-thead");
  const tbody = document.getElementById("comp-table-tbody");
  card.style.display = "block";

  thead.innerHTML = `
    <tr>
      <th>Metric Attribute</th>
      ${players.map(p => `<th>${escapeHtml(p.name)}<br><small style="color:var(--text-muted); font-weight:normal;">${p.primary_role}</small></th>`).join("")}
    </tr>
  `;

  const rows = [
    { label: "Matches Played", key: "matches_played" },
    { label: "Total Runs", key: "total_runs", highlight: true },
    { label: "Batting Average", key: "batting_avg" },
    { label: "Strike Rate", key: "strike_rate", highlight: true },
    { label: "Highest Score", key: "highest_score" },
    { label: "50s / 100s", custom: p => `${p.fifties} / ${p.hundreds}` },
    { label: "Total Wickets", key: "total_wickets", highlight: true },
    { label: "Bowling Economy", key: "bowling_economy" },
    { label: "Bowling Average", key: "bowling_avg" },
    { label: "Consistency Score", key: "consistency_score" },
    { label: "Pressure Score", key: "pressure_score", custom: p => `<span class="pill pill-gold">${p.pressure_score} (${p.clutch_rating})</span>` },
    { label: "Overall Impact Score", key: "overall_impact_score", custom: p => `<strong style="color:var(--gold); font-size:15px;">${p.overall_impact_score}</strong>` },
  ];

  tbody.innerHTML = "";
  rows.forEach(r => {
    const tr = document.createElement("tr");
    let cells = `<td><strong>${r.label}</strong></td>`;
    players.forEach(p => {
      let val = r.custom ? r.custom(p) : p[r.key];
      if (r.highlight) val = `<strong>${val}</strong>`;
      cells += `<td>${val}</td>`;
    });
    tr.innerHTML = cells;
    tbody.appendChild(tr);
  });
}

function renderComparisonCharts(players) {
  const chartsGrid = document.getElementById("comparison-charts-grid");
  chartsGrid.style.display = "grid";

  if (typeof Plotly === "undefined") return;

  const names = players.map(p => p.name);
  const colors = ["#2563eb", "#f59e0b", "#10b981"];

  // 1. Batting
  const batTraceRuns = { x: names, y: players.map(p => p.total_runs), name: "Runs", type: "bar", marker: { color: "#2563eb" } };
  const batTraceAvg = { x: names, y: players.map(p => p.batting_avg), name: "Average", type: "bar", marker: { color: "#3b82f6" } };
  const batTraceSR = { x: names, y: players.map(p => p.strike_rate), name: "Strike Rate", type: "bar", marker: { color: "#f59e0b" } };

  Plotly.newPlot("comp-chart-batting", [batTraceRuns, batTraceAvg, batTraceSR], {
    barmode: "group",
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 20, r: 20, l: 30, b: 60 },
    legend: { orientation: "h", y: 1.15 },
    yaxis: { gridcolor: "#1e293b" }
  }, { responsive: true, displayModeBar: false });

  // 2. Bowling
  const bowlTraceWkts = { x: names, y: players.map(p => p.total_wickets), name: "Wickets", type: "bar", marker: { color: "#10b981" } };
  const bowlTraceEcon = { x: names, y: players.map(p => p.bowling_economy), name: "Economy", type: "bar", marker: { color: "#ec4899" } };

  Plotly.newPlot("comp-chart-bowling", [bowlTraceWkts, bowlTraceEcon], {
    barmode: "group",
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 20, r: 20, l: 30, b: 60 },
    legend: { orientation: "h", y: 1.15 },
    yaxis: { gridcolor: "#1e293b" }
  }, { responsive: true, displayModeBar: false });

  // 3. Multi-Player Radar
  const radarTraces = players.map((p, idx) => {
    const cats = Object.keys(p.radar_metrics);
    const vals = Object.values(p.radar_metrics);
    return {
      type: "scatterpolar",
      r: [...vals, vals[0]],
      theta: [...cats, cats[0]],
      fill: "toself",
      name: p.name,
      line: { color: colors[idx % colors.length] }
    };
  });

  Plotly.newPlot("comp-chart-radar", radarTraces, {
    polar: {
      radialaxis: { visible: true, range: [0, 100], color: "#64748b" },
      angularaxis: { color: "#94a3b8" },
      bgcolor: "transparent"
    },
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    margin: { t: 25, r: 25, b: 25, l: 25 },
    legend: { orientation: "h", y: -0.15 }
  }, { responsive: true, displayModeBar: false });

  // 4. Pressure Resilience Comparison
  const pressureTrace = { x: names, y: players.map(p => p.pressure_score), name: "Pressure Score", type: "bar", marker: { color: "#f59e0b" } };
  const impactTrace = { x: names, y: players.map(p => p.overall_impact_score), name: "Overall Impact", type: "bar", marker: { color: "#2563eb" } };

  Plotly.newPlot("comp-chart-pressure", [pressureTrace, impactTrace], {
    barmode: "group",
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 20, r: 20, l: 30, b: 60 },
    legend: { orientation: "h", y: 1.15 },
    yaxis: { gridcolor: "#1e293b" }
  }, { responsive: true, displayModeBar: false });
}

// ---------------------------------------------------------------------------
// 7. Pressure Analytics & Player Pressure Percentage Analyzer
// ---------------------------------------------------------------------------
async function loadPressureSection() {
  const select = document.getElementById("analyzer-player-select");
  if (!select.children.length || select.options[0]?.value === "") {
    if (allPlayersCache.length === 0) {
      await preloadPlayerOptions();
    } else {
      populatePressurePlayerDropdown();
    }
  }

  // Auto analyze the first selected player (e.g. Virat Kohli [47])
  const playerId = parseInt(select.value, 10) || 47;
  await loadPressurePlayerAnalyzer(playerId);

  // Also load macro leaderboards
  loadMacroPressureLeaderboards();
}

async function loadPressurePlayerAnalyzer(playerId) {
  const format = document.getElementById("analyzer-format-filter")?.value || "All";
  const statusMsg = document.getElementById("analyzer-status-msg");

  if (statusMsg) {
    statusMsg.textContent = "Fetching delivery-level pressure data...";
    statusMsg.style.color = "var(--gold)";
  }

  try {
    const data = await API.getPlayerPressureAnalysis(playerId, format);

    if (statusMsg) {
      statusMsg.textContent = `Analysis complete for ${data.player_name}. ${data.explanation.sample_reliability}`;
      statusMsg.style.color = "var(--success)";
    }

    // 1. Banner Info
    document.getElementById("analyzer-player-name").textContent = data.player_name;
    document.getElementById("analyzer-player-role-badge").textContent = data.primary_role;
    document.getElementById("analyzer-player-summary").textContent = 
      `Career: ${data.matches_played} Matches • ${data.batting_pressure.pressure_runs} Pressure Runs (${data.batting_pressure.pressure_balls_faced} balls) • ${data.bowling_pressure.pressure_wickets} Pressure Wickets`;
    document.getElementById("analyzer-explanation-text").textContent = data.explanation.effectiveness;

    // Big score and badge
    document.getElementById("analyzer-score-pct").textContent = `${data.overall_pressure_percentage}%`;
    const classBadge = document.getElementById("analyzer-classification-badge");
    classBadge.textContent = `${data.classification.toUpperCase()} (${data.classification_band})`;
    classBadge.className = `pill pill-${data.classification.toLowerCase().replace(' ', '-')}`;

    // Sample warning pill
    const sampleBadge = document.getElementById("analyzer-sample-badge");
    const hasWarning = data.batting_pressure.sample_warning && data.bowling_pressure.sample_warning;
    if (hasWarning) {
      sampleBadge.textContent = "⚠️ Limited Sample Notice";
      sampleBadge.className = "pill pill-elite";
      sampleBadge.style.background = "#ef4444";
    } else {
      sampleBadge.textContent = "✓ Robust Sample Verified";
      sampleBadge.className = "pill pill-solid";
      sampleBadge.style.background = "";
    }

    // 2. Batting Pressure Card
    const bp = data.batting_pressure;
    document.getElementById("card-bat-score-badge").textContent = `${bp.pressure_score_pct}%`;
    document.getElementById("val-bat-score").textContent = `${bp.pressure_score_pct}%`;
    document.getElementById("val-bat-sr").textContent = bp.pressure_strike_rate;
    document.getElementById("val-bat-avg").textContent = bp.pressure_average;
    document.getElementById("val-bat-runs").textContent = bp.pressure_runs.toLocaleString();
    document.getElementById("val-bat-balls").textContent = bp.pressure_balls_faced.toLocaleString();
    document.getElementById("val-bat-bnd").textContent = `${bp.pressure_boundary_pct}%`;
    document.getElementById("val-bat-matches").textContent = bp.pressure_match_count;
    document.getElementById("val-bat-qual").textContent = `${bp.qualifying_match_count} (≥5 balls)`;

    const batWarnRow = document.getElementById("bat-sample-warning-row");
    if (bp.sample_warning) {
      batWarnRow.textContent = "⚠️ Limited sample: under 20 pressure deliveries faced.";
      batWarnRow.style.color = "var(--warning)";
      batWarnRow.style.background = "rgba(245, 158, 11, 0.15)";
    } else {
      batWarnRow.textContent = `✓ Robust sample: ${bp.pressure_balls_faced} deliveries across ${bp.qualifying_match_count} qualifying matches.`;
      batWarnRow.style.color = "var(--success)";
      batWarnRow.style.background = "rgba(16, 185, 129, 0.15)";
    }

    // 3. Bowling Pressure Card
    const bwp = data.bowling_pressure;
    document.getElementById("card-bowl-score-badge").textContent = `${bwp.pressure_score_pct}%`;
    document.getElementById("val-bowl-score").textContent = `${bwp.pressure_score_pct}%`;
    document.getElementById("val-bowl-econ").textContent = bwp.pressure_economy;
    document.getElementById("val-bowl-wkts").textContent = bwp.pressure_wickets;
    document.getElementById("val-bowl-balls").textContent = bwp.pressure_balls_bowled;
    document.getElementById("val-bowl-dots").textContent = `${bwp.pressure_dot_ball_pct}%`;
    document.getElementById("val-bowl-wkt-rate").textContent = `${bwp.pressure_wicket_rate} balls/wkt`;
    document.getElementById("val-bowl-matches").textContent = bwp.pressure_match_count;
    document.getElementById("val-bowl-qual").textContent = `${bwp.qualifying_match_count} (≥6 balls)`;

    const bowlWarnRow = document.getElementById("bowl-sample-warning-row");
    if (bwp.sample_warning) {
      bowlWarnRow.textContent = "⚠️ Limited sample: under 24 legal pressure deliveries bowled.";
      bowlWarnRow.style.color = "var(--warning)";
      bowlWarnRow.style.background = "rgba(245, 158, 11, 0.15)";
    } else {
      bowlWarnRow.textContent = `✓ Robust sample: ${bwp.pressure_balls_bowled} balls bowled across ${bwp.qualifying_match_count} qualifying matches.`;
      bowlWarnRow.style.color = "var(--success)";
      bowlWarnRow.style.background = "rgba(16, 185, 129, 0.15)";
    }

    // 4. Render Visualizations
    renderPressureVisualizations(data);

  } catch (err) {
    console.error("Pressure Analyzer Error:", err);
    if (statusMsg) {
      statusMsg.textContent = "Error running pressure analyzer: " + err.message;
      statusMsg.style.color = "var(--danger)";
    }
  }
}

function renderPressureVisualizations(data) {
  if (typeof Plotly === "undefined") return;

  // Chart 1: Gauge Indicator
  const gaugeData = [{
    type: "indicator",
    mode: "gauge+number",
    value: data.overall_pressure_percentage,
    title: { text: "Clutch Performance Index (%)", font: { color: "#94a3b8", size: 14 } },
    number: { suffix: "%", font: { color: "#f59e0b", size: 36 } },
    gauge: {
      axis: { range: [0, 100], tickwidth: 1, tickcolor: "#64748b" },
      bar: { color: "#f59e0b", thickness: 0.25 },
      bgcolor: "transparent",
      borderwidth: 1,
      bordercolor: "#1e293b",
      steps: [
        { range: [0, 40], color: "rgba(239, 68, 68, 0.3)" },
        { range: [40, 55], color: "rgba(249, 115, 22, 0.3)" },
        { range: [55, 70], color: "rgba(245, 158, 11, 0.3)" },
        { range: [70, 85], color: "rgba(59, 130, 246, 0.3)" },
        { range: [85, 100], color: "rgba(16, 185, 129, 0.3)" },
      ],
    }
  }];

  Plotly.newPlot("analyzer-gauge-chart", gaugeData, {
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    margin: { t: 40, r: 25, l: 25, b: 25 }
  }, { responsive: true, displayModeBar: false });

  // Chart 2: Batting vs Bowling Pressure Balance
  const balanceTrace = {
    x: ["Batting Pressure", "Bowling Pressure", "Combined Index"],
    y: [data.batting_pressure.pressure_score_pct, data.bowling_pressure.pressure_score_pct, data.overall_pressure_percentage],
    type: "bar",
    marker: { color: ["#3b82f6", "#f59e0b", "#10b981"] }
  };

  Plotly.newPlot("analyzer-balance-chart", [balanceTrace], {
    title: { text: "Discipline Pressure Balance", font: { size: 13, color: "#94a3b8" } },
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 35, r: 20, l: 30, b: 50 },
    yaxis: { range: [0, 100], title: "Percentage Score (%)", gridcolor: "#1e293b" }
  }, { responsive: true, displayModeBar: false });

  // Chart 3: Recent Pressure Performance Trend
  const trend = data.trend || [];
  const trendTrace = {
    x: trend.map(t => t.label),
    y: trend.map(t => t.metric),
    mode: "lines+markers",
    line: { color: "#f59e0b", width: 2 },
    marker: { size: 8, color: "#2563eb" },
    name: "Pressure SR"
  };

  Plotly.newPlot("analyzer-trend-chart", [trendTrace], {
    title: { text: "Chronological Match Pressure SR Trend", font: { size: 13, color: "#94a3b8" } },
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 35, r: 20, l: 35, b: 60 },
    xaxis: { tickangle: -20, gridcolor: "#1e293b" },
    yaxis: { title: "Strike Rate in Pressure Overs", gridcolor: "#1e293b" }
  }, { responsive: true, displayModeBar: false });

  // Chart 4: Situational Contribution (Death Overs vs Chasing)
  const sit = data.situational_breakdown;
  const sitTraceRuns = {
    x: ["Death Overs (16-20)", "Innings 2 Chasing"],
    y: [sit.death_overs.runs, sit.chase_innings_2.runs],
    name: "Runs",
    type: "bar",
    marker: { color: "#2563eb" }
  };
  const sitTraceSR = {
    x: ["Death Overs (16-20)", "Innings 2 Chasing"],
    y: [sit.death_overs.strike_rate, sit.chase_innings_2.strike_rate],
    name: "Strike Rate",
    type: "bar",
    marker: { color: "#f59e0b" }
  };

  Plotly.newPlot("analyzer-situation-chart", [sitTraceRuns, sitTraceSR], {
    barmode: "group",
    title: { text: "Situational Phase Contribution", font: { size: 13, color: "#94a3b8" } },
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 35, r: 20, l: 30, b: 50 },
    legend: { orientation: "h", y: 1.15 },
    yaxis: { gridcolor: "#1e293b" }
  }, { responsive: true, displayModeBar: false });
}

async function loadMacroPressureLeaderboards() {
  try {
    const data = await API.getPressureAnalysis(15);
    
    const batTbody = document.getElementById("pressure-batting-tbody");
    batTbody.innerHTML = "";
    data.batting_pressure_rankings.forEach((p, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="rank-badge rank-${idx < 3 ? idx + 1 : 'other'}">${idx + 1}</span></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td>${p.matches_played}</td>
        <td>${p.total_runs}</td>
        <td>${p.strike_rate}</td>
        <td><strong style="color:var(--gold); font-size:14px;">${p.pressure_score}%</strong></td>
        <td><span class="pill pill-${p.clutch_rating.toLowerCase()}">${p.clutch_rating}</span></td>
        <td>
          <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="loadPressurePlayerAnalyzer(${p.player_id})">
            Analyze
          </button>
        </td>
      `;
      batTbody.appendChild(tr);
    });

    const bowlTbody = document.getElementById("pressure-bowling-tbody");
    bowlTbody.innerHTML = "";
    data.bowling_pressure_rankings.forEach((p, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><span class="rank-badge rank-${idx < 3 ? idx + 1 : 'other'}">${idx + 1}</span></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td>${p.matches_played}</td>
        <td>${p.total_wickets}</td>
        <td>${p.bowling_economy}</td>
        <td><strong style="color:var(--gold); font-size:14px;">${p.pressure_score}%</strong></td>
        <td><span class="pill pill-${p.clutch_rating.toLowerCase()}">${p.clutch_rating}</span></td>
        <td>
          <button class="btn btn-secondary" style="padding: 3px 8px; font-size: 11px;" onclick="loadPressurePlayerAnalyzer(${p.player_id})">
            Analyze
          </button>
        </td>
      `;
      bowlTbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Macro Leaderboards Error:", err);
  }
}

// ---------------------------------------------------------------------------
// 8. ML Training Monitor
// ---------------------------------------------------------------------------
let trainingPollInterval = null;

async function loadTrainingMonitor() {
  loadTrainingHistory();
  checkTrainingStatus();
}

async function triggerCustomTraining() {
  const modelType = document.getElementById("train-model-type").value;
  const algorithm = document.getElementById("train-algorithm").value;
  const nEstimators = parseInt(document.getElementById("train-n-estimators").value, 10);
  const maxDepth = parseInt(document.getElementById("train-max-depth").value, 10);
  const learningRate = parseFloat(document.getElementById("train-learning-rate").value);
  const testSize = parseFloat(document.getElementById("train-test-size").value);
  const cvFolds = parseInt(document.getElementById("train-cv-folds").value, 10);

  const btn = document.getElementById("btn-start-training");
  btn.disabled = true;
  btn.textContent = "Initiating Training...";

  try {
    const res = await API.triggerTraining({
      model_type: modelType,
      algorithm: algorithm,
      n_estimators: nEstimators,
      max_depth: maxDepth > 0 ? maxDepth : null,
      learning_rate: learningRate,
      test_size: testSize,
      cross_validation_folds: cvFolds
    });

    document.getElementById("training-status-badge").textContent = "TRAINING IN PROGRESS";
    document.getElementById("training-status-badge").className = "pill pill-elite";
    document.getElementById("training-status-text").textContent = res.message;

    if (trainingPollInterval) clearInterval(trainingPollInterval);
    trainingPollInterval = setInterval(pollTrainingStatus, 1500);
  } catch (err) {
    alert("Training trigger failed: " + err.message);
    btn.disabled = false;
    btn.textContent = "Start Training Execution";
  }
}

async function pollTrainingStatus() {
  try {
    const status = await API.getTrainingStatus();
    document.getElementById("training-progress-fill").style.width = `${status.progress_percent}%`;
    document.getElementById("training-status-text").textContent = status.status_message;

    if (!status.is_training) {
      clearInterval(trainingPollInterval);
      const btn = document.getElementById("btn-start-training");
      btn.disabled = false;
      btn.textContent = "Start Training Execution";

      document.getElementById("training-status-badge").textContent = "COMPLETED";
      document.getElementById("training-status-badge").className = "pill pill-solid";
      loadTrainingHistory();
      loadModelEvaluation();
    }
  } catch (err) {
    console.error("Poll error:", err);
  }
}

async function checkTrainingStatus() {
  const status = await API.getTrainingStatus();
  document.getElementById("training-progress-fill").style.width = `${status.progress_percent}%`;
  document.getElementById("training-status-text").textContent = status.status_message;
  if (status.is_training) {
    document.getElementById("training-status-badge").textContent = "TRAINING IN PROGRESS";
    document.getElementById("training-status-badge").className = "pill pill-elite";
    if (!trainingPollInterval) trainingPollInterval = setInterval(pollTrainingStatus, 1500);
  }
}

async function loadTrainingHistory() {
  try {
    const res = await API.getTrainingHistory();
    const tbody = document.getElementById("training-history-tbody");
    tbody.innerHTML = "";

    if (!res.history || res.history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No recorded training runs yet. Configure parameters above and run training.</td></tr>`;
      return;
    }

    res.history.forEach(h => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${h.timestamp}</td>
        <td><strong>${escapeHtml(h.model_type.toUpperCase())}</strong></td>
        <td><span class="pill pill-normal">${escapeHtml(h.algorithm)}</span></td>
        <td>n=${h.hyperparameters.n_estimators}, depth=${h.hyperparameters.max_depth || 'Auto'}, cv=${h.hyperparameters.cv_folds}</td>
        <td>${h.mae}</td>
        <td><strong>${h.rmse}</strong></td>
        <td>${h.r2}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Training history error:", err);
  }
}

// ---------------------------------------------------------------------------
// 9. Model Evaluation & Sandbox
// ---------------------------------------------------------------------------
async function loadModelEvaluation() {
  try {
    const data = await API.getModelsStatus();
    const container = document.getElementById("models-status-cards");
    container.innerHTML = "";

    data.models.forEach(m => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.borderLeft = "4px solid var(--royal-blue-light)";
      card.innerHTML = `
        <div class="card-title">
          <span>${escapeHtml(m.model_name)} (v${m.version})</span>
          <span class="badge">${m.status}</span>
        </div>
        <div style="font-size: 13px; margin-bottom: 12px; color: var(--text-muted);">
          Algorithm: <strong>${escapeHtml(m.algorithm)}</strong> • Trained: ${m.training_date.slice(0, 19).replace('T', ' ')}
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; background: rgba(0,0,0,0.25); padding: 14px; border-radius: var(--radius-sm); margin-bottom: 12px; text-align: center;">
          <div><div style="font-size:11px; color:var(--text-muted);">MAE</div><strong style="font-size:18px;">${m.mae}</strong></div>
          <div><div style="font-size:11px; color:var(--text-muted);">RMSE</div><strong style="font-size:18px; color:var(--gold);">${m.rmse}</strong></div>
          <div><div style="font-size:11px; color:var(--text-muted);">R² SCORE</div><strong style="font-size:18px; color:var(--royal-blue-light);">${m.r2}</strong></div>
        </div>
        <div style="font-size: 11px; color: var(--text-muted);">
          Input Features: ${m.features.join(", ")}
        </div>
      `;
      container.appendChild(card);
    });

    renderAlgorithmComparison(data.models);
  } catch (err) {
    console.error("Model Evaluation Error:", err);
  }
}

function renderAlgorithmComparison(models) {
  const chartDiv = document.getElementById("model-comparison-chart");
  if (!chartDiv || typeof Plotly === "undefined") return;

  const batModel = models.find(m => m.model_name.includes("Batting"));
  if (!batModel || !batModel.comparison) return;

  const algos = Object.keys(batModel.comparison);
  const cvRmse = algos.map(a => batModel.comparison[a].cv_rmse);
  const testRmse = algos.map(a => batModel.comparison[a].test_rmse);

  const trace1 = { x: algos, y: cvRmse, name: "CV RMSE (Lower is Better)", type: "bar", marker: { color: "#2563eb" } };
  const trace2 = { x: algos, y: testRmse, name: "Test RMSE (Lower is Better)", type: "bar", marker: { color: "#f59e0b" } };

  const layout = {
    title: "Algorithm Benchmarking Comparison (Batting Predictor)",
    barmode: "group",
    plot_bgcolor: "transparent",
    paper_bgcolor: "transparent",
    font: { color: "#94a3b8", family: "Inter, sans-serif" },
    margin: { t: 40, r: 20, l: 40, b: 60 },
    legend: { orientation: "h", y: 1.15 },
    yaxis: { gridcolor: "#1e293b" }
  };

  Plotly.newPlot(chartDiv, [trace1, trace2], layout, { responsive: true, displayModeBar: false });
}

async function runBattingPrediction() {
  const avg = parseFloat(document.getElementById("pred-bat-avg").value);
  const sr = parseFloat(document.getElementById("pred-bat-sr").value);
  const recAvg = parseFloat(document.getElementById("pred-bat-rec-avg").value);
  const recSr = parseFloat(document.getElementById("pred-bat-rec-sr").value);
  const order = parseInt(document.getElementById("pred-bat-order").value, 10);
  const inn = parseInt(document.getElementById("pred-bat-inn").value, 10);
  const pressure = parseFloat(document.getElementById("pred-bat-pressure").value);

  try {
    const res = await API.predictBatting({
      career_avg: avg,
      career_sr: sr,
      recent_5_avg: recAvg,
      recent_5_sr: recSr,
      batting_order: order,
      innings: inn,
      pressure_situation: pressure
    });

    document.getElementById("pred-bat-result").innerHTML = `
      <div style="background: rgba(37, 99, 235, 0.15); border: 1px solid var(--royal-blue); padding: 16px; border-radius: var(--radius-sm); margin-top: 10px;">
        <div style="font-size: 11px; text-transform: uppercase; color: var(--gold); font-weight: 600;">Predicted Runs:</div>
        <div style="font-size: 32px; font-weight: 700; color: #fff; margin: 4px 0;">${res.predicted_value} runs</div>
        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Confidence Range: ${res.confidence_interval.lower} – ${res.confidence_interval.upper} runs</div>
        <div style="font-size: 11px; color: #cbd5e1;">Model: ${res.model_algorithm} (v${res.model_version})</div>
      </div>
    `;
  } catch (err) {
    alert("Prediction error: " + err.message);
  }
}

async function checkSystemHealth() {
  try {
    const health = await API.getHealth();
    const sidebarDb = document.getElementById("sidebar-db-status");
    if (sidebarDb) {
      sidebarDb.textContent = `DB: ${health.database_type}`;
    }
  } catch (err) {
    const sidebarDb = document.getElementById("sidebar-db-status");
    if (sidebarDb) {
      sidebarDb.textContent = "API Offline";
      sidebarDb.style.color = "var(--danger)";
    }
  }
}

// ---------------------------------------------------------------------------
// Setup Event Listeners
// ---------------------------------------------------------------------------
function setupEventListeners() {
  // Player search
  document.getElementById("player-search-input")?.addEventListener("input", debounce(() => {
    playerPage = 1;
    loadPlayersList();
  }, 300));

  document.getElementById("player-role-filter")?.addEventListener("change", () => {
    playerPage = 1;
    loadPlayersList();
  });

  document.getElementById("player-sort-filter")?.addEventListener("change", () => {
    loadPlayersList();
  });

  document.getElementById("btn-prev-page")?.addEventListener("click", () => {
    if (playerPage > 1) {
      playerPage--;
      loadPlayersList();
    }
  });

  document.getElementById("btn-next-page")?.addEventListener("click", () => {
    playerPage++;
    loadPlayersList();
  });

  // Selector filters
  document.getElementById("selector-role-select")?.addEventListener("change", loadSmartSelector);
  document.getElementById("selector-min-matches")?.addEventListener("change", loadSmartSelector);

  // Comparison Controls
  document.getElementById("btn-execute-comparison")?.addEventListener("click", renderComparisonWorkspace);
  document.getElementById("compare-role-filter")?.addEventListener("change", (e) => {
    populateComparisonDropdowns(e.target.value);
  });

  // Rankings filters
  document.getElementById("batting-sort-select")?.addEventListener("change", loadBattingRankings);
  document.getElementById("bowling-sort-select")?.addEventListener("change", loadBowlingRankings);

  // Pressure Percentage Analyzer Controls
  document.getElementById("btn-run-pressure-analysis")?.addEventListener("click", () => {
    const sel = document.getElementById("analyzer-player-select");
    const pid = parseInt(sel.value, 10);
    if (pid) loadPressurePlayerAnalyzer(pid);
  });

  document.getElementById("analyzer-role-filter")?.addEventListener("change", (e) => {
    populatePressurePlayerDropdown(e.target.value);
  });

  // Training monitor trigger
  document.getElementById("btn-start-training")?.addEventListener("click", triggerCustomTraining);

  // Prediction sandbox trigger
  document.getElementById("btn-run-bat-pred")?.addEventListener("click", runBattingPrediction);

  // Close modals
  document.querySelectorAll(".modal-close").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
    });
  });
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/[&<>"']/g, m => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[m]));
}
