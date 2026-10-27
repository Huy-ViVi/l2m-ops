"""Gói agent tải từ website: code app + data/local.json đã điền sẵn địa chỉ CSDL chung và tài khoản người tải.

Người dùng chỉ cần giải nén rồi nháy đúp agent.bat (tự cài Python + thư viện — tools/setup.ps1). Website và agent
cùng tính code_version() trên cùng danh sách file, nên website biết agent nào đang chạy bản cũ.
"""
from __future__ import annotations

import functools
import hashlib
import io
import json
import zipfile
from pathlib import Path

from . import config

CODE_DIRS = ("core", "ui", "views", "automation", "tools", "resources")
CODE_FILES = ("app.py", "requirements.txt", "run.bat", "run-team.bat", "agent.bat", "README.md")
SKIP_SUFFIXES = (".pyc", ".pyo")


def code_files(root: Path = config.APP_ROOT) -> list[Path]:
    files = [root / f for f in CODE_FILES if (root / f).is_file()]
    for d in CODE_DIRS:
        if (root / d).is_dir():
            files += [p for p in (root / d).rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts and p.suffix not in SKIP_SUFFIXES]
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


@functools.lru_cache(maxsize=4)
def code_version(root: Path = config.APP_ROOT) -> str:
    """Mã ngắn của bản code (đổi khi bất kỳ file code nào đổi)."""
    h = hashlib.sha256()
    for p in code_files(root):
        h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:12]


def agent_zip(username: str, database_url: str, root: Path = config.APP_ROOT) -> bytes:
    """Zip cài agent cho một tài khoản. Chứa mật khẩu CSDL: chỉ đưa cho đúng người đã đăng nhập."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in code_files(root):
            z.write(p, p.relative_to(root).as_posix())
        z.writestr("data/local.json", json.dumps({"database_url": database_url, "agent_user": username}, ensure_ascii=False, indent=2))
        z.writestr("CHAY-AGENT.txt", (
            "L2M Ops Agent\r\n\r\n"
            "1. Bat VPN cong ty.\r\n"
            "2. Nhay dup agent.bat. Lan dau tu cai Python + thu vien (vai phut, can Internet).\r\n"
            "3. Giu cua so agent mo trong luc dung website.\r\n\r\n"
            f"Agent nay chay lenh cua tai khoan '{username}'. Khong gui thu muc nay cho nguoi khac\r\n"
            "(co san dia chi CSDL chung va tai khoan cua ban).\r\n"))
    return buf.getvalue()
