/** RR Intelligence Hub — static GitHub Pages data adapter.
 * Reads the verified JSON export; no backend server or API routes required.
 */
const DATA_URL = new URL('../rr_intelligence_static_data.json', document.currentScript.src).href;
let dataPromise;
const loadData = () => dataPromise ||= fetch(DATA_URL).then(r => {
  if (!r.ok) throw new Error(`Unable to load cricket dataset (${r.status})`);
  return r.json();
});
const num = v => Number.isFinite(Number(v)) ? Number(v) : 0;
const round = v => Math.round(num(v) * 10) / 10;
const by = (a, b, key, order='desc') => (num(a[key])-num(b[key])) * (order === 'asc' ? 1 : -1);
const rating = p => String(p.clutch_rating || (num(p.pressure_score)>=75?'Elite':num(p.pressure_score)>=60?'Strong':num(p.pressure_score)>=45?'Average':'Developing'));
const rank = (rows, key, limit=25, order='desc') => [...rows].sort((a,b)=>by(a,b,key,order)).slice(0,limit).map((p,i)=>({...p,rank:i+1,clutch_rating:rating(p)}));
const API = {
 async getHealth(){const d=await loadData();return {status:'healthy',database_type:'Static JSON',source:'verified SQLite export'};},
 async getOverview(){const d=await loadData();const p=d.players;const bat=[...p].sort((a,b)=>by(a,b,'total_runs'))[0];const bowl=[...p].sort((a,b)=>by(a,b,'total_wickets'))[0];const clutch=[...p].sort((a,b)=>by(a,b,'pressure_score'))[0];return {total_players:p.length,total_matches:d.matches.length,total_competitions:d.competitions.length,total_teams:d.teams.length,highlights:{top_run_scorer:{name:bat.name,runs:bat.total_runs,avg:bat.batting_avg},top_wicket_taker:{name:bowl.name,wickets:bowl.total_wickets,economy:bowl.bowling_economy},top_clutch_player:{name:clutch.name,pressure_score:clutch.pressure_score,clutch_rating:rating(clutch)}}};},
 async getPlayerOptions(){const d=await loadData();return d.players.map(p=>({...p,clutch_rating:rating(p)})).sort((a,b)=>a.name.localeCompare(b.name));},
 async getPlayers({query='',role='All',minMatches=0,sortBy='total_runs',order='desc',page=1,pageSize=15}={}){const d=await loadData();let rows=d.players.filter(p=>(role==='All'||p.primary_role===role)&&num(p.matches_played)>=num(minMatches)&&p.name.toLowerCase().includes(query.toLowerCase()));rows.sort((a,b)=>by(a,b,sortBy,order));const total_records=rows.length,total_pages=Math.max(1,Math.ceil(total_records/pageSize));return {players:rows.slice((page-1)*pageSize,page*pageSize).map(p=>({...p,clutch_rating:rating(p)})),total_records,total_pages,page};},
 async getPlayerDetail(id){const d=await loadData();const p=d.players.find(x=>String(x.player_id)===String(id));if(!p)throw new Error('Player not found');return {...p,clutch_rating:rating(p)};},
 async comparePlayers(ids){const d=await loadData();const players=ids.map(id=>d.players.find(p=>String(p.player_id)===String(id))).filter(Boolean).map(p=>({...p,clutch_rating:rating(p)}));const leader=(key)=>{const p=[...players].sort((a,b)=>by(a,b,key))[0];return p?{name:p.name,reason:`Highest ${key.replaceAll('_',' ')} among the selected players (${p[key]}).`}:null;};return {players,insights:{batting_leader:leader('total_runs'),bowling_leader:leader('total_wickets'),clutch_leader:leader('pressure_score'),consistency_leader:leader('consistency_score'),overall_recommendation:leader('overall_impact_score')}};},
 async getBattingRankings(limit=25,sortBy='total_runs'){const d=await loadData();return {rankings:rank(d.players.filter(p=>num(p.innings_batted)>0),sortBy,limit)};},
 async getBowlingRankings(limit=25,sortBy='total_wickets'){const d=await loadData();return {rankings:rank(d.players.filter(p=>num(p.overs_bowled)>0||num(p.total_wickets)>0),sortBy,limit)};},
 async getOverallRankings(limit=25){const d=await loadData();return {rankings:rank(d.players,'overall_impact_score',limit)};},
 async getSelectorRecommendations(role='All',limit=10,minMatches=5){const d=await loadData();let rows=d.players.filter(p=>num(p.matches_played)>=minMatches&&(role==='All'||p.primary_role===role||num(p.role_scores?.[role])>0));rows.sort((a,b)=>num(role==='All'?b.overall_impact_score:(b.role_scores?.[role]??b.primary_suitability_score))-num(role==='All'?a.overall_impact_score:(a.role_scores?.[role]??a.primary_suitability_score)));return {recommendations:rows.slice(0,limit).map((p,i)=>({...p,rank:i+1,composite_score:round(role==='All'?p.overall_impact_score:(p.role_scores?.[role]??p.primary_suitability_score)),recommendation_reasons:[p.role_explanations?.[role]||'Ranked using the saved player suitability and performance metrics.'],tactical_fit:p.primary_role,clutch_rating:rating(p)}))};},
 async getPressureAnalysis(limit=20){const d=await loadData();return {batting_pressure_rankings:rank(d.players.filter(p=>num(p.innings_batted)>0),'pressure_score',limit),bowling_pressure_rankings:rank(d.players.filter(p=>num(p.total_wickets)>0),'pressure_score',limit)};},
 async getPlayerPressureAnalysis(id){const p=await this.getPlayerDetail(id);throw new Error('Detailed delivery-level pressure breakdown is not included in the static data export. Saved overall pressure score and evidence are available in this player profile.');},
 async getModelsStatus(){const d=await loadData();return {models:d.ml_model_status.map(m=>({...m,features:[],comparison:null}))};},
 async getTrainingHistory(){const d=await loadData();return {history:d.training_history||[]};},
 async getTrainingStatus(){return {is_training:false,progress_percent:0,status_message:'Static GitHub Pages mode — model training requires the Python backend.'};},
 async triggerTraining(){throw new Error('Model training is unavailable on static GitHub Pages. Run training locally or on a backend server.');},
 async predictBatting(){throw new Error('Live ML prediction requires the Python model runtime and is unavailable on static GitHub Pages.');},
 async predictBowling(){throw new Error('Live ML prediction requires the Python model runtime and is unavailable on static GitHub Pages.');}
};
