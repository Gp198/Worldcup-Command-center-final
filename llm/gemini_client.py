from __future__ import annotations

import json
import os
from dataclasses import dataclass

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


@dataclass
class GeminiConfig:
    api_key: str | None = None
    model: str = "gemini-2.5-flash"
    temperature: float = 0.35
    max_output_tokens: int = 1200
    timeout_seconds: int = 45


class GeminiClient:
    """Gemini REST client optimized for local demos and corporate networks.

    Environment variables:
      - GEMINI_API_KEY or GOOGLE_API_KEY
      - GEMINI_MODEL, optional. Default: gemini-2.5-flash
      - GEMINI_SSL_VERIFY, optional. Use false only for local demos behind
        corporate SSL inspection when you get CERTIFICATE_VERIFY_FAILED.
    """

    def __init__(self, config: GeminiConfig | None = None):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.config = config or GeminiConfig(api_key=api_key, model=model)

    @property
    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    @property
    def ssl_verify(self) -> bool:
        raw = os.getenv("GEMINI_SSL_VERIFY", "true").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured:
            return self._missing_key_response()

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.config.model}:generateContent?key={self.config.api_key}"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            "generationConfig": {
                "temperature": self.config.temperature,
                "maxOutputTokens": self.config.max_output_tokens,
            },
        }

        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=self.config.timeout_seconds,
                verify=self.ssl_verify,
            )

            if response.status_code >= 400:
                return self._api_error_response(response.status_code, response.text)

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return "### Gemini Analyst returned no candidates\n\nTry again with a more specific question."

            parts = candidates[0].get("content", {}).get("parts", [])
            text = "\n".join(part.get("text", "") for part in parts).strip()
            if text:
                return text
            return "### Gemini Analyst returned an empty response\n\nTry asking again with a more specific question."

        except requests.exceptions.SSLError as exc:
            return (
                "### Gemini Analyst unavailable\n\n"
                "The Gemini request failed because Windows/Python could not validate the SSL certificate. "
                "This often happens on corporate networks, VPNs or proxies with SSL inspection.\n\n"
                "For a local demo only, run:\n\n"
                "```cmd\n"
                "set GEMINI_SSL_VERIFY=false\n"
                "streamlit run app.py\n"
                "```\n\n"
                "Better production fix: install your corporate root certificate in the Python/requests trust store.\n\n"
                f"Technical detail: `{exc}`"
            )
        except requests.exceptions.Timeout:
            return (
                "### Gemini Analyst timeout\n\n"
                "The Gemini request took too long. Check your connection or try again."
            )
        except Exception as exc:
            return (
                "### Gemini Analyst unavailable\n\n"
                f"Could not call Gemini: `{exc}`.\n\n"
                "Check your internet connection, `GEMINI_API_KEY`, and selected `GEMINI_MODEL`. "
                "The local Chief Analyst fallback remains available below."
            )

    @staticmethod
    def _api_error_response(status_code: int, text: str) -> str:
        safe_text = text[:900]
        return (
            "### Gemini API returned an error\n\n"
            f"Status code: `{status_code}`\n\n"
            f"Response: `{safe_text}`\n\n"
            "Check whether the API key is valid, the Gemini API is enabled, and the selected model is available."
        )

    @staticmethod
    def _missing_key_response() -> str:
        return (
            "### Gemini Analyst not configured\n\n"
            "Create a free API key in Google AI Studio and set it before running Streamlit.\n\n"
            "For CMD:\n\n"
            "```cmd\n"
            "set GEMINI_API_KEY=your_api_key_here\n"
            "set GEMINI_MODEL=gemini-2.5-flash\n"
            "streamlit run app.py\n"
            "```\n\n"
            "For PowerShell:\n\n"
            "```powershell\n"
            "$env:GEMINI_API_KEY=\"your_api_key_here\"\n"
            "$env:GEMINI_MODEL=\"gemini-2.5-flash\"\n"
            "streamlit run app.py\n"
            "```\n\n"
            "Without the key, the app continues using the local Chief Analyst fallback."
        )
