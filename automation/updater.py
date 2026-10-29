"""Agent tự cập nhật khi website có bản code mới — người dùng không phải tải zip, giải nén hay bấm gì.

Website ghi bản code của nó vào CSDL (bảng agents, dòng ~website). Agent thấy khác bản của mình thì:
1. Tải code từ kho GitHub của website (UPDATE_URL, chỉ đọc, không cần tài khoản) vào data/update/.
2. Chỉ dùng khi code vừa tải đúng là bản website đang chạy (bundle.version_of): ai sửa được CSDL cũng không bắt agent
   chạy code lạ được — code luôn lấy từ GitHub, CSDL chỉ nói "bản nào".
3. Chép đè các file code (bundle.code_files) lên thư mục agent, xoá file code không còn trong bản mới. Không đụng data/
   (địa chỉ CSDL, tài khoản, phiên SSO), .venv, .python.
4. Khởi động lại: một tiến trình PowerShell ẩn chờ agent cũ thoát, cài thêm thư viện nếu requirements.txt đổi
   (tools/setup.ps1), rồi bật agent chạy ngầm bằng code mới.
Chỉ chép đè thư mục cài từ zip của website (data/local.json có auto_update) — thư mục code đang phát triển thì không.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from core import bundle, config

UPDATE_URL = "https://github.com/huy-vivi/l2m-ops/archive/HEAD.zip"  # kho website deploy (Streamlit Cloud)
MAX_BYTES = 50_000_000
TIMEOUT = 60


def source_url() -> str:
    return os.environ.get("L2M_UPDATE_URL") or UPDATE_URL  # test: máy chủ HTTP tạm


def enabled() -> bool:
    return bool(config.load_local().get("auto_update"))


def _download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp, open(dest, "wb") as f:  # noqa: S310 — chỉ https cố định / test
        size = 0
        while chunk := resp.read(1 << 16):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError(f"file cập nhật quá lớn (> {MAX_BYTES // 1_000_000} MB)")
            f.write(chunk)


def _extract(zip_path: Path, dest: Path) -> Path:
    """Giải nén an toàn (không cho đường dẫn thoát ra ngoài dest); trả về thư mục chứa app.py (zip GitHub có một thư mục gốc)."""
    base = dest.resolve()
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            target = (dest / name).resolve()
            if target != base and base not in target.parents:
                raise ValueError(f"đường dẫn lạ trong file cập nhật: {name}")
        z.extractall(dest)
    roots = [p.parent for p in dest.glob("*/app.py")] + ([dest] if (dest / "app.py").is_file() else [])
    if len(roots) != 1:
        raise ValueError("file cập nhật không có code app")
    return roots[0]


def fetch(target: str, url: str | None = None) -> Path | None:
    """Tải code về data/update/; trả về thư mục code nếu đúng bản target, None nếu GitHub chưa có đúng bản đó
    (vd website chưa deploy xong, hoặc kho đã có commit mới hơn website)."""
    work = config.DATA_DIR / "update"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    _download(url or source_url(), work / "code.zip")
    root = _extract(work / "code.zip", work / "src")
    return root if bundle.version_of(root) == target else None


def apply(new_root: Path, app_root: Path = config.APP_ROOT) -> None:
    """Chép đè code mới lên thư mục agent (từng file: ghi tạm rồi đổi tên), xoá file code không còn trong bản mới."""
    new = {p.relative_to(new_root).as_posix(): p for p in bundle.code_files(new_root)}
    old = {p.relative_to(app_root).as_posix() for p in bundle.code_files(app_root)}
    for rel, src in new.items():
        dst = app_root / rel
        data = src.read_bytes()
        if dst.is_file() and dst.read_bytes() == data:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".update")
        tmp.write_bytes(data)
        os.replace(tmp, dst)
    for rel in old - new.keys():
        (app_root / rel).unlink(missing_ok=True)


def _ps(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def relaunch_script(pid: int, app_root: Path, pythonw: str, agent_py: Path, setup: bool) -> str:
    """Lệnh PowerShell: chờ agent cũ (pid) thoát, cài thư viện nếu cần, bật agent chạy ngầm bằng code mới."""
    lines = ["$ErrorActionPreference = 'SilentlyContinue'", f"Wait-Process -Id {int(pid)} -Timeout 120"]
    if setup:  # requirements.txt đổi thì cài thêm; không đổi thì setup.ps1 xong ngay
        log = config.DATA_DIR / "update-setup.log"
        lines.append(f"& {_ps(str(app_root / 'tools' / 'setup.ps1'))} *> {_ps(str(log))}")
    args = '-X utf8 "' + str(agent_py) + '" --background'
    lines.append(f"Start-Process -FilePath {_ps(pythonw)} -ArgumentList {_ps(args)} -WorkingDirectory {_ps(str(app_root))}")
    return "\n".join(lines)


def relaunch(version: str, pythonw: str, agent_py: Path, app_root: Path = config.APP_ROOT) -> None:
    """Tách một tiến trình PowerShell ẩn bật lại agent sau khi tiến trình này thoát."""
    setup = (app_root / ".venv") in Path(sys.executable).resolve().parents  # agent dùng .venv của chính thư mục này
    script = relaunch_script(os.getpid(), app_root, pythonw, agent_py, setup)
    env = {**os.environ, "PYTHONUTF8": "1", "L2M_AGENT_UPDATED": version}
    args = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", script]
    flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    kw = dict(cwd=app_root, env=env, close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
              stderr=subprocess.DEVNULL)
    try:
        subprocess.Popen(args, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kw)
    except OSError:  # tiến trình đang chạy trong job không cho tách
        subprocess.Popen(args, creationflags=flags, **kw)
