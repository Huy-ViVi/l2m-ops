"""API nhỏ (thư viện chuẩn) chạy kèm server team để bản local của thành viên đẩy kết quả lên.

    GET  /api/ping                      -> kiểm tra kết nối (+ token hợp lệ không)
    POST /api/activities  (Bearer token) -> tạo bản ghi lịch sử kèm file

Token do admin cấp ở trang Thành viên; chỉ vai trò Admin/Thành viên được đẩy dữ liệu.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import store

MAX_BODY = 30 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "L2MOps/1"

    def log_message(self, fmt, *args):  # không in log mỗi request ra console
        pass

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _user(self) -> dict | None:
        auth = self.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        return store.user_by_token(token)

    def do_GET(self):
        if self.path != "/api/ping":
            return self._send(404, {"ok": False, "error": "Không có endpoint này"})
        user = self._user()
        self._send(200, {"ok": True, "user": user["username"] if user else None})

    def do_POST(self):
        if self.path != "/api/activities":
            return self._send(404, {"ok": False, "error": "Không có endpoint này"})
        user = self._user()
        if not user:
            return self._send(401, {"ok": False, "error": "Token không hợp lệ hoặc tài khoản đã bị khoá"})
        if user["role"] not in ("admin", "member"):
            return self._send(403, {"ok": False, "error": "Tài khoản 'Chỉ xem' không được đẩy dữ liệu"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self._send(413, {"ok": False, "error": "Dữ liệu rỗng hoặc quá lớn (tối đa 30MB)"})
        try:
            data = json.loads(self.rfile.read(length))
            files = {f["name"]: base64.b64decode(f["content_b64"]) for f in data.get("files", [])}
        except (json.JSONDecodeError, KeyError, TypeError, binascii.Error):
            return self._send(400, {"ok": False, "error": "Dữ liệu không hợp lệ"})
        kind = data.get("kind")
        if kind not in store.KINDS:
            return self._send(400, {"ok": False, "error": f"Loại hoạt động không hợp lệ: {kind}"})
        status = data.get("status") if data.get("status") in store.STATUSES else "done"
        game = re.sub(r"[^a-z0-9]", "", str(data.get("game") or "l2m").lower())[:16] or "l2m"
        aid = store.add_activity(kind, str(data.get("title", ""))[:300], data.get("summary") or {}, user["username"],
                                 files, note=str(data.get("note", "")), status=status, source=f"local:{user['username']}",
                                 game=game)
        self._send(201, {"ok": True, "id": aid})


def start(host: str, port: int) -> ThreadingHTTPServer:
    store.init()
    srv = ThreadingHTTPServer((host, port), Handler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True, name="l2m-api").start()
    return srv
