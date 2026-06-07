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
class MistralConfig:
    api_key: str | None = None
    model: str = "mistral-medium-latest"
    temperature: float = 0.35
    max_tokens: int = 1200
    timeout_seconds: int = 12
    api_url: str = "https://api.mistral.ai/v1/chat/completions"


class MistralClient:
    """Mistral REST client for the World Cup Command Center.

    Environment variables:
      - MISTRAL_API_KEY, required for real AI Analyst calls
      - MISTRAL_MODEL, optional. Default: mistral-medium-latest
      - MISTRAL_SSL_VERIFY, optional. Use false only for local demos behind
        corporate SSL inspection when you get CERTIFICATE_VERIFY_FAILED.
    """

    def __init__(self, config: MistralConfig | None = None):
        api_key = os.getenv("MISTRAL_API_KEY")
        model = os.getenv("MISTRAL_MODEL", "mistral-medium-latest")
        timeout_raw = os.getenv("MISTRAL_TIMEOUT_SECONDS", "12")
        try:
            timeout_seconds = max(3, min(60, int(timeout_raw)))
        except ValueError:
            timeout_seconds = 12
        self.config = config or MistralConfig(api_key=api_key, model=model, timeout_seconds=timeout_seconds)

    @property
    def is_configured(self) -> bool:
        return bool(self.config.api_key)

    @property
    def ssl_verify(self) -> bool:
        raw = os.getenv("MISTRAL_SSL_VERIFY", "true").strip().lower()
        return raw not in {"0", "false", "no", "off"}

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if not self.is_configured:
            return self._missing_key_response()

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = requests.post(
                self.config.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=self.config.timeout_seconds,
                verify=self.ssl_verify,
            )

            if response.status_code >= 400:
                return self._api_error_response(response.status_code, response.text)

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return "### Mistral Analyst returned no choices\n\nTry again with a more specific question."

            message = choices[0].get("message", {})
            text = message.get("content", "")
            if isinstance(text, list):
                text = "\n".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in text)
            text = str(text).strip()
            if text:
                return text
            return "### Mistral Analyst returned an empty response\n\nTry asking again with a more specific question."

        except requests.exceptions.SSLError as exc:
            return (
                "### Mistral Analyst unavailable\n\n"
                "The Mistral request failed because Windows/Python could not validate the SSL certificate. "
                "This often happens on corporate networks, VPNs or proxies with SSL inspection.\n\n"
                "For a local demo only, run:\n\n"
                "```cmd\n"
                "set MISTRAL_SSL_VERIFY=false\n"
                "streamlit run app.py\n"
                "```\n\n"
                "Better production fix: install your corporate root certificate in the Python/requests trust store.\n\n"
                f"Technical detail: `{exc}`"
            )
        except requests.exceptions.Timeout:
            return (
                "### Mistral Analyst timeout\n\n"
                "The Mistral request took too long. Check your connection or try again."
            )
        except Exception as exc:
            return (
                "### Mistral Analyst unavailable\n\n"
                f"Could not call Mistral: `{exc}`.\n\n"
                "Check your internet connection, `MISTRAL_API_KEY`, and selected `MISTRAL_MODEL`. "
                "The local Chief Analyst fallback remains available below."
            )

    @staticmethod
    def _api_error_response(status_code: int, text: str) -> str:
        safe_text = text[:900]
        return (
            "### Mistral API returned an error\n\n"
            f"Status code: `{status_code}`\n\n"
            f"Response: `{safe_text}`\n\n"
            "Check whether the API key is valid, the selected Mistral model is available, and your account has quota."
        )

    @staticmethod
    def _missing_key_response() -> str:
        return (
            "### Mistral Analyst not configured\n\n"
            "Create a Mistral API key and set it before running Streamlit.\n\n"
            "For CMD:\n\n"
            "```cmd\n"
            "set MISTRAL_API_KEY=your_api_key_here\n"
            "set MISTRAL_MODEL=mistral-medium-latest\n"
            "streamlit run app.py\n"
            "```\n\n"
            "For PowerShell:\n\n"
            "```powershell\n"
            "$env:MISTRAL_API_KEY=\"your_api_key_here\"\n"
            "$env:MISTRAL_MODEL=\"mistral-medium-latest\"\n"
            "streamlit run app.py\n"
            "```\n\n"
            "Without the key, the app continues using the local Chief Analyst fallback."
        )
