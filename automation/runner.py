"""Chạy một job browser automation trong tiến trình riêng (Streamlit gọi qua subprocess, cũng chạy được từ terminal).

    python -m automation.runner <job> --input payload.json --output result.json

Job: login | nc_inspect | nc_create | nc_view | nc_item_lookup | nc_item_dump | nc_app_groups | mytool_orders | mytool_sold
Payload có "game" (id hồ sơ game trong Cài đặt) — app group, URL MyTool... lấy theo game đó.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import config, netcheck  # noqa: E402
from core.i18n import t  # noqa: E402

from automation import mytool, nc_billing  # noqa: E402
from automation.browser import browser, log  # noqa: E402


class NetworkProblem(RuntimeError):
    """Biết chắc không tới được tool -> báo lỗi ngắn gọn, không in traceback."""


def _target_urls(job: str, payload: dict, auto: dict, game: dict) -> list[str]:
    base = auto["nc_base_url"].rstrip("/")
    if job.startswith("nc_"):
        return [base]
    if job == "mytool_orders":
        return [game["mytool_search_order"][s] for s in payload.get("shops", ["SEA", "VN"]) if game["mytool_search_order"].get(s)]
    if job == "mytool_sold":
        return [u for u in game["mytool_sold_package"].values() if u]
    return []


def preflight(job: str, payload: dict, auto: dict, game: dict) -> None:
    """Kiểm tra DNS trước khi mở trình duyệt (vd NC tool cần VPN)."""
    hosts_checked = set()
    for url in _target_urls(job, payload, auto, game):
        host = url.split("/")[2] if "//" in url else url
        if host in hosts_checked:
            continue
        hosts_checked.add(host)
        problem = netcheck.blocking_problem(url)
        if problem:
            raise NetworkProblem(problem)
        log(t("  ✓ Kết nối được {host}", host=host))


def run(job: str, payload: dict) -> dict:
    settings = config.load_settings()
    auto = settings["automation"]
    game = config.game(settings, payload.get("game"))  # mọi thông số theo game đang chọn trên UI
    log(f"🎮 Game: {game['name']} (app group {game['nc_app_group'] or '?'})")
    base = auto["nc_base_url"].rstrip("/")
    preflight(job, payload, auto, game)
    # L2M_HEADLESS=1: không hiện cửa sổ trình duyệt (chỉ dùng khi test — thao tác thật cần người xem và bấm Register)
    with browser(config.BROWSER_PROFILE_DIR, auto.get("browser_channel", "msedge"), headless=config.env("L2M_HEADLESS") == "1") as ctx:
        if job == "login":
            urls = payload.get("urls") or [f"{base}/MobileGoodsAdmin/goods"] + [u for u in [game["mytool_search_order"].get("SEA")] if u]
            for url in urls:
                problem = netcheck.blocking_problem(url)
                if problem:
                    log(t("  ⚠ Bỏ qua {url}: {problem}", url=url, problem=problem))
                    continue
                page = ctx.new_page()
                try:
                    page.goto(url, wait_until="domcontentloaded")
                except Exception as e:  # noqa: BLE001
                    log(t("  ⚠ Không mở được {url}: {error}", url=url, error=e))
            log(t("🔐 Đăng nhập các trang vừa mở. Xong thì ĐÓNG cửa sổ trình duyệt để lưu phiên."))
            ctx.wait_for_event("close", timeout=30 * 60 * 1000)
            return {"ok": True}

        if job == "nc_inspect":
            form = payload.get("form", "goods_new")
            url = payload.get("url") or (f"{base}/MobileGoodsAdmin/goods/new" if form == "goods_new"
                                         else f"{base}/MobileLimitAdmin/purchase/goodsgroup/new")
            dump = nc_billing.inspect(ctx, url)
            mapping = nc_billing.calibrate(dump, nc_billing.load_fields()[form])
            log(t("  Tìm thấy {fields} ô, map được {mapped} trường.", fields=len(dump), mapped=len(mapping)))
            return {"ok": True, "form": form, "dump": dump, "mapping": mapping}

        if job == "nc_create":
            mode = payload.get("mode", "manual")
            results = []
            for plan in payload["plans"]:
                r = nc_billing.create_goods(ctx, plan, auto, mode)
                goods_id = r.get("goods_id") or plan.get("goods_id")
                if payload.get("create_limit", True) and plan.get("limit") and not plan["limit"].get("error"):
                    if goods_id:
                        r["limit"] = nc_billing.create_limit(ctx, plan, goods_id, auto, mode)
                    else:
                        log(t("  ⚠ Chưa có Product # nên chưa tạo limit — chạy lại sau khi có Product #"))
                results.append(r)
            return {"ok": True, "results": results}

        if job == "nc_view":
            views = []
            for target in payload["targets"]:
                views.append({**target, **nc_billing.read_view(ctx, target["url"])})
            return {"ok": True, "views": views}

        if job == "nc_item_lookup":
            res = nc_billing.item_lookup(ctx, auto, payload["names"], game["nc_app_group"], game["nc_app_group_label"])
            if "_error" in res:
                return {"ok": False, "error": res.pop("_error"), "results": res}
            return {"ok": True, "results": res}

        if job == "nc_item_dump":
            res = nc_billing.dump_items(ctx, auto, game["nc_app_group"], game["nc_app_group_label"],
                                        int(payload.get("max_pages", 300)))
            if "_error" in res:
                return {"ok": False, "error": res["_error"]}
            return {"ok": True, "rows": res["rows"]}

        if job == "nc_app_groups":
            return {"ok": True, "app_groups": nc_billing.list_app_groups(ctx, auto)}

        if job == "mytool_orders":
            out_dir = Path(payload.get("out_dir") or config.WORK_DIR / "mytool")
            results = []
            for shop in payload.get("shops", ["SEA", "VN"]):
                url = game["mytool_search_order"].get(shop)
                if url:
                    results.append(mytool.export_orders(ctx, shop, url, payload["orders"], out_dir))
                else:
                    log(t("  ⚠ {game}: chưa cấu hình URL Search Order shop {shop}", game=game["name"], shop=shop))
            return {"ok": True, "results": results}

        if job == "mytool_sold":
            sold = game["mytool_sold_package"]
            shops = {k: v for k, v in sold.items() if k in payload.get("shops", list(sold))}
            return {"ok": True, "results": mytool.sold_packages(ctx, shops, payload["package_ids"])}

    raise ValueError(t("Job không hợp lệ: {job}", job=job))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--input")
    ap.add_argument("--output")
    args = ap.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8")) if args.input else {}
    try:
        result = run(args.job, payload)
    except NetworkProblem as e:
        log(f"✗ {e}")
        result = {"ok": False, "error": str(e), "kind": "network"}
    except Exception as e:  # noqa: BLE001 — trả lỗi về UI thay vì crash im lặng
        friendly = netcheck.explain(str(e))
        if type(e).__name__ == "TargetClosedError":  # người dùng đóng cửa sổ Edge giữa chừng
            message = t("Trình duyệt đã bị đóng trước khi thao tác xong. Chạy lại và giữ cửa sổ Edge mở tới khi log báo xong "
                        "(nếu cửa sổ bật lên trên máy người khác: bạn đang dùng tài khoản của họ).")
            log(f"✗ {message}")
            result = {"ok": False, "error": message, "kind": "closed"}
        elif friendly:
            log(f"✗ {friendly}")
            result = {"ok": False, "error": friendly, "kind": "network"}
        else:
            traceback.print_exc()
            result = {"ok": False, "error": f"{type(e).__name__}: {str(e).splitlines()[0][:300]}"}
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
