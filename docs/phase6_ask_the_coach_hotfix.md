# Ask the Coach Hotfix

This build makes the Ask the Coach module demo-safe:

- Mistral calls have a short timeout via `MISTRAL_TIMEOUT_SECONDS`.
- If Mistral is slow/unavailable, the local deterministic coach fallback is returned.
- Ask-the-Coach simulations are capped internally to keep the UI responsive.
- Projection/path/what-if simulations are cached in memory.
- The UI now shows diagnostics, simulation depth used, and AI status.

Recommended local command:

```cmd
set MISTRAL_API_KEY=your_key
set MISTRAL_MODEL=mistral-medium-latest
set MISTRAL_TIMEOUT_SECONDS=12
streamlit run app.py
```
