# Phase 3.5 — Gemini Free API AI Analyst

This phase replaces the Groq Analyst with a Gemini-powered analyst using the official Google Gen AI SDK.

## What changed

- Added `llm/gemini_client.py`
- Added `llm/gemini_analyst.py`
- Updated the `AgentOrchestrator` with `ask_gemini_analyst(...)`
- Updated the Streamlit AI Analyst page from Groq to Gemini
- Added `google-genai` to `requirements.txt`
- The local Chief Analyst fallback remains available when no API key is configured

## Setup

Install dependencies:

```powershell
pip install -r requirements.txt
```

Set your Gemini key:

```powershell
$env:GEMINI_API_KEY="your_api_key_here"
$env:GEMINI_MODEL="gemini-2.5-flash"
streamlit run app.py
```

You can also use `GOOGLE_API_KEY` instead of `GEMINI_API_KEY`.

## How it works

The app builds a structured football intelligence context containing:

- match prediction probabilities
- expected goals
- Elo ratings
- FIFA ranking
- recent form
- attack / defense / squad strength
- scout findings
- tactical findings
- news/risk findings
- knowledge base snippets
- local Chief Analyst fallback

Gemini receives that context and answers as the Chief Analyst of the World Cup Command Center.

## Recommended demo question

```text
Why is Portugal favoured against Brazil?
```


## Local RAG layer

This version also upgrades retrieval from keyword overlap to a local TF-IDF vector retriever:

- `rag/vector_knowledge_retriever.py`
- zero-cost
- no external vector database required
- compatible with the existing agent interface

This is intentionally lightweight for local development. Later, replace it with ChromaDB, FAISS or Azure AI Search without changing the agent contracts.
