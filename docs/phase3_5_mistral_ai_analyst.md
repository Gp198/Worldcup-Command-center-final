# Phase 3.5 — Mistral AI Analyst

This phase replaces the Gemini Analyst with a Mistral-powered analyst using the Mistral Chat Completions REST API.

## Environment variables

CMD:

```cmd
set MISTRAL_API_KEY=your_key_here
set MISTRAL_MODEL=mistral-medium-latest
streamlit run app.py
```

PowerShell:

```powershell
$env:MISTRAL_API_KEY="your_key_here"
$env:MISTRAL_MODEL="mistral-medium-latest"
streamlit run app.py
```

Optional for local corporate-network demos only:

```cmd
set MISTRAL_SSL_VERIFY=false
```

## Flow

The app builds a structured context from the prediction engine, Phase 2 data layer, local agents and knowledge snippets, then sends it to Mistral as the Chief Analyst of the World Cup Command Center.

If Mistral is unavailable or the key is missing, the deterministic local Chief Analyst remains available as fallback.
