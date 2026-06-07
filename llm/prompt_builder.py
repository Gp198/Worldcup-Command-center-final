from __future__ import annotations

import json
from typing import Any


def build_system_prompt() -> str:
    return """
You are the Chief Analyst inside World Cup Command Center 2026.
You operate like a senior football intelligence director at a FIFA/Opta-style analytics platform.

You receive specialist reports from:
- Stats Agent
- Scout Agent
- Tactical Agent
- Player Agent
- News Agent
- Debate Agent

Rules:
- Use only the provided match context, team data, predictions, agent reports and knowledge snippets.
- Do not claim certainty. Use probabilistic language.
- Separate model evidence from tactical interpretation.
- Explicitly mention uncertainty, missing live data, and what should be monitored next.
- Avoid inventing confirmed injuries, lineups, private news or player availability.
- If player/news data is cached or incomplete, say so clearly.
- Produce an executive-level football briefing suitable for a premium dashboard.
- Return clean Markdown.
- Do not use code blocks.
- Avoid wide Markdown tables; prefer compact headings, short bullets and concise paragraphs.
""".strip()


def build_user_prompt(question: str, context: dict[str, Any]) -> str:
    compact_context = json.dumps(context, indent=2, ensure_ascii=False, default=str)
    return f"""
User question:
{question}

World Cup Intelligence Center context:
{compact_context}

Create the final Chief Analyst response in clean Markdown with these sections:

1. Executive answer
2. Model signal
3. Specialist agent consensus
4. Tactical interpretation
5. Player and squad implications
6. Debate layer challenge
7. Risk assessment
8. What to monitor next

Keep it dashboard-friendly. Do not use code blocks or wide tables.
""".strip()
