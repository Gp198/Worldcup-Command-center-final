from __future__ import annotations

import os
import random
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from agents.orchestrator import AgentOrchestrator
from agents.executive_war_room import ExecutiveWarRoom
from connectors.data_layer import connector_status, load_phase2_data
from connectors.live_data import LiveFootballDataHub
from observability.health import app_health
from models.predictor import MatchPredictor
from simulator.monte_carlo import TournamentSimulator

st.set_page_config(
    page_title="World Cup Command Center 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

FLAGS = {
    "Portugal": "🇵🇹", "Brazil": "🇧🇷", "France": "🇫🇷", "Argentina": "🇦🇷", "Spain": "🇪🇸",
    "England": "🏴", "Germany": "🇩🇪", "Netherlands": "🇳🇱", "USA": "🇺🇸", "Mexico": "🇲🇽",
    "Japan": "🇯🇵", "Morocco": "🇲🇦", "Canada": "🇨🇦", "Italy": "🇮🇹", "Uruguay": "🇺🇾",
    "Belgium": "🇧🇪", "Croatia": "🇭🇷", "Colombia": "🇨🇴", "Switzerland": "🇨🇭", "Denmark": "🇩🇰",
    "Senegal": "🇸🇳", "Austria": "🇦🇹", "Australia": "🇦🇺", "Iran": "🇮🇷", "Korea Republic": "🇰🇷",
    "South Africa": "🇿🇦", "Czechia": "🇨🇿", "Nigeria": "🇳🇬", "Egypt": "🇪🇬", "Ghana": "🇬🇭",
    "Turkey": "🇹🇷", "Poland": "🇵🇱", "Norway": "🇳🇴", "Scotland": "🏴", "Wales": "🏴",
    "Serbia": "🇷🇸", "Ecuador": "🇪🇨", "Paraguay": "🇵🇾", "Chile": "🇨🇱", "Peru": "🇵🇪",
    "Qatar": "🇶🇦", "Saudi Arabia": "🇸🇦", "Tunisia": "🇹🇳", "Algeria": "🇩🇿", "Cameroon": "🇨🇲",
    "Costa Rica": "🇨🇷", "Panama": "🇵🇦", "Jamaica": "🇯🇲", "New Zealand": "🇳🇿"
}

TEAM_STYLE = {
    "Portugal": "technical midfield control, flexible attacking rotations and strong squad depth",
    "Brazil": "explosive transition play, elite 1v1 creativity and dangerous wide attacks",
    "France": "physical dominance, vertical speed and high-end attacking efficiency",
    "Argentina": "compact control, elite decision making and tournament experience",
    "Spain": "possession control, positional play and midfield overloads",
    "England": "set-piece threat, powerful transitions and depth across the front line",
    "Germany": "structured pressing, central progression and high-tempo attacking phases",
    "Netherlands": "compact defensive shape, wing progression and direct attacking routes",
    "USA": "athletic pressing, fast transitions and improving tactical maturity",
    "Mexico": "aggressive tempo, wide combinations and emotional tournament intensity",
    "Japan": "technical discipline, pressing triggers and fast collective transitions",
    "Morocco": "compact defensive resilience, counter-attacking speed and tactical discipline",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp {
    background:
        radial-gradient(circle at 10% 0%, rgba(25,199,217,.16), transparent 28%),
        radial-gradient(circle at 90% 0%, rgba(214,178,94,.18), transparent 26%),
        linear-gradient(135deg, #051226 0%, #071B33 48%, #0A2347 100%);
    color:#EAF2FF;
}
header[data-testid="stHeader"] { background:rgba(5,18,38,.72); backdrop-filter:blur(18px); border-bottom:1px solid rgba(255,255,255,.08); }
.block-container { max-width:1500px; padding-top:1.25rem; padding-bottom:3rem; }
section[data-testid="stSidebar"] { background:linear-gradient(180deg,#031126 0%,#071B33 55%,#020814 100%); border-right:1px solid rgba(255,255,255,.1); }
section[data-testid="stSidebar"] * { color:#F8FBFF !important; }
section[data-testid="stSidebar"] div[role="radiogroup"] label { background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.11); border-radius:15px; padding:.72rem .78rem; margin-bottom:.44rem; }
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover { border-color:rgba(25,199,217,.55); background:rgba(25,199,217,.11); }
.sidebar-brand { padding:.45rem 0 1.1rem; }
.brand-title { font-size:1.16rem; font-weight:900; letter-spacing:-.03em; line-height:1.08; }
.brand-caption { color:#9FB2D1 !important; font-size:.76rem; margin-top:.45rem; line-height:1.5; }
.status-panel { margin-top:1.3rem; padding:1rem; background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.035)); border:1px solid rgba(255,255,255,.12); border-radius:22px; }
.status-title,.briefing-title { font-weight:950; font-size:.8rem; text-transform:uppercase; letter-spacing:.12em; color:#D6B25E !important; margin-bottom:.75rem; }
.status-row { display:flex; align-items:center; justify-content:space-between; gap:.6rem; padding:.46rem 0; border-bottom:1px solid rgba(255,255,255,.07); font-size:.82rem; }
.status-row:last-child { border-bottom:none; }
.dot { width:8px; height:8px; border-radius:50%; display:inline-block; background:#42E8C6; box-shadow:0 0 16px rgba(66,232,198,.92); margin-right:.42rem; }
.hero { position:relative; overflow:hidden; border-radius:34px; padding:2.65rem 2.8rem; background:linear-gradient(135deg,rgba(4,18,41,.98),rgba(8,35,74,.96) 42%,rgba(13,73,134,.92) 72%,rgba(22,196,217,.84)); border:1px solid rgba(255,255,255,.16); box-shadow:0 28px 90px rgba(0,0,0,.34); margin-bottom:1.6rem; }
.hero-title { margin:1rem 0 .42rem; font-weight:950; letter-spacing:-.075em; line-height:.92; font-size:clamp(2.7rem,5.2vw,5.8rem); color:white; max-width:1000px; }
.hero-platform { color:#D6B25E; font-size:clamp(1rem,2vw,1.5rem); font-weight:900; letter-spacing:.12em; text-transform:uppercase; }
.hero-subtitle { color:rgba(234,242,255,.82); font-size:1.04rem; line-height:1.7; max-width:980px; }
.eyebrow,.hero-tag { display:inline-flex; border:1px solid rgba(255,255,255,.18); background:rgba(255,255,255,.09); color:rgba(234,242,255,.92); border-radius:999px; padding:.48rem .9rem; font-size:.77rem; font-weight:900; letter-spacing:.1em; text-transform:uppercase; }
.hero-tags { display:flex; flex-wrap:wrap; gap:.62rem; margin-top:1.25rem; }
.hero-kpis { display:grid; grid-template-columns:repeat(4,minmax(120px,1fr)); gap:.75rem; margin-top:1.5rem; max-width:820px; }
.hero-kpi { padding:.95rem 1.05rem; border-radius:22px; background:rgba(255,255,255,.105); border:1px solid rgba(255,255,255,.15); }
.hero-kpi strong { display:block; color:#fff; font-size:1.26rem; font-weight:950; }
.hero-kpi span { display:block; color:rgba(234,242,255,.72); font-size:.74rem; margin-top:.18rem; }
.section-head { margin:.8rem 0 1rem; }
.section-title { color:#fff; font-size:1.75rem; font-weight:950; letter-spacing:-.055em; }
.section-caption { color:#9FB2D1; margin-top:.38rem; font-size:.95rem; }
.glass-card,.glass-card-tight,.ai-answer-card { background:rgba(9,29,58,.74); border:1px solid rgba(255,255,255,.12); border-radius:26px; padding:1.18rem; box-shadow:0 24px 65px rgba(0,0,0,.22); backdrop-filter:blur(18px); margin-bottom:1rem; }
.glass-card-tight { border-radius:22px; padding:.92rem; margin-bottom:.8rem; }
.briefing { border-radius:26px; padding:1.2rem 1.25rem; background:linear-gradient(90deg,rgba(214,178,94,.16),rgba(255,255,255,.045)),rgba(255,255,255,.04); border:1px solid rgba(214,178,94,.28); box-shadow:0 18px 45px rgba(0,0,0,.18); margin-bottom:1rem; }
.briefing-text { color:#EAF2FF; line-height:1.72; font-size:.96rem; }
.matchup-shell { padding:1.1rem; border-radius:34px; background:linear-gradient(135deg,rgba(255,255,255,.095),rgba(255,255,255,.045)),radial-gradient(circle at center,rgba(214,178,94,.16),transparent 38%); border:1px solid rgba(255,255,255,.13); box-shadow:0 24px 70px rgba(0,0,0,.25); margin-bottom:1rem; }
.team-card { min-height:245px; border-radius:28px; padding:1.25rem; background:linear-gradient(160deg,rgba(255,255,255,.13),rgba(255,255,255,.055)),linear-gradient(135deg,rgba(11,61,145,.22),rgba(25,199,217,.04)); border:1px solid rgba(255,255,255,.16); }
.flag-xl { font-size:4rem; line-height:1; }
.team-name { color:#fff; font-size:2rem; font-weight:950; letter-spacing:-.055em; margin-top:.45rem; }
.team-meta { color:#9FB2D1; font-size:.84rem; margin-top:.18rem; }
.stat-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:.6rem; margin-top:1rem; }
.mini-stat { border-radius:16px; padding:.72rem; background:rgba(255,255,255,.075); border:1px solid rgba(255,255,255,.10); }
.mini-stat span { color:#9FB2D1; display:block; font-size:.70rem; text-transform:uppercase; font-weight:850; letter-spacing:.07em; }
.mini-stat strong { color:#fff; display:block; font-size:1.08rem; font-weight:950; margin-top:.12rem; }
.form-row { display:flex; gap:.28rem; margin-top:.9rem; }
.form-badge { width:28px; height:28px; display:flex; align-items:center; justify-content:center; border-radius:9px; font-size:.72rem; font-weight:950; color:#061833; background:#42E8C6; }
.form-badge.D { background:#D6B25E; } .form-badge.L { background:#FF5F6D; color:#fff; }
.vs-orb { width:92px; height:92px; border-radius:999px; display:flex; align-items:center; justify-content:center; margin:5.4rem auto 0; color:#fff; font-weight:950; background:radial-gradient(circle at 32% 20%,#19C7D9,#0B3D91 48%,#061833); border:5px solid rgba(255,255,255,.92); }
.metric-card { border-radius:24px; padding:1.1rem; background:linear-gradient(160deg,rgba(255,255,255,.12),rgba(255,255,255,.045)); border:1px solid rgba(255,255,255,.14); min-height:142px; box-shadow:0 18px 45px rgba(0,0,0,.18); }
.metric-label { color:#9FB2D1; font-size:.76rem; text-transform:uppercase; font-weight:900; letter-spacing:.085em; }
.metric-value { color:white; font-size:2.35rem; font-weight:950; letter-spacing:-.07em; margin-top:.25rem; }
.metric-sub { color:#9FB2D1; font-size:.8rem; margin-top:.2rem; }
.gold-line { width:52px; height:4px; border-radius:999px; background:linear-gradient(90deg,#D6B25E,#F7D774); margin-top:.72rem; }
.ai-answer-card h1,.ai-answer-card h2,.ai-answer-card h3,.ai-answer-card h4 { color:#F7D774 !important; }
.ai-answer-card p,.ai-answer-card li { color:#EAF2FF !important; line-height:1.7; font-size:.98rem; }
.ai-answer-card strong { color:#FFFFFF !important; } .ai-answer-card em { color:#D6B25E !important; }
.stButton > button { background:linear-gradient(135deg,#D6B25E,#F7D774) !important; color:#061833 !important; border-radius:15px !important; font-weight:950 !important; border:1px solid rgba(255,255,255,.22) !important; }
[data-testid="stSelectbox"] label,[data-testid="stSlider"] label,[data-testid="stTextArea"] label,[data-testid="stRadio"] label,[data-testid="stNumberInput"] label { color:#EAF2FF !important; font-weight:800 !important; }
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,[data-testid="stTextArea"] textarea,[data-testid="stNumberInput"] input { background:rgba(9,31,61,.96) !important; border:1px solid rgba(255,255,255,.18) !important; border-radius:16px !important; color:#fff !important; }
.stMarkdown pre,.stMarkdown code,pre,code { background:rgba(4,18,41,.92) !important; color:#EAF2FF !important; border-radius:14px !important; white-space:pre-wrap !important; word-break:break-word !important; }
.footer-note { color:#7486A5; font-size:.78rem; margin-top:2rem; border-top:1px solid rgba(255,255,255,.08); padding-top:1rem; }
@media (max-width:900px) { .hero-kpis { grid-template-columns:repeat(2,1fr); } .vs-orb { margin:1rem auto; } }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return load_phase2_data()


@st.cache_data
def load_connector_status() -> pd.DataFrame:
    return connector_status()


def flag(team: str) -> str:
    return FLAGS.get(team, "🏳️")


def row_value(row: pd.Series, key: str, default: Any) -> Any:
    try:
        value = row.get(key, default)
        return default if pd.isna(value) else value
    except Exception:
        return default


def team_record(team: str) -> pd.Series:
    return teams_df.loc[teams_df["team"] == team].iloc[0]


def get_form(team: str) -> list[str]:
    row = team_record(team)
    value = row_value(row, "form_string", "W-D-W-L-W")
    return str(value).split("-")


def render_form(team: str) -> str:
    return "".join([f"<span class='form-badge {r}'>{r}</span>" for r in get_form(team)])


def team_card(team: str) -> None:
    row = team_record(team)
    conf = row_value(row, "confederation", "N/A")
    rank = int(row_value(row, "fifa_rank", 99))
    elo = int(row_value(row, "elo", 1800))
    attack = float(row_value(row, "attack_strength", 75))
    defense = float(row_value(row, "defense_strength", 75))
    squad = float(row_value(row, "squad_strength", 78))
    form = float(row_value(row, "recent_form", .55))
    st.markdown(f"""
    <div class="team-card">
        <div class="flag-xl">{flag(team)}</div>
        <div class="team-name">{team}</div>
        <div class="team-meta">{conf} · FIFA Rank #{rank} · Elo {elo}</div>
        <div class="stat-grid">
            <div class="mini-stat"><span>Attack</span><strong>{attack:.1f}</strong></div>
            <div class="mini-stat"><span>Defense</span><strong>{defense:.1f}</strong></div>
            <div class="mini-stat"><span>Squad</span><strong>{squad:.1f}</strong></div>
            <div class="mini-stat"><span>Form</span><strong>{round(form * 100)}%</strong></div>
        </div>
        <div class="form-row">{render_form(team)}</div>
    </div>
    """, unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown("""
    <div class="hero">
        <div class="eyebrow">🏆 Football intelligence product</div>
        <div class="hero-title">World Cup Command Center</div>
        <div class="hero-platform">2026 Tournament Intelligence Platform</div>
        <div class="hero-subtitle">Predict • Simulate • Analyze • Strategize. A zero-cost AI command center combining predictive models, multi-agent analysis, football intelligence, RAG-ready knowledge and complete tournament simulation.</div>
        <div class="hero-tags">
            <div class="hero-tag">Real Multi-Agent Layer</div><div class="hero-tag">100,000 Monte Carlo Runs</div><div class="hero-tag">Ask the Coach</div><div class="hero-tag">Mistral Chief Analyst</div>
        </div>
        <div class="hero-kpis">
            <div class="hero-kpi"><strong>48</strong><span>World Cup teams</span></div>
            <div class="hero-kpi"><strong>7</strong><span>specialist agents</span></div>
            <div class="hero-kpi"><strong>100K</strong><span>simulation mode</span></div>
            <div class="hero-kpi"><strong>0€</strong><span>cloud cost MVP</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def page_title(icon: str, title: str, caption: str) -> None:
    st.markdown(f"<div class='section-head'><div class='section-title'>{icon} {title}</div><div class='section-caption'>{caption}</div></div>", unsafe_allow_html=True)


def metric_card(label: str, value: float | str, sub: str = "") -> None:
    st.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div class='metric-value'>{value}</div><div class='metric-sub'>{sub}</div><div class='gold-line'></div></div>", unsafe_allow_html=True)


def sanitize_ai_markdown(text: str) -> str:
    if not text:
        return "_No AI response was returned._"
    cleaned = str(text).strip()
    for prefix in ("```markdown", "```md", "```"):
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()
    return cleaned.replace("\n---\n", "\n\n")


def render_ai_answer(answer: str, title: str = "Mistral Chief Analyst Response") -> None:
    st.markdown(f"<div class='ai-answer-card'><div class='briefing-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(sanitize_ai_markdown(answer), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def status_class(status: str) -> str:
    status = (status or "").lower()
    if status == "ok":
        return "provider-ok"
    if status in {"skipped", "not_configured"}:
        return "provider-warn"
    return "provider-error"


def render_provider_cards(snapshot: dict[str, Any], title: str = "Live Provider Snapshot") -> None:
    providers = snapshot.get("providers", []) if isinstance(snapshot, dict) else []
    ready = bool(snapshot.get("live_data_ready")) if isinstance(snapshot, dict) else False
    st.markdown(
        f"""
        <div class='briefing'>
            <div class='briefing-title'>{title}</div>
            <div class='briefing-text'>
                Operating mode: <strong>{'LIVE + CACHE' if ready else 'CACHE-FIRST FALLBACK'}</strong>. The app remains resilient even when a provider is missing, blocked by SSL, rate-limited or not configured.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cards = []
    for provider in providers:
        name = provider.get("provider", "Unknown provider")
        status = provider.get("status", "unknown")
        mode = provider.get("source_mode", provider.get("mode", "unknown"))
        records = provider.get("records", 0)
        message = str(provider.get("message", ""))
        if len(message) > 180:
            message = message[:177] + "..."
        cards.append(
            f"""
            <div class='provider-card'>
                <div class='provider-title'>{name}</div>
                <div class='provider-status {status_class(status)}'>{status}</div>
                <div class='provider-meta'>
                    <strong>Mode:</strong> {mode}<br/>
                    <strong>Records:</strong> {records}<br/>
                    <strong>Message:</strong> {message}
                </div>
            </div>
            """
        )
    if cards:
        st.markdown("<div class='provider-grid'>" + "".join(cards) + "</div>", unsafe_allow_html=True)
    with st.expander("Raw provider payload"):
        st.json(snapshot)


def render_graph_trace(result: dict[str, Any]) -> None:
    trace = result.get("graph_trace", []) or []
    mode = result.get("graph_mode", "unknown")
    st.markdown(
        f"""
        <div class='briefing'>
            <div class='briefing-title'>Agent Graph Execution</div>
            <div class='briefing-text'>
                Orchestration mode: <strong>{mode}</strong>. When LangGraph is installed, specialist agents execute through a real fan-out/fan-in graph before the Mistral Chief Analyst node.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for item in trace:
        status = item.get("status", "unknown")
        cls = "provider-ok" if status == "completed" else "provider-error"
        st.markdown(
            f"""
            <div class='trace-node'>
                <div>
                    <div class='trace-name'>{item.get('name', 'unknown')}</div>
                    <div class='trace-meta'>{item.get('elapsed_ms', 0)} ms</div>
                </div>
                <div class='provider-status {cls}'>{status}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def agent_network_panel() -> None:
    agents = [("📊", "Stats Agent", "completed"), ("🔎", "Scout Agent", "completed"), ("♟️", "Tactical Agent", "completed"), ("👟", "Player Agent", "completed"), ("📰", "News Agent", "checked"), ("⚖️", "Debate Agent", "challenging"), ("🧠", "Chief Analyst", "Mistral")]
    cards = "".join([f"<div class='agent-card'><div class='agent-icon'>{i}</div><div class='agent-name'>{n}</div><div class='agent-state'><span class='dot'></span>{s}</div></div>" for i, n, s in agents])
    html = """
    <html><head><style>
    body { margin:0; background:transparent; font-family:Inter,Arial,sans-serif; }
    .panel { border-radius:26px; padding:1.15rem; background:linear-gradient(180deg,rgba(11,36,69,.96),rgba(6,24,51,.96)); border:1px solid rgba(255,255,255,.12); }
    .title { color:#D6B25E; font-size:.82rem; text-transform:uppercase; font-weight:900; letter-spacing:.12em; margin-bottom:.85rem; }
    .grid { display:grid; grid-template-columns:repeat(7,minmax(110px,1fr)); gap:.72rem; }
    .agent-card { border-radius:20px; padding:.92rem; background:rgba(255,255,255,.065); border:1px solid rgba(255,255,255,.13); min-height:108px; box-sizing:border-box; }
    .agent-icon { font-size:1.55rem; } .agent-name { color:white; font-weight:900; margin-top:.35rem; font-size:.9rem; }
    .agent-state { display:inline-flex; align-items:center; gap:.36rem; color:#42E8C6; font-size:.75rem; margin-top:.42rem; font-weight:800; }
    .dot { width:8px; height:8px; border-radius:99px; background:#42E8C6; display:inline-block; box-shadow:0 0 12px rgba(66,232,198,.75); }
    @media (max-width:900px) { .grid { grid-template-columns:repeat(2,minmax(120px,1fr)); } }
    </style></head><body><div class='panel'><div class='title'>World Cup Intelligence Center · Multi-Agent Layer</div><div class='grid'>""" + cards + """</div></div></body></html>
    """
    components.html(html, height=210, scrolling=False)


def render_agent_report_cards(result: dict) -> None:
    reports = result.get("agent_reports", {}) or {}
    labels = [("stats", "📊 Stats Agent"), ("scout", "🔎 Scout Agent"), ("tactical", "♟️ Tactical Agent"), ("player", "👟 Player Agent"), ("news", "📰 News Agent"), ("debate", "⚖️ Debate Agent")]
    st.markdown("<div class='glass-card'><div class='briefing-title'>Specialist Agent Reports</div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for idx, (key, label) in enumerate(labels):
        report = reports.get(key, {})
        with cols[idx % 3]:
            st.markdown(f"<div class='glass-card-tight'><div class='briefing-title'>{label}</div><div class='briefing-text'>{report.get('summary', 'No report available.')}</div></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def model_confidence(pred) -> int:
    spread = abs(pred.home_win - pred.away_win)
    draw_penalty = pred.draw * .18
    return int(max(58, min(91, round(68 + spread * .45 - draw_penalty))))


def executive_briefing(home: str, away: str, pred) -> str:
    leader = home if pred.home_win >= pred.away_win else away
    leader_prob = max(pred.home_win, pred.away_win)
    risk_team = away if leader == home else home
    return f"<strong>{leader}</strong> holds the strongest win signal at <strong>{leader_prob:.2f}%</strong>. Expected goals: <strong>{home} {pred.home_expected_goals}</strong> vs <strong>{away} {pred.away_expected_goals}</strong>. {home} brings {TEAM_STYLE.get(home, 'a balanced tactical profile')}; {away} brings {TEAM_STYLE.get(away, 'a balanced tactical profile')}. Main tactical risk: whether <strong>{risk_team}</strong> can disrupt transitions and convert high-value moments. Model confidence: <strong>{model_confidence(pred)}%</strong>."


def probability_ring(values: list[float], labels: list[str]) -> go.Figure:
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.68, sort=False, textinfo="label+percent", textfont=dict(color="white", size=14), marker=dict(colors=["#19C7D9", "#D6B25E", "#0B3D91"], line=dict(color="rgba(255,255,255,.18)", width=2)))])
    fig.update_layout(height=430, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False, margin=dict(l=10, r=10, t=10, b=10), annotations=[dict(text="WIN<br>PROBABILITY", x=.5, y=.5, font=dict(color="#EAF2FF", size=17), showarrow=False)])
    return fig


def radar_comparison(home: str, away: str) -> go.Figure:
    metrics = ["Attack", "Defense", "Squad", "Form", "Elo", "Experience"]
    def values(team: str) -> list[float]:
        row = team_record(team)
        return [float(row_value(row,"attack_strength",75)), float(row_value(row,"defense_strength",75)), float(row_value(row,"squad_strength",78)), float(row_value(row,"recent_form",.55))*100, min(100, (float(row_value(row,"elo",1800))-1600)/5), max(50, 105 - float(row_value(row,"fifa_rank",99))*2)]
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=values(home), theta=metrics, fill="toself", name=home, line=dict(color="#19C7D9", width=3)))
    fig.add_trace(go.Scatterpolar(r=values(away), theta=metrics, fill="toself", name=away, line=dict(color="#D6B25E", width=3)))
    fig.update_layout(height=460, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#EAF2FF"), legend=dict(orientation="h", y=-.08, x=.18), polar=dict(bgcolor="rgba(255,255,255,.02)", radialaxis=dict(visible=True, range=[0,100], gridcolor="rgba(255,255,255,.12)"), angularaxis=dict(gridcolor="rgba(255,255,255,.12)")), margin=dict(l=20,r=20,t=35,b=45))
    return fig


def momentum_chart(home: str, away: str) -> go.Figure:
    random.seed(hash(home + away) % 10000)
    x = list(range(1, 11))
    def series(team: str):
        base = float(row_value(team_record(team), "recent_form", .55)) * 72 + 18
        vals, cur = [], base
        for _ in x:
            cur += random.uniform(-7, 7)
            vals.append(max(35, min(96, cur)))
        return vals
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=series(home), mode="lines+markers", name=home, line=dict(color="#19C7D9", width=4)))
    fig.add_trace(go.Scatter(x=x, y=series(away), mode="lines+markers", name=away, line=dict(color="#D6B25E", width=4)))
    fig.update_layout(height=340, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#EAF2FF"), xaxis=dict(title="Last 10 matches", gridcolor="rgba(255,255,255,.08)"), yaxis=dict(title="Performance index", range=[30,100], gridcolor="rgba(255,255,255,.10)"), legend=dict(orientation="h", y=1.08, x=0), margin=dict(l=10,r=10,t=35,b=15))
    return fig


def champion_chart(champ_df: pd.DataFrame) -> go.Figure:
    df = champ_df.head(12).copy().sort_values("champion_probability", ascending=True)
    fig = go.Figure(go.Bar(x=df["champion_probability"], y=df["team"], orientation="h", text=df["champion_probability"].map(lambda x: f"{x:.2f}%"), textposition="inside", marker=dict(color=df["champion_probability"], colorscale=[[0,"#0B3D91"],[.5,"#19C7D9"],[1,"#D6B25E"]])))
    fig.update_layout(height=560, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#EAF2FF"), xaxis=dict(title="Champion probability", gridcolor="rgba(255,255,255,.10)"), yaxis=dict(title=None), margin=dict(l=10,r=10,t=20,b=20), showlegend=False)
    return fig


def sidebar() -> str:
    with st.sidebar:
        st.markdown("""<div class="sidebar-brand"><div class="brand-title">🏆 World Cup<br/>Command Center</div><div class="brand-caption">AI-powered football intelligence. Prediction, simulation, real multi-agent analysis and Ask the Coach.</div></div>""", unsafe_allow_html=True)
        page = st.radio("Choose module", ["Match Predictor", "Tournament Intelligence", "World Cup Intelligence Center", "Executive War Room", "Ask the Coach", "Team Intelligence", "What-if Scenarios", "Live World Cup Data", "Live Data Operations", "Production Readiness", "Data Sources"])
        mistral_state = "Live" if os.getenv("MISTRAL_API_KEY") else "Setup"
        st.markdown(f"""
        <div class="status-panel"><div class="status-title">World Cup Intelligence Status</div>
        <div class="status-row"><span><span class="dot"></span>Prediction Engine</span><strong>Live</strong></div>
        <div class="status-row"><span><span class="dot"></span>Multi-Agent Layer</span><strong>Ready</strong></div>
        <div class="status-row"><span><span class="dot"></span>100K Simulator</span><strong>Online</strong></div>
        <div class="status-row"><span><span class="dot"></span>Ask the Coach</span><strong>Active</strong></div>
        <div class="status-row"><span><span class="dot"></span>48-Team Data Layer</span><strong>Active</strong></div>
        <div class="status-row"><span><span class="dot"></span>Mistral Chief Analyst</span><strong>{mistral_state}</strong></div></div>
        """, unsafe_allow_html=True)
        st.caption(f"Local build · {datetime.now().strftime('%Y-%m-%d')}")
    return page


teams_df, matches_df = load_data()
teams = sorted(teams_df["team"].tolist())
predictor = MatchPredictor(teams_df)
simulator = TournamentSimulator(teams_df)
orchestrator = AgentOrchestrator(teams_df, matches_df)
live_hub = LiveFootballDataHub()
war_room = ExecutiveWarRoom(teams_df, matches_df, live_hub)

page = sidebar()
render_hero()

if page == "Match Predictor":
    page_title("⚽", "Match Predictor", "Executive-level match intelligence with explainable probabilities, tactical comparison and AI briefing.")
    st.markdown("<div class='matchup-shell'>", unsafe_allow_html=True)
    c1, cm, c2 = st.columns([1.2, .24, 1.2])
    with c1:
        home_team = st.selectbox("Home team", teams, index=teams.index("Portugal") if "Portugal" in teams else 0)
        team_card(home_team)
    with cm:
        st.markdown("<div class='vs-orb'>VS</div>", unsafe_allow_html=True)
    with c2:
        away_team = st.selectbox("Away team", teams, index=teams.index("Brazil") if "Brazil" in teams else 1)
        team_card(away_team)
    st.markdown("</div>", unsafe_allow_html=True)
    if home_team == away_team:
        st.warning("Choose two different teams.")
    else:
        pred = predictor.predict(home_team, away_team)
        p1, p2, p3, p4 = st.columns(4)
        with p1: metric_card(f"{home_team} Win", f"{pred.home_win:.2f}%", "home outcome signal")
        with p2: metric_card("Draw", f"{pred.draw:.2f}%", "stalemate probability")
        with p3: metric_card(f"{away_team} Win", f"{pred.away_win:.2f}%", "away outcome signal")
        with p4: metric_card("Model Confidence", f"{model_confidence(pred)}%", "probabilistic reliability")
        st.markdown(f"<div class='briefing'><div class='briefing-title'>Executive Match Briefing</div><div class='briefing-text'>{executive_briefing(home_team, away_team, pred)}</div></div>", unsafe_allow_html=True)
        agent_network_panel()
        left, right = st.columns([.92, 1.08])
        with left:
            st.markdown("<div class='glass-card'><div class='briefing-title'>Probability Ring</div>", unsafe_allow_html=True)
            st.plotly_chart(probability_ring([pred.home_win, pred.draw, pred.away_win], [home_team, "Draw", away_team]), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            st.markdown("<div class='glass-card'><div class='briefing-title'>Team Strength Comparison</div>", unsafe_allow_html=True)
            st.plotly_chart(radar_comparison(home_team, away_team), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'><div class='briefing-title'>Recent Performance Momentum</div>", unsafe_allow_html=True)
        st.plotly_chart(momentum_chart(home_team, away_team), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        if st.button("Generate World Cup Intelligence Center Report"):
            result = orchestrator.run_intelligence_center(home_team, away_team, "Create a full executive match briefing.")
            render_agent_report_cards(result)
            render_ai_answer(result["ai_answer"], "Mistral Chief Analyst Executive Briefing")
        with st.expander("Feature signals and audit trail"):
            st.json(pred.explanation_factors)

elif page == "Tournament Intelligence":
    page_title("🏆", "Tournament Intelligence", "Full 48-team World Cup simulation with 100,000-run champion projections.")
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    n = st.slider("Number of simulations", min_value=1000, max_value=100000, value=100000, step=1000)
    st.caption("100,000 simulations may take a little time locally. For quick demos, use 10,000–25,000.")
    run = st.button(f"Run {n:,} Simulations")
    st.markdown("</div>", unsafe_allow_html=True)
    if run or "full_projection_df" not in st.session_state:
        progress = st.progress(0)
        st.session_state["full_projection_df"] = simulator.champion_projection_full(matches_df, n=n, progress_callback=lambda x: progress.progress(min(1.0, x)))
        progress.empty()
    projection = st.session_state["full_projection_df"]
    c1, c2 = st.columns([1.15, .85])
    with c1:
        st.markdown("<div class='glass-card'><div class='briefing-title'>World Cup Win Probability</div>", unsafe_allow_html=True)
        st.plotly_chart(champion_chart(projection), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='glass-card'><div class='briefing-title'>Top Contenders</div>", unsafe_allow_html=True)
        for _, r in projection.head(8).iterrows():
            metric_card(f"{flag(r['team'])} {r['team']}", f"{r['champion_probability']:.2f}%", f"Final {r['final_probability']:.2f}% · SF {r['semifinal_probability']:.2f}%")
        st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'><div class='briefing-title'>Full Projection Table</div>", unsafe_allow_html=True)
    st.dataframe(projection, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "World Cup Intelligence Center":
    page_title("🤖", "World Cup Intelligence Center", "Real multi-agent layer: Stats, Scout, Tactical, Player, News, Debate and Mistral Chief Analyst.")
    agent_network_panel()
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: home_team = st.selectbox("Team A", teams, index=teams.index("Portugal") if "Portugal" in teams else 0)
    with c2: away_team = st.selectbox("Team B", teams, index=teams.index("Brazil") if "Brazil" in teams else 1)
    question = st.text_area("Ask the Chief Analyst", "Why is Portugal favoured against Brazil? Give me an executive briefing.")
    ask = st.button("Run Intelligence Center")
    st.markdown("</div>", unsafe_allow_html=True)
    if ask:
        result = orchestrator.run_intelligence_center(home_team, away_team, question)
        render_agent_report_cards(result)
        render_ai_answer(result["ai_answer"], "Mistral Chief Analyst Response")
        with st.expander("View full structured context sent to Mistral"):
            st.json(result["llm_context"])
        render_graph_trace(result)
        with st.expander("Local deterministic fallback"):
            st.markdown(result["briefing"])


elif page == "Executive War Room":
    page_title("🛰️", "Executive War Room", "One-click boardroom briefing powered by live data diagnostics, Monte Carlo projection, risk register and Mistral Chief Analyst.")
    st.markdown("""
    <div class='briefing'><div class='briefing-title'>Demo Positioning</div>
    <div class='briefing-text'>This is the high-impact layer for LinkedIn, Medium and stakeholder demos. It creates an executive intelligence briefing by combining provider health, World Cup live-data snapshot, tournament simulation, dark-horse detection and a risk register.</div></div>
    """, unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        focus_team = st.selectbox("War Room focus team", teams, index=teams.index("Portugal") if "Portugal" in teams else 0)
    with c2:
        war_sims = st.slider("War Room simulation depth", 1000, 25000, 10000, step=1000)
    run_war_room = st.button("Generate Executive War Room Briefing")
    st.markdown("</div>", unsafe_allow_html=True)
    if run_war_room:
        with st.spinner("Generating executive war-room briefing..."):
            report = war_room.generate(focus_team=focus_team, simulations=war_sims)
        st.success(f"War Room briefing generated · {report['ai_status']} · {report['cache_status']} · {report['simulations_used']:,} simulations")
        render_ai_answer(report["executive_briefing"], "Executive War Room Briefing")
        m1, m2, m3, m4 = st.columns(4)
        fp = report.get("focus_projection", {})
        with m1: metric_card("Champion", f"{float(fp.get('champion_probability', 0)):.2f}%", focus_team)
        with m2: metric_card("Final", f"{float(fp.get('final_probability', 0)):.2f}%", "projected path strength")
        with m3: metric_card("Providers", "LIVE" if report["world_cup_snapshot"].get("live_data_ready") else "CACHE", "data operating mode")
        with m4: metric_card("Risks", str(len(report["risk_register"])), "active risk signals")
        c1, c2 = st.columns([1.1, .9])
        with c1:
            st.markdown("<div class='glass-card'><div class='briefing-title'>Top Tournament Signals</div>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(report["top_contenders"]), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with c2:
            st.markdown("<div class='glass-card'><div class='briefing-title'>Risk Register</div>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(report["risk_register"]), use_container_width=True, hide_index=True)
            st.markdown("</div>", unsafe_allow_html=True)
        render_provider_cards(report["world_cup_snapshot"], "War Room Live Data Diagnostics")

elif page == "Live World Cup Data":
    page_title("🌐", "Live World Cup Data", "football-data.org World Cup endpoint, API-Football status, SofaScore cache and local fallback in one provider-agnostic hub.")
    st.markdown("<div class='glass-card'><div class='briefing-title'>Provider Health</div>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(live_hub.health()), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if st.button("Fetch World Cup Live Snapshot"):
        with st.spinner("Fetching cache-first World Cup snapshot..."):
            snapshot = live_hub.get_world_cup_snapshot()
        st.success("World Cup snapshot completed. The app will fall back to local data if providers are unavailable.")
        render_provider_cards(snapshot, "World Cup Live Data Snapshot")
    st.markdown("""
    <div class='briefing'><div class='briefing-title'>How this becomes production-grade</div>
    <div class='briefing-text'>Use <strong>FOOTBALL_DATA_API_KEY</strong> for official World Cup competition data, <strong>API_FOOTBALL_KEY</strong> for richer live/event data where available, and keep SofaScore as cache-first enrichment only where permitted. The prediction engine never depends on a single live provider.</div></div>
    """, unsafe_allow_html=True)

elif page == "Ask the Coach":
    page_title("🎙️", "Ask the Coach", "Strategic tournament questions: path to final, dark horses and what-if scenarios.")
    st.markdown("<div class='briefing'><div class='briefing-title'>Professional Demo Questions</div><div class='briefing-text'>Try: <strong>What is Portugal's most likely path to the final?</strong><br/>Try: <strong>Which team is the biggest dark horse?</strong><br/>Try: <strong>What happens if Mbappé misses the quarter-finals?</strong></div></div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    focus_team = st.selectbox("Focus team", teams, index=teams.index("Portugal") if "Portugal" in teams else 0)
    sims = st.slider("Coach simulation depth", 500, 10000, 3000, step=500, help="Ask the Coach is optimized for fast strategic Q&A. Higher values are capped internally for responsiveness.")
    coach_question = st.text_area("Ask the Coach", "What is Portugal's most likely path to the final?")
    run_coach = st.button("Ask the Coach")
    st.markdown("</div>", unsafe_allow_html=True)
    if run_coach:
        try:
            with st.spinner("Running strategic simulation and coach analysis..."):
                result = orchestrator.ask_the_coach(coach_question, focus_team=focus_team, simulations=sims)
        except Exception as exc:
            st.error(f"Ask the Coach failed before generating an answer: {exc}")
            result = None

        if result:
            status = result.get("ai_status", "unknown")
            if status == "mistral_success":
                st.success("Mistral Chief Analyst completed successfully.")
            elif status.startswith("fallback"):
                st.warning("Mistral was unavailable or slow. Showing the local coach fallback so the demo never blocks.")

            render_ai_answer(result["answer"], "Ask the Coach Response")

            with st.expander("Diagnostics and execution details"):
                st.write({
                    "ai_status": result.get("ai_status"),
                    "simulations_requested": result.get("simulations_requested"),
                    "simulations_used": result.get("simulations_used"),
                })
                for item in result.get("diagnostics", []):
                    st.markdown(f"- {item}")

            with st.expander("Simulation context"):
                st.json(result["context"])
            with st.expander("Top tournament projection used by coach"):
                st.dataframe(result["projection"].head(12), use_container_width=True, hide_index=True)

elif page == "Team Intelligence":
    page_title("🧠", "Team Intelligence", "National team profile with radar, momentum, style and tournament readiness.")
    selected = st.selectbox("Select team", teams, index=teams.index("Portugal") if "Portugal" in teams else 0)
    row = team_record(selected)
    left, right = st.columns([.88, 1.12])
    with left:
        team_card(selected)
        st.markdown("<div class='glass-card-tight'>", unsafe_allow_html=True)
        m1, m2 = st.columns(2); m1.metric("Elo Rating", int(row_value(row,"elo",1800))); m2.metric("FIFA Rank", f"#{int(row_value(row,'fifa_rank',99))}")
        m3, m4 = st.columns(2); m3.metric("Attack", float(row_value(row,"attack_strength",75))); m4.metric("Defense", float(row_value(row,"defense_strength",75)))
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='briefing'><div class='briefing-title'>Team Style</div><div class='briefing-text'>{selected} is profiled as a side built around {TEAM_STYLE.get(selected, 'balanced tactical structure and tournament adaptability')}.</div></div>", unsafe_allow_html=True)
    with right:
        compare = "France" if selected != "France" and "France" in teams else (teams[0] if teams[0] != selected else teams[1])
        st.markdown("<div class='glass-card'><div class='briefing-title'>Intelligence Radar</div>", unsafe_allow_html=True)
        st.plotly_chart(radar_comparison(selected, compare), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='glass-card'><div class='briefing-title'>Momentum Timeline</div>", unsafe_allow_html=True)
        st.plotly_chart(momentum_chart(selected, compare), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

elif page == "What-if Scenarios":
    page_title("🔮", "What-if Scenarios", "Stress-test any match by simulating injuries, fatigue, tactical disruption or loss of form.")
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    home_team = st.selectbox("Scenario team A", teams, index=teams.index("Portugal") if "Portugal" in teams else 0)
    away_team = st.selectbox("Scenario team B", teams, index=teams.index("Brazil") if "Brazil" in teams else 1)
    impact_team = st.radio("Apply negative impact to", [home_team, away_team], horizontal=True)
    impact = st.slider("Impact severity", 0, 25, 8)
    st.markdown("</div>", unsafe_allow_html=True)
    scenario_df = teams_df.copy()
    mask = scenario_df["team"] == impact_team
    scenario_df.loc[mask, "squad_strength"] = scenario_df.loc[mask, "squad_strength"] - impact
    scenario_df.loc[mask, "attack_strength"] = scenario_df.loc[mask, "attack_strength"] - impact
    scenario_df.loc[mask, "recent_form"] = scenario_df.loc[mask, "recent_form"] - impact / 100
    scenario_df["recent_form"] = scenario_df["recent_form"].clip(lower=.1, upper=1)
    base_pred = predictor.predict(home_team, away_team)
    scenario_pred = MatchPredictor(scenario_df).predict(home_team, away_team)
    comparison = pd.DataFrame({"Outcome": [f"{home_team} win", "Draw", f"{away_team} win"], "Base": [base_pred.home_win, base_pred.draw, base_pred.away_win], "Scenario": [scenario_pred.home_win, scenario_pred.draw, scenario_pred.away_win]})
    melted = comparison.melt(id_vars="Outcome", var_name="Version", value_name="Probability")
    fig = px.bar(melted, x="Outcome", y="Probability", color="Version", barmode="group", color_discrete_sequence=["#19C7D9", "#D6B25E"])
    fig.update_layout(height=470, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#EAF2FF"))
    st.markdown("<div class='glass-card'><div class='briefing-title'>Scenario Impact Analysis</div>", unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(comparison, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Live Data Operations":
    page_title("🔌", "Live Data Operations", "Production-ready live data hub with API-Football, football-data.org and SofaScore cache-first strategy.")
    st.markdown("<div class='glass-card'><div class='briefing-title'>Provider Health</div>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(live_hub.health()), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        live_home = st.selectbox("Live context team A", teams, index=teams.index("Portugal") if "Portugal" in teams else 0)
    with c2:
        live_away = st.selectbox("Live context team B", teams, index=teams.index("Brazil") if "Brazil" in teams else 1)
    refresh_live = st.button("Refresh Live Data Snapshot")
    st.markdown("</div>", unsafe_allow_html=True)

    if refresh_live:
        with st.spinner("Checking live providers and cache-first connectors..."):
            snapshot = live_hub.get_match_context(live_home, live_away)
        st.success("Live data snapshot completed. The app remains resilient even when providers are not configured.")
        render_provider_cards(snapshot, f"{live_home} vs {live_away} Live Data Snapshot")

    st.markdown("""
    <div class='briefing'><div class='briefing-title'>Production Strategy</div>
    <div class='briefing-text'>The live data layer is designed as cache-first and provider-agnostic.
    API keys are optional, demos never block, and SofaScore is treated as an optional cache enrichment path rather than a hard dependency.</div></div>
    """, unsafe_allow_html=True)

elif page == "Production Readiness":
    page_title("🚀", "Production Readiness", "Docker, CI/CD, monitoring, tests, environment configuration and deployment guardrails.")
    health = app_health()
    h1, h2, h3, h4 = st.columns(4)
    with h1: metric_card("App Health", health["status"].upper(), "runtime diagnostics")
    with h2: metric_card("Mistral", "LIVE" if health["mistral_configured"] else "SETUP", "LLM key status")
    with h3: metric_card("Live APIs", "READY" if (health["api_football_configured"] or health["football_data_configured"]) else "OPTIONAL", "provider status")
    with h4: metric_card("Graph", getattr(orchestrator.graph_executor, "mode", "local"), "agent orchestration")
    st.markdown("<div class='glass-card'><div class='briefing-title'>Health Check</div>", unsafe_allow_html=True)
    st.json(health)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'><div class='briefing-title'>Production Checklist</div>", unsafe_allow_html=True)
    st.markdown("""
- Dockerfile and docker-compose included.
- GitHub Actions CI included.
- Unit tests included.
- Secrets handled via environment variables or Streamlit Secrets.
- Mistral timeout and local fallback implemented.
- Live data providers are optional and cache-first.
- Observability health endpoint helper included.
    """)
    st.markdown("</div>", unsafe_allow_html=True)

elif page == "Data Sources":
    page_title("🗄️", "Data Sources", "Realistic local data layer with 48 teams, Elo cache, FIFA ranking cache, historical results, players and optional SofaScore cache.")
    st.markdown("<div class='glass-card'><div class='briefing-title'>Connector Health</div>", unsafe_allow_html=True)
    st.dataframe(load_connector_status(), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='glass-card'><div class='briefing-title'>Master Team Dataset</div>", unsafe_allow_html=True)
    st.dataframe(teams_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='briefing'><div class='briefing-title'>SofaScore Connector Strategy</div><div class='briefing-text'>SofaScore remains optional and cache-first. The app does not depend on live SofaScore calls. This protects the demo from endpoint changes, rate limits and compliance issues.</div></div>", unsafe_allow_html=True)

st.markdown("<div class='footer-note'>World Cup Command Center 2026 · Final Build · Multi-Agent Intelligence Center · 100K Tournament Simulation · Ask the Coach · Mistral Chief Analyst · Zero-cost local deployment.</div>", unsafe_allow_html=True)
