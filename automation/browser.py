"""Mở trình duyệt thật (Edge) với profile riêng của app để giữ session SSO giữa các lần chạy.

App không bao giờ nhập mật khẩu: lần đầu bạn tự đăng nhập trong cửa sổ trình duyệt, cookie được giữ
trong data/browser-profile cho các lần sau.
"""
from __future__ import annotations

import re
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import BrowserContext, Page, sync_playwright

from core.i18n import t


def log(msg: str) -> None:
    print(msg, flush=True)


@contextmanager
def browser(profile_dir: Path, channel: str = "msedge", headless: bool = False):
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        kwargs = dict(user_data_dir=str(profile_dir), headless=headless, accept_downloads=True,
                      no_viewport=True, args=["--start-maximized"])
        if channel and channel != "chromium":
            kwargs["channel"] = channel
        ctx = p.chromium.launch_persistent_context(**kwargs)

        def on_dialog(dialog):
            # Tool NC bật alert/confirm sau mỗi lần Add/Register — tự đồng ý để không bị treo.
            log(t("  [hộp thoại] {message}", message=dialog.message[:120]))
            dialog.accept()

        def wire(page: Page):
            page.on("dialog", on_dialog)

        for pg in ctx.pages:
            wire(pg)
        ctx.on("page", wire)
        try:
            yield ctx
        finally:
            try:
                ctx.close()
            except Exception:
                pass


def new_page(ctx: BrowserContext) -> Page:
    blank = [p for p in ctx.pages if p.url in ("about:blank", "")]
    return blank[0] if blank else ctx.new_page()


def _needs_login(page: Page, host: str) -> bool:
    if urlparse(page.url).netloc != host:
        return True
    try:
        return page.locator("input[type=password]:visible").count() > 0
    except Exception:
        return False


def open_logged_in(page: Page, url: str, timeout_s: int = 600) -> None:
    """Mở URL; nếu bị chuyển sang trang SSO thì chờ người dùng tự đăng nhập."""
    host = urlparse(url).netloc
    page.goto(url, wait_until="domcontentloaded")
    if not _needs_login(page, host):
        return
    log(t("🔐 Cần đăng nhập — hãy đăng nhập trong cửa sổ trình duyệt vừa mở (app sẽ chờ)."))
    deadline = time.time() + timeout_s
    while _needs_login(page, host):
        if time.time() > deadline:
            raise TimeoutError(t("Hết thời gian chờ đăng nhập."))
        page.wait_for_timeout(2000)
    page.wait_for_load_state("domcontentloaded")
    if page.url.rstrip("/") != url.rstrip("/"):
        page.goto(url, wait_until="domcontentloaded")
    log(t("✅ Đã đăng nhập."))


def settle(page: Page, ms: int = 1500) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    page.wait_for_timeout(ms)


def click_button(page: Page, text: str) -> None:
    btn = page.get_by_role("button", name=re.compile(rf"^\s*{re.escape(text)}\s*$", re.I))
    if btn.count():
        btn.first.click()
        return
    page.get_by_text(text, exact=True).first.click()


def wait_until_left(page: Page, url_part: str, timeout_s: int = 1800) -> bool:
    """Chờ người dùng tự bấm Register (trang rời khỏi url_part). False nếu cửa sổ bị đóng/hết giờ."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if page.is_closed():
            return False
        if url_part not in page.url:
            return True
        page.wait_for_timeout(1500)
    return False


TABLE_JS = """
(skipForms) => {
  const out = [];
  for (const table of document.querySelectorAll('table')) {
    if (!table.offsetParent) continue;
    // Bảng form tìm kiếm (có ô nhập/ô chọn) không phải bảng kết quả.
    if (skipForms && table.querySelector('input:not([type=checkbox]):not([type=hidden]):not([type=radio]), select, textarea')) continue;
    let headers = [...table.querySelectorAll('thead th')].map(th => th.innerText.trim());
    let rows = [...table.querySelectorAll('tbody tr')];
    if (!headers.length && rows.length) {
      headers = [...rows[0].children].map(c => c.innerText.trim());
      rows = rows.slice(1);
    }
    for (const tr of rows) {
      const cells = [...tr.children].map(c => c.innerText.trim());
      if (!cells.some(Boolean)) continue;
      const rec = {};
      cells.forEach((v, i) => { rec[headers[i] || ('col' + (i + 1))] = v; });
      out.push(rec);
    }
  }
  return out;
}
"""

KV_JS = """
() => {
  const kv = {};
  const put = (k, v) => { k = (k || '').trim(); if (k && !(k in kv)) kv[k] = (v || '').trim(); };
  for (const tr of document.querySelectorAll('tr')) {
    const ths = tr.querySelectorAll(':scope > th');
    const tds = tr.querySelectorAll(':scope > td');
    ths.forEach((th, i) => { if (tds[i]) put(th.innerText, tds[i].innerText); });
  }
  for (const dt of document.querySelectorAll('dt')) {
    if (dt.nextElementSibling && dt.nextElementSibling.tagName === 'DD') put(dt.innerText, dt.nextElementSibling.innerText);
  }
  return {kv, text: document.body.innerText};
}
"""
