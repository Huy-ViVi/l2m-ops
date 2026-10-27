"""Điều khiển VNGGames MyTool: Search Order (Export Excel) và Shop Operation > Sold Package.

Không patch XMLHttpRequest/fetch trên MyTool (làm treo trang) — lấy dữ liệu qua Export Excel và đọc bảng.
Download được Playwright bắt trực tiếp nên không bật hộp thoại Save As của Windows.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext

from core.i18n import t
from core.master import markets_for, short_key

from .browser import TABLE_JS, click_button, log, new_page, open_logged_in, settle


def export_orders(ctx: BrowserContext, shop: str, url: str, orders: list[str], out_dir: Path) -> dict:
    page = new_page(ctx)
    log(t("\n=== MyTool Search Order — shop {shop} ({n} mã) ===", shop=shop, n=len(orders)))
    open_logged_in(page, url)
    settle(page)
    page.get_by_text("Order Number", exact=True).first.click()
    page.wait_for_timeout(800)
    box = page.locator("textarea:visible")
    if not box.count():
        return {"shop": shop, "status": "error", "message": t("Không thấy ô nhập Order Number (Step 2)")}
    box.first.fill("\n".join(orders))
    click_button(page, "Confirm")
    settle(page, 3000)
    if page.get_by_text("not available", exact=False).count() and not page.locator("table tbody tr").count():
        log(t("  · Order Info not available ở shop này"))
        return {"shop": shop, "status": "not_found", "message": "Order Info not available"}
    out_dir.mkdir(parents=True, exist_ok=True)
    with page.expect_download(timeout=120_000) as dl_info:
        click_button(page, "Export Excel")
    dl = dl_info.value
    path = out_dir / f"{shop}-{dl.suggested_filename or 'orders.xlsx'}"
    dl.save_as(path)
    log(t("  ✓ Đã export: {file}", file=path.name))
    return {"shop": shop, "status": "ok", "file": str(path)}


def _search_box(page):
    for css in ("input[type=search]:visible", "input[placeholder*='earch' i]:visible",
                "input[placeholder*='ackage' i]:visible", "input[placeholder*='eyword' i]:visible"):
        loc = page.locator(css)
        if loc.count():
            return loc.first
    return None


def sold_packages(ctx: BrowserContext, shop_urls: dict[str, str], package_ids: list[str]) -> list[dict]:
    keys = [short_key(p) for p in package_ids if short_key(p)]
    results: list[dict] = []
    page = new_page(ctx)
    for shop, url in shop_urls.items():
        wanted = [k for k in keys if shop in markets_for(k)]
        if not wanted:
            continue
        if not url:
            log(t("  ⚠ Shop {shop}: chưa cấu hình URL Sold Package (trang Cài đặt) — bỏ qua", shop=shop))
            continue
        log(f"\n=== Sold Package — shop {shop} ===")
        open_logged_in(page, url)
        settle(page, 2500)
        box = _search_box(page)
        if box is None:
            log(t("  ✗ Không thấy ô search ở shop {shop}", shop=shop))
            continue
        for k in wanted:
            box.click()
            box.fill("")
            box.fill(k)
            box.press("Enter")
            settle(page, 2000)
            rows = page.evaluate(TABLE_JS)
            exact = [r for r in rows if any(v.strip().lower() in (k, "com.ncv.l2m." + k) for v in r.values())]
            loose = [r for r in rows if k in " ".join(r.values()).lower()]
            hit = (exact or loose or [None])[0]
            if hit is None:
                log(t("  ✗ {key}: không thấy", key=k))
                results.append({"Package ID": k, "Shop": shop, "_not_found": True, "_raw": {}})
            else:
                log(f"  ✓ {k}: {' | '.join(v for v in hit.values() if v)[:140]}")
                results.append({"Package ID": k, "Shop": shop, "_raw": hit})
    return results
