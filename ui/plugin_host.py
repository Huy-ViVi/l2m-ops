"""Đưa plugin (plugins/<id>/) vào menu website và chạy trang plugin trong khung cô lập lỗi:
plugin lỗi chỉ hiện thông báo ở trang của nó, phần còn lại của website vẫn chạy."""
from __future__ import annotations

import runpy
import sys
import traceback
import types
from pathlib import Path

import streamlit as st

from core import plugins, sdk
from core.i18n import t
from ui import auth, common


def ensure_package() -> None:
    """`plugins.<id>` import được (để trang plugin dùng `from . import helpers`), kể cả khi L2M_PLUGINS_DIR trỏ chỗ khác."""
    root = str(plugins.PLUGINS_DIR)
    pkg = sys.modules.get("plugins")
    if pkg is None or root not in [str(x) for x in getattr(pkg, "__path__", [])]:
        pkg = types.ModuleType("plugins")
        pkg.__path__ = [root]
        sys.modules["plugins"] = pkg


def visible(p: plugins.Plugin) -> bool:
    if not p.ok or (p.access == "admin" and not auth.is_admin()):
        return False
    return not p.games or common.game()["id"] in p.games


def _module(p: plugins.Plugin, page: plugins.Page) -> str:
    return f"plugins.{p.id}." + Path(page.file).with_suffix("").as_posix().replace("/", ".")


def run_page(p: plugins.Plugin, page: plugins.Page) -> None:
    """Chạy một trang plugin như module trong gói plugins.<id> (đọc lại file mỗi lượt chạy)."""
    ensure_package()
    token = sdk._bind(p)
    try:
        runpy.run_module(_module(p, page), run_name="__main__", alter_sys=False)
    except Exception as e:  # noqa: BLE001 — st.stop / st.rerun không phải Exception nên vẫn chạy bình thường
        st.error(t("Plugin **{name}** đang bị lỗi: {error}", name=p.label, error=f"{type(e).__name__}: {e}"))
        st.caption(t("Phần còn lại của website vẫn dùng bình thường. Báo cho người phụ trách plugin: {owners}.",
                     owners=", ".join(p.owners) or "?"))
        with st.expander(t("Chi tiết lỗi (gửi cho người phụ trách plugin)")):
            st.code(traceback.format_exc(), language=None)
    finally:
        sdk._unbind(token)


def _page(p: plugins.Plugin, page: plugins.Page):
    def run() -> None:
        run_page(p, page)

    stem = Path(page.file).with_suffix("").as_posix().replace("/", "-")
    run.__name__ = f"plugin_{p.id}_{stem.replace('-', '_')}"
    return st.Page(run, title=page.title, icon=page.icon or None, url_path=f"plugin-{p.id}-{stem}")


def sections() -> dict[str, list]:
    """Nhóm menu -> trang của các plugin người này được thấy (plugin lỗi khai báo bị bỏ qua, xem ở trang Plugin của team)."""
    reserved = {"", t("Chức năng"), "Team", t("Hệ thống")}  # nhóm của nền tảng (app.py) — trùng tên sẽ đè mất trang
    out: dict[str, list] = {}
    for p in plugins.discover():
        if not visible(p):
            continue
        try:
            built = [_page(p, page) for page in p.pages]
        except Exception:  # noqa: BLE001 — một plugin khai báo lạ không được làm hỏng menu
            continue
        out.setdefault(plugins.DEFAULT_SECTION if p.section in reserved else p.section, []).extend(built)
    return out
