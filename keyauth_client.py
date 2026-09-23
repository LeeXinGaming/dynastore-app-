from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from typing import Any


class KeyAuthError(RuntimeError):
    pass


class KeyAuthClient:
    endpoint = "https://keyauth.win/api/1.3/"

    def __init__(self, name: str, owner_id: str, version: str) -> None:
        self.name, self.owner_id, self.version = name, owner_id, version
        self.session_id = ""
        self.user: dict[str, Any] = {}
        self.hwid = self._get_hwid()

    @staticmethod
    def _get_hwid() -> str:
        """Return the Windows user SID used by the official KeyAuth Python client."""
        if os.name == "nt":
            try:
                output = subprocess.check_output(
                    ["whoami", "/user"], text=True, encoding="utf-8", errors="ignore",
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=8,
                )
                match = re.search(r"S-\d+(?:-\d+)+", output)
                if match:
                    return match.group(0)
            except (OSError, subprocess.SubprocessError):
                pass
        # Stable fallback for environments where the SID command is unavailable.
        identity = f"{os.environ.get('COMPUTERNAME', '')}|{os.environ.get('USERNAME', '')}"
        import hashlib
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def _request(self, **parameters: str) -> dict[str, Any]:
        parameters.update(name=self.name, ownerid=self.owner_id)
        request = urllib.request.Request(
            self.endpoint + "?" + urllib.parse.urlencode(parameters),
            headers={"User-Agent": "DYNA-STORE/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise KeyAuthError(f"Could not contact KeyAuth: {exc}") from exc
        if not isinstance(result, dict):
            raise KeyAuthError("KeyAuth returned an invalid response.")
        if not result.get("success"):
            raise KeyAuthError(str(result.get("message", "Authentication failed.")))
        return result

    def initialize(self) -> dict[str, Any]:
        result = self._request(type="init", ver=self.version, hash="undefined")
        self.session_id = str(result.get("sessionid", ""))
        if not self.session_id:
            raise KeyAuthError("KeyAuth did not return a session ID.")
        return result

    def _ready(self) -> None:
        if not self.session_id:
            self.initialize()

    def login(self, username: str, password: str, code: str = "") -> dict[str, Any]:
        self._ready()
        result = self._request(**{"type": "login", "username": username, "pass": password,
                                  "code": code, "hwid": self.hwid, "sessionid": self.session_id})
        self.user = dict(result.get("info") or {})
        return result

    def register(self, username: str, password: str, key: str, email: str = "") -> dict[str, Any]:
        self._ready()
        result = self._request(**{"type": "register", "username": username, "pass": password,
                                  "key": key, "email": email, "hwid": self.hwid,
                                  "sessionid": self.session_id})
        self.user = dict(result.get("info") or {})
        return result

    def license(self, key: str, code: str = "") -> dict[str, Any]:
        self._ready()
        result = self._request(type="license", key=key, code=code, hwid=self.hwid,
                               sessionid=self.session_id)
        self.user = dict(result.get("info") or {})
        return result

    def logout(self) -> None:
        if self.session_id:
            try:
                self._request(type="logout", sessionid=self.session_id)
            finally:
                self.session_id, self.user = "", {}
