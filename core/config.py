"""Cấu hình app: đọc/ghi data/settings.json, env var được ưu tiên hơn (dùng khi deploy lên web).

Thông số riêng của từng game (app group trên NC tool, tiền tố Store Product Key, URL MyTool...) nằm trong
settings["games"][<game id>]. Lineage2M SEA ('l2m') có sẵn; admin thêm game khác ở trang Cài đặt.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
# Giờ của team (Việt Nam, không đổi giờ mùa hè). Website trên Streamlit Cloud chạy giờ UTC, nên mọi mốc thời gian
# ghi vào CSDL chung / hiển thị đều lấy theo giờ này cho khớp với bản local.
TEAM_TZ = timezone(timedelta(hours=7))


def now() -> datetime:
    return datetime.now(TEAM_TZ).replace(tzinfo=None)


def today() -> date:
    return now().date()


RESOURCES_DIR = APP_ROOT / "resources"
DATA_DIR = Path(os.environ.get("L2M_DATA_DIR", APP_ROOT / "data"))
SETTINGS_PATH = DATA_DIR / "settings.json"
MASTER_DIR = DATA_DIR / "master"
WORK_DIR = DATA_DIR / "work"
BROWSER_PROFILE_DIR = DATA_DIR / "browser-profile"
BROWSERS = {"msedge": "Microsoft Edge", "chrome": "Google Chrome", "chromium": "Chromium (Playwright)"}  # kênh Playwright
TEAM_BROWSER = "team"  # người dùng chọn hẳn "Theo team" (khác '' = chưa chọn: website lấy theo trình duyệt đang mở nó)

MARKETS = ["SG", "ID", "PH", "MY", "TH", "VN"]
DEFAULT_GAME = "l2m"


def blank_game(name: str = "") -> dict:
    return {
        "name": name,
        "nc_app_group": "",
        "nc_app_group_label": "",
        "store_key_prefix": "",
        "mytool_search_order": {"SEA": "", "VN": ""},
        "mytool_sold_package": {m: "" for m in MARKETS},
    }


DEFAULTS: dict = {
    "ai": {
        "provider": "claude",
        "claude": {"api_key": "", "model": "claude-opus-5-5"},
        "openai": {"api_key": "", "model": "gpt-5"},
        "gemini": {"api_key": "", "model": "gemini-2.5-flash"},
        "gateway": {"api_key": "", "model": "", "base_url": ""},
    },
    "output_root": str(APP_ROOT),
    "automation": {
        "browser_channel": "msedge",
        "nc_base_url": "https://rc-ncv-billingadmin.ncsoft.net",
        "submit_mode": "manual",
    },
    "default_game": DEFAULT_GAME,
    "default_lang": "vi",  # ngôn ngữ giao diện khi trình duyệt chưa chọn (vi / en)
    "games": {
        DEFAULT_GAME: {
            **blank_game("Lineage2M SEA"),
            "nc_app_group": "l2msa",
            "nc_app_group_label": "NCV-Lineage2M",
            "store_key_prefix": "com.ncv.l2m.",
            "mytool_search_order": {
                "SEA": "https://mytool.ge.vng.vn/en/webpayment/tool/search-order/JV1.JVL2M_SEA",
                "VN": "https://mytool.ge.vng.vn/en/webpayment/tool/search-order/A22.L2M_VN",
            },
        },
    },
    # Bản local của thành viên đẩy kết quả lên server team qua API (cổng api_port trên máy server).
    "team": {"server_url": "", "token": "", "api_port": 8502},
}

# Env var ghi đè giá trị trong settings.json — khi deploy web, đặt key ở đây thay vì lưu file.
ENV_OVERRIDES = {
    ("ai", "claude", "api_key"): "ANTHROPIC_API_KEY",
    ("ai", "openai", "api_key"): "OPENAI_API_KEY",
    ("ai", "gemini", "api_key"): "GEMINI_API_KEY",
    ("ai", "gateway", "api_key"): "GATEWAY_API_KEY",
    ("ai", "gateway", "base_url"): "GATEWAY_BASE_URL",
    ("ai", "provider"): "L2M_AI_PROVIDER",
}


LOCAL_PATH = DATA_DIR / "local.json"  # cấu hình riêng của máy này (vd địa chỉ CSDL chung), không đưa lên CSDL
_secrets_checked = False


def env(name: str, default: str = "") -> str:
    """Biến môi trường. Trên Streamlit Cloud, secrets cấp gốc (.streamlit/secrets.toml) được Streamlit đưa vào
    biến môi trường khi đọc lần đầu — đọc một lần là đủ."""
    global _secrets_checked
    if name not in os.environ and not _secrets_checked and "streamlit" in sys.modules:
        _secrets_checked = True
        try:
            import streamlit as st

            st.secrets.load_if_toml_exists()
        except Exception:  # noqa: BLE001 — không có / không đọc được secrets: dùng biến môi trường như thường
            pass
    return os.environ.get(name, default)


_local_cache: tuple[float, dict] | None = None


def load_local() -> dict:
    global _local_cache
    try:
        mtime = LOCAL_PATH.stat().st_mtime
    except OSError:
        return {}
    if _local_cache is None or _local_cache[0] != mtime:
        try:
            _local_cache = (mtime, json.loads(LOCAL_PATH.read_text(encoding="utf-8-sig")))
        except (OSError, json.JSONDecodeError):
            return {}
    return dict(_local_cache[1])


def save_local(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def database_url() -> str:
    """Postgres dùng chung (Supabase). Trống -> SQLite data/app.db như trước.
    Website: secrets DATABASE_URL. Bản local: trang Cài đặt ghi vào data/local.json."""
    return (env("DATABASE_URL") or load_local().get("database_url") or "").strip()


def app_mode() -> str:
    """'local' = máy cá nhân, không cần đăng nhập. 'team' = dùng chung cho cả team (đăng nhập, phân quyền, lịch sử chung).
    Nối CSDL chung thì luôn là 'team', để mỗi thao tác ghi đúng tên người làm."""
    mode = env("L2M_APP_MODE").strip().lower()
    if mode in ("team", "web") or (not mode and database_url()):
        return "team"
    return "local"


def team_mode() -> bool:
    return app_mode() == "team"


def automation_enabled() -> bool:
    """Tiến trình này có điều khiển được trình duyệt không. Ở chế độ team còn phải là người ngồi tại máy chạy app
    (kiểm tra ở ui.auth.automation_allowed). L2M_NO_AUTOMATION=1 tắt hẳn (vd website trên Streamlit Cloud)."""
    return env("L2M_NO_AUTOMATION") != "1"


def _merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _migrate(stored: dict) -> dict:
    """Bản cũ để app group / URL MyTool trong 'automation' -> chuyển sang hồ sơ game Lineage2M."""
    auto = stored.get("automation", {})
    old = {k: auto.pop(k) for k in ("nc_app_group", "mytool_search_order", "mytool_sold_package") if k in auto}
    if old:
        l2m = stored.setdefault("games", {}).setdefault(DEFAULT_GAME, {})
        for k, v in old.items():
            l2m.setdefault(k, v)
    return stored


# Khi dùng CSDL chung, các phần này lưu trong CSDL (bảng app_settings) để website và mọi bản local cùng một cấu hình.
# Phần còn lại (thư mục lưu kết quả, server team kiểu cũ) là của riêng từng máy, vẫn nằm trong data/settings.json.
SHARED_KEYS = ("ai", "automation", "default_game", "default_lang", "games")


def _shared_from_db(settings: dict) -> dict:
    from . import store  # import muộn: store cũng import config

    shared = store.get_app_setting("shared")
    if shared is None:  # lần đầu nối CSDL chung: lấy cấu hình của máy này làm cấu hình chung
        store.set_app_setting("shared", {k: settings[k] for k in SHARED_KEYS}, "system")
        return settings
    shared = {k: v for k, v in shared.items() if k in SHARED_KEYS}
    games = shared.pop("games", None)
    settings = _merge(settings, shared)
    if games:
        settings["games"] = games  # thay hẳn, để game đã xoá không quay lại
    return settings


def load_settings() -> dict:
    stored = {}
    if SETTINGS_PATH.exists():
        try:
            stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            stored = {}
    settings = _merge(DEFAULTS, _migrate(stored))
    if database_url():
        settings = _shared_from_db(settings)
    for gid, profile in settings["games"].items():
        settings["games"][gid] = _merge(blank_game(gid), profile)  # game thêm sau vẫn đủ trường
    if settings.get("default_game") not in settings["games"]:
        settings["default_game"] = DEFAULT_GAME
    for path, name in ENV_OVERRIDES.items():
        value = env(name)
        if value:
            node = settings
            for key in path[:-1]:
                node = node.setdefault(key, {})
            node[path[-1]] = value
    return settings


def save_settings(settings: dict, by: str = "admin") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    if database_url():
        from . import store

        store.set_app_setting("shared", {k: settings[k] for k in SHARED_KEYS}, by)


def game(settings: dict, gid: str | None = None) -> dict:
    """Hồ sơ game (kèm 'id'). Không truyền gid -> game mặc định."""
    gid = gid if gid in settings["games"] else settings.get("default_game", DEFAULT_GAME)
    return {"id": gid, **settings["games"][gid]}


def browser_channel(settings: dict, own: str = "") -> str:
    """Trình duyệt mở NC tool / MyTool: người dùng tự chọn (own), không chọn thì theo mặc định của team."""
    return own if own in BROWSERS else settings["automation"].get("browser_channel") or "msedge"


def game_id_from_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())[:16] or "game"


def api_key(settings: dict, provider: str) -> str:
    return (settings.get("ai", {}).get(provider, {}).get("api_key") or "").strip()


def master_dir(gid: str) -> Path:
    """Thư mục master của một game. Khi dùng CSDL chung, master nằm trong CSDL và đây chỉ là bản sao tạm
    (thư mục riêng, không lẫn với master của chế độ SQLite)."""
    return (DATA_DIR / "master-shared" if database_url() else MASTER_DIR) / gid


def _migrate_master_layout() -> None:
    """Bản cũ: data/master/current.xlsx (chỉ có Lineage2M) -> data/master/l2m/."""
    old = MASTER_DIR / "current.xlsx"
    new_dir = master_dir(DEFAULT_GAME)
    if old.exists() and not (new_dir / "current.xlsx").exists():
        new_dir.mkdir(parents=True, exist_ok=True)
        for name in ("current.xlsx", "current.json", "history"):
            if (MASTER_DIR / name).exists():
                shutil.move(str(MASTER_DIR / name), str(new_dir / name))


def ensure_dirs() -> None:
    for d in (DATA_DIR, MASTER_DIR, WORK_DIR):
        d.mkdir(parents=True, exist_ok=True)
    _migrate_master_layout()
