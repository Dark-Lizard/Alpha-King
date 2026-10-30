"""Conservative WorldQuant BRAIN API client.

Uses documented BRAIN API workflows only. No browser-cookie extraction,
DOM scraping, private frontend endpoints, or credential persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests

API_ROOT = "https://api.worldquantbrain.com"


class BrainAPIError(RuntimeError):
    pass


@dataclass
class AuthResult:
    authenticated: bool
    persona_required: bool = False
    persona_url: str | None = None
    message: str = ""


class BrainClient:
    def __init__(self, timeout: int = 30):
        self.session = requests.Session()
        self.timeout = timeout
        self.authenticated = False

    def authenticate(self, email: str, password: str) -> AuthResult:
        """Start API authentication; return Persona hand-off when challenged."""
        response = self.session.post(
            f"{API_ROOT}/authentication",
            auth=(email, password),
            json={"expiry": 14400},
            timeout=self.timeout,
            allow_redirects=False,
        )
        if response.status_code in (200, 201, 204):
            self.authenticated = True
            return AuthResult(True, message="BRAIN API authentication succeeded.")
        if response.status_code == 401 and response.headers.get("WWW-Authenticate", "").lower().startswith("persona"):
            location = response.headers.get("Location")
            if not location:
                raise BrainAPIError("BRAIN requested Persona verification but did not return a Location header.")
            return AuthResult(
                False,
                persona_required=True,
                persona_url=urljoin(response.url, location),
                message="Complete the requested Persona verification in your browser, then return here.",
            )
        raise BrainAPIError(self._error_message(response, "Authentication failed"))

    def finish_persona(self, persona_url: str, email: str, password: str) -> AuthResult:
        """Complete the official browser Persona hand-off, then retry authentication."""
        # The user completes Persona in their normal browser. The documented
        # API hand-off is then POSTed with this API session before retrying auth.
        persona = self.session.post(persona_url, timeout=self.timeout, allow_redirects=True)
        if persona.status_code >= 400:
            raise BrainAPIError(self._error_message(persona, "Persona verification hand-off failed"))
        return self.authenticate(email, password)

    def check_session(self) -> bool:
        response = self.session.get(
            f"{API_ROOT}/authentication",
            headers={"Accept": "application/json;version=2.0"},
            timeout=self.timeout,
        )
        if response.status_code == 200:
            self.authenticated = True
        elif response.status_code == 204:
            self.authenticated = False
        elif response.status_code in (401, 403):
            self.authenticated = False
        else:
            raise BrainAPIError(self._error_message(response, "Could not verify BRAIN session"))
        return self.authenticated

    def get_alpha(self, alpha_id: str) -> Any:
        return self._request("GET", f"/alphas/{alpha_id}").json()

    def get_alpha_pnl(self, alpha_id: str) -> Any:
        return self._request("GET", f"/alphas/{alpha_id}/recordsets/pnl").json()

    def _request(self, method: str, path_or_url: str, *, version: str = "2.0", **kwargs):
        if not self.authenticated:
            raise BrainAPIError("Connect to BRAIN before making API requests.")
        url = path_or_url if path_or_url.startswith(("https://", "http://")) else urljoin(API_ROOT + "/", path_or_url.lstrip("/"))
        headers = dict(kwargs.pop("headers", {}) or {})
        headers.setdefault("Accept", f"application/json;version={version}")
        response = self.session.request(
            method, url, headers=headers, timeout=self.timeout, **kwargs
        )
        if response.status_code in (401, 403):
            self.authenticated = False
            raise BrainAPIError(f"BRAIN rejected the request ({response.status_code}). Your session may have expired or your account may lack permission.")
        if response.status_code >= 400:
            raise BrainAPIError(self._error_message(response, f"BRAIN API request failed ({response.status_code})"))
        return response

    @staticmethod
    def _error_message(response, fallback: str) -> str:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:500]
        return f"{fallback}: {detail}"

    def get_operators(self) -> Any:
        return self._request("GET", "/operators").json()

    def get_data_fields(self, params: dict | None = None) -> Any:
        return self._request("GET", "/data-fields", params=params or {}).json()

    def submit_simulation(self, expression: str, settings: dict) -> dict:
        payload = {"type": "REGULAR", "settings": settings, "regular": expression}
        response = self._request("POST", "/simulations", json=payload, version="2.0")
        location = response.headers.get("Location")
        body = None
        try:
            body = response.json()
        except Exception:
            pass
        return {
            "status_code": response.status_code,
            "location": urljoin(response.url, location) if location else None,
            "body": body,
            "retry_after": response.headers.get("Retry-After"),
        }

    def poll_simulation(self, location: str) -> Any:
        # The Location value is returned by BRAIN itself and is polled unchanged.
        return self._request("GET", location).json()
