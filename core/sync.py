"""Phía bản local: đẩy bản ghi lịch sử lên server team (xem core/api_server.py)."""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from .i18n import t

# Không đi qua proxy công ty — server team nằm trong mạng LAN.
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def configured(settings: dict) -> bool:
    team = settings.get("team", {})
    return bool(team.get("server_url") and team.get("token"))


def _request(settings: dict, path: str, payload: dict | None = None, timeout: int = 30) -> dict:
    team = settings["team"]
    url = team["server_url"].rstrip("/") + path
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {team.get('token', '')}"})
    with _opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _error(e: Exception) -> str:
    if isinstance(e, urllib.error.HTTPError):
        try:
            return f"HTTP {e.code}: {json.loads(e.read()).get('error', '')}"
        except (json.JSONDecodeError, ValueError):
            return f"HTTP {e.code}"
    return t("Không kết nối được server team ({error})", error=e)


def ping(settings: dict) -> tuple[bool, str]:
    try:
        data = _request(settings, "/api/ping", timeout=8)
    except (urllib.error.URLError, OSError, ValueError) as e:
        return False, _error(e)
    if not data.get("user"):
        return False, t("Kết nối được server nhưng token không hợp lệ")
    return True, t("Đã kết nối — đăng nhập server với tài khoản '{user}'", user=data["user"])


def push(settings: dict, kind: str, title: str, summary: dict, files: dict[str, bytes] | None = None,
         note: str = "", status: str = "done", game: str = "l2m") -> tuple[bool, str]:
    payload = {
        "kind": kind, "title": title, "summary": summary, "note": note, "status": status, "game": game,
        "files": [{"name": n, "content_b64": base64.b64encode(b).decode("ascii")} for n, b in (files or {}).items()],
    }
    try:
        data = _request(settings, "/api/activities", json.loads(json.dumps(payload, default=str)))
    except (urllib.error.URLError, OSError, ValueError) as e:
        return False, _error(e)
    return True, f"#{data['id']}"
