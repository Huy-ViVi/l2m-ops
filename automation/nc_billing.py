"""Điều khiển NC Goods Admin + Limit Admin (rc-ncv-billingadmin.ncsoft.net).

Mặc định chế độ 'manual': app điền form rồi DỪNG, bạn kiểm tra và tự bấm Register trong trình duyệt.
Kinh nghiệm từ skill: radio phải click thật (không set prop), dòng item trống là template ẩn — không đụng,
thêm item qua $.fn.addGoodsItem, thêm product vào limit qua $.fn.addGoods.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from playwright.sync_api import BrowserContext, Page

from core import config
from core.excel import norm
from core.i18n import t

from .browser import KV_JS, TABLE_JS, click_button, log, new_page, open_logged_in, settle, wait_until_left

DEFAULT_FIELDS_PATH = Path(__file__).with_name("nc_fields.json")
CALIBRATED_FIELDS_PATH = config.DATA_DIR / "nc_fields.json"
ITEM_TYPE_GAME = 103
CURRENCY_GROUP_CASH = 1

LABEL_JS = """
([label, nth, field]) => {
  const norm = s => (s || '').replace(/\\s+/g, ' ').replace(/[*:]\\s*$/, '').trim().toLowerCase();
  const want = norm(label);
  const cands = [...document.querySelectorAll('th, label, dt, .control-label, .form-label, td')]
    .filter(el => el.offsetParent !== null && !el.querySelector('input, select, textarea'));
  const hits = cands.filter(el => { const t = norm(el.innerText); return t === want || t.startsWith(want + ' ') || t.startsWith(want + '('); });
  const exact = cands.filter(el => norm(el.innerText) === want);
  const el = (exact.length > (nth || 0) ? exact : hits)[nth || 0];
  if (!el) return false;
  let scope = null;
  if (el.tagName === 'LABEL' && el.htmlFor) { const c = document.getElementById(el.htmlFor); if (c) scope = c.closest('td, dd, .form-group, div') || c.parentElement; }
  if (!scope && ['TH', 'TD', 'DT'].includes(el.tagName)) scope = el.nextElementSibling;
  if (!scope) scope = el.parentElement;
  document.querySelectorAll(`[data-l2m-scope="${field}"]`).forEach(x => x.removeAttribute('data-l2m-scope'));
  scope.setAttribute('data-l2m-scope', field);
  return true;
}
"""

INSPECT_JS = """
() => [...document.querySelectorAll('input, select, textarea, button')].map(e => {
  const tr = e.closest('tr');
  let rowLabel = '';
  if (tr) { const th = tr.querySelector('th'); if (th) rowLabel = th.innerText; }
  if (!rowLabel) { const g = e.closest('.form-group, dd'); const l = g && (g.querySelector('label, .control-label') || g.previousElementSibling); if (l) rowLabel = l.innerText; }
  let own = '';
  if (e.id) { const l = document.querySelector(`label[for="${CSS.escape(e.id)}"]`); if (l) own = l.innerText; }
  if (!own && e.closest('label')) own = e.closest('label').innerText;
  return {
    tag: e.tagName.toLowerCase(), type: e.type || '', name: e.name || '', id: e.id || '',
    value: e.type === 'password' ? '' : String(e.value || '').slice(0, 80),
    row_label: rowLabel.trim().slice(0, 80), own_label: own.trim().slice(0, 80),
    text: e.tagName === 'BUTTON' ? e.innerText.trim().slice(0, 40) : '',
    visible: !!e.offsetParent, checked: !!e.checked,
    options: e.tagName === 'SELECT' ? [...e.options].slice(0, 60).map(o => [o.value, o.text.trim()]) : null,
  };
})
"""

MARK_LAST_JS = """
([keyword, marker]) => {
  const k = keyword.toLowerCase();
  const els = [...document.querySelectorAll('input')].filter(e => e.offsetParent !== null && e.type !== 'hidden'
    && ((e.name || '') + ' ' + (e.id || '') + ' ' + (e.className || '')).toLowerCase().includes(k));
  if (!els.length) return false;
  document.querySelectorAll(`[data-l2m-mark="${marker}"]`).forEach(x => x.removeAttribute('data-l2m-mark'));
  els[els.length - 1].setAttribute('data-l2m-mark', marker);
  return true;
}
"""


def load_fields() -> dict:
    fields = json.loads(DEFAULT_FIELDS_PATH.read_text(encoding="utf-8-sig"))
    if CALIBRATED_FIELDS_PATH.exists():
        calibrated = json.loads(CALIBRATED_FIELDS_PATH.read_text(encoding="utf-8-sig"))
        for form in ("goods_new", "limit_new"):
            for name, spec in calibrated.get(form, {}).items():
                fields.setdefault(form, {}).setdefault(name, {}).update(spec)
    return fields


# ---------------------------------------------------------------------------
# Điền form
# ---------------------------------------------------------------------------
def _scope(page: Page, field: str, spec: dict):
    for i, label in enumerate(spec.get("labels", [])):
        if page.evaluate(LABEL_JS, [label, spec.get("label_nth", 0), field]):
            return page.locator(f'[data-l2m-scope="{field}"]')
    return None


OPTIONS_JS = "s => [...s.options].map(o => [o.value, o.text.trim()])"
SET_SELECT_JS = """(s, v) => {
  s.value = v;
  s.dispatchEvent(new Event('input', {bubbles: true}));
  s.dispatchEvent(new Event('change', {bubbles: true}));  // jQuery/select2 cũng nghe sự kiện này -> ô giả cập nhật theo
  return s.value === v;
}"""


def _set_select(sel, value: str) -> bool:
    """Chọn option theo value. Tool NC dùng dropdown tuỳ biến (select2...) -> ô <select> gốc bị ẩn,
    Playwright không thao tác được trên phần tử ẩn nên đặt giá trị trực tiếp rồi phát sự kiện change."""
    try:
        if sel.is_visible():
            sel.select_option(value=value, timeout=3000)
            return True
    except Exception:  # noqa: BLE001 — rơi xuống cách đặt trực tiếp
        pass
    return bool(sel.evaluate(SET_SELECT_JS, value))


def _select(sel, option: str) -> bool:
    """Chọn option theo text: khớp chính xác trước, sau đó khớp chuỗi con (vd 'VNG Store' ~ 'VNG Store (25)')."""
    options = sel.evaluate(OPTIONS_JS)
    for value, text in options:
        if norm(text) == norm(option) or value == option:
            return _set_select(sel, value)
    for value, text in options:
        if norm(option) and norm(option) in norm(text):
            return _set_select(sel, value)
    return False


def _choose(page: Page, root, option: str) -> bool:
    sel = root.locator("select")
    if sel.count() and _select(sel.first, option):
        return True
    radio = root.get_by_label(option, exact=True)
    if radio.count():
        radio.first.click()  # click thật để kích hoạt handler của form
        return True
    text = root.get_by_text(option, exact=True)
    if text.count():
        text.first.click()
        return True
    return False


def fill_field(page: Page, field: str, spec: dict, value) -> bool:
    kind = spec.get("kind", "text")
    if spec.get("selector"):
        loc = page.locator(spec["selector"])
        if loc.count():
            target = loc.nth(spec.get("nth", 0))
            if kind == "text":
                target.fill(str(value))
                return True
            if target.evaluate("e => e.tagName") == "SELECT":
                return _select(target, str(value))
            target.click()  # radio đã calibrate: click thật
            return True
    root = _scope(page, field, spec)
    if root is None:
        return False
    if kind == "text":
        box = root.locator("input:not([type=hidden]):not([type=radio]):not([type=checkbox]):visible, textarea:visible")
        if not box.count():
            return False
        box.nth(spec.get("nth", 0)).fill(str(value))
        return True
    if kind == "select":
        sel = root.locator("select")
        return bool(sel.count()) and _choose(page, root, str(value))
    return _choose(page, root, str(value))


def _fill_all(page: Page, form: dict, values: dict) -> tuple[list[str], list[str]]:
    filled, missing = [], []
    for field, value in values.items():
        spec = form.get(field)
        if spec is None or value in (None, ""):
            continue
        try:
            ok = fill_field(page, field, spec, value)
        except Exception as e:  # noqa: BLE001 — một trường lỗi không được làm hỏng cả form
            log(f"  ⚠ {field}: {e}")
            ok = False
        (filled if ok else missing).append(field)
        mark = "✓" if ok else t("✗ CHƯA MAP — điền tay")
        log(f"  {mark} {field} = {value}")
    return filled, missing


APP_GROUP_LABELS = ["Item app group code", "App group code", "App group", "Application group"]


def _match_app_group(options: list, want_code: str, want_label: str):
    """Ưu tiên: đúng mã (value) > đúng tên > mã nằm trong tên > tên gần đúng."""
    for test in (
        lambda v, t: want_code and v.strip().lower() == want_code,
        lambda v, t: want_label and norm(t) == want_label,
        lambda v, t: want_code and re.search(rf"\b{re.escape(want_code)}\b", t.lower()),
        lambda v, t: want_label and (want_label in norm(t) or (norm(t) and norm(t) in want_label)),
    ):
        hit = next((v for v, t in options if v and test(v, t)), None)
        if hit is not None:
            return hit
    return None


def _try_select_app_group(page: Page, want_code: str, want_label: str) -> bool:
    for sel in page.locator("select").all():  # gồm cả <select> bị ẩn dưới dropdown tuỳ biến
        options = sel.evaluate(OPTIONS_JS)
        hit = _match_app_group(options, want_code, want_label)
        if hit is None:
            continue
        text = next(t for v, t in options if v == hit)
        if sel.evaluate("s => s.value") != hit:
            _set_select(sel, hit)
            settle(page, 800)
        ok = sel.evaluate("s => s.value") == hit
        log(f"  {'✓' if ok else '✗'} App group = {text or hit}")
        return ok
    return False


def _select_app_group(page: Page, code: str, label: str = "") -> bool:
    """Chọn đúng app group của game (tool hay để mặc định game khác, vd NCV-Journey Of Monarch)."""
    want_code, want_label = (code or "").strip().lower(), norm(label)
    if _try_select_app_group(page, want_code, want_label):
        return True
    # Danh sách có thể chỉ được nạp khi bấm vào ô -> bấm mở rồi thử lại một lần.
    scope = _scope(page, "app_group_box", {"labels": APP_GROUP_LABELS})
    if scope is not None:
        try:
            scope.click(timeout=3000)
            page.wait_for_timeout(1200)
            page.keyboard.press("Escape")
        except Exception:  # noqa: BLE001
            pass
        if _try_select_app_group(page, want_code, want_label):
            return True
    log("  " + t("⚠ Không thấy app group '{group}'. Các ô chọn đang có trên trang:", group=label or code))
    found = False
    for i, sel in enumerate(page.locator("select").all()):
        options = sel.evaluate(OPTIONS_JS)
        if len(options) > 1 or any("ncv" in txt.lower() for _, txt in options):
            found = True
            log(f"    [{i}] " + t("{n} lựa chọn:", n=len(options)) + " " + ", ".join(f"{txt} ({v})" for v, txt in options[:15]))
    if not found:
        log("    " + t("(không có ô <select> nào chứa app group — có thể là dropdown nạp dữ liệu khi gõ; gửi ảnh chụp ô này để chỉnh)"))
    return False


def list_app_groups(ctx: BrowserContext, auto: dict) -> list[list[str]]:
    """Danh sách app group (value, tên) trên trang Item lookup — để admin chọn khi thêm game."""
    base = auto["nc_base_url"].rstrip("/")
    page = new_page(ctx)
    open_logged_in(page, f"{base}/MobileGoodsAdmin/items")
    settle(page)
    scope = _scope(page, "app_group_list", {"labels": APP_GROUP_LABELS})
    sel = scope.locator("select").first if scope is not None and scope.locator("select").count() else None
    if sel is None:
        candidates = [s for s in page.locator("select").all()  # gồm cả <select> bị ẩn dưới dropdown tuỳ biến
                      if any("ncv" in t.lower() for _, t in s.evaluate(OPTIONS_JS))]
        sel = candidates[0] if candidates else None
    if sel is None:
        log("  " + t("✗ Không thấy ô chọn app group trên trang Item lookup"))
        return []
    options = [[v, txt] for v, txt in sel.evaluate(OPTIONS_JS) if v]
    log("  " + t("✓ Tìm thấy {n} app group", n=len(options)))
    return options


def _has_jquery_fn(page: Page, fn: str) -> bool:
    return page.evaluate(f"() => typeof window.$ !== 'undefined' && !!(window.$.fn && window.$.fn.{fn})")


# ---------------------------------------------------------------------------
# Điền form theo tên/id ô THẬT của NC tool (skill package-creation §8c, đã chạy 06/08–08/10/2026).
# Ô nào không thấy thì rơi xuống cách dò theo nhãn (nc_fields.json / Calibrate) và báo "điền tay".
# ---------------------------------------------------------------------------
MARK_LAST_CSS_JS = """
([css, marker]) => {
  const els = [...document.querySelectorAll(css)].filter(e => e.offsetParent !== null);  // bỏ dòng template ẩn
  document.querySelectorAll(`[data-l2m-mark="${marker}"]`).forEach(x => x.removeAttribute('data-l2m-mark'));
  if (!els.length) return false;
  els[els.length - 1].setAttribute('data-l2m-mark', marker);
  return true;
}
"""


def _last_visible(page: Page, css: str, marker: str):
    return page.locator(f'[data-l2m-mark="{marker}"]') if page.evaluate(MARK_LAST_CSS_JS, [css, marker]) else None


def _set_named(page: Page, name: str, value) -> bool:
    """Đặt giá trị ô theo name: select (cả select bị ẩn) / radio (click thật) / input."""
    loc = page.locator(f'[name="{name}"]')
    if not loc.count():
        return False
    first = loc.first
    tag = first.evaluate("e => e.tagName")
    if tag == "SELECT":
        return _set_select(first, str(value))
    if first.evaluate("e => e.type") == "radio":
        radio = page.locator(f'[name="{name}"][value="{value}"]')
        if radio.count() and radio.first.is_enabled():
            radio.first.click()
            return True
        return radio.count() > 0  # radio bị disabled nhưng đã đúng giá trị mặc định
    target = next((x for x in loc.all() if x.is_visible()), None)
    if target is not None:
        target.fill(str(value))
        return True
    # Ô ẩn (input hidden do JS của form quản lý): đặt giá trị trực tiếp + phát sự kiện change.
    return bool(first.evaluate("(e, v) => { e.value = v; e.dispatchEvent(new Event('change', {bubbles: true})); return e.value === v; }",
                               str(value)))


def _set_app_group_fields(page: Page, code: str, label: str, names: tuple[str, ...]) -> None:
    """Chọn app group trên header (tool reset về jmsa sau login) rồi ép đúng ô app group của form."""
    _select_app_group(page, code, label)
    for name in names:
        if page.locator(f'select[name="{name}"]').count() and _set_named(page, name, code):
            log(f"  ✓ {name} = {code}")


def _click_add_in(page: Page, scope_name: str, labels: list[str]) -> bool:
    """Bấm '+ Add' trong đúng mục (mỗi lần 1 nút — bấm 2 nút trong 1 lần làm trang treo)."""
    scope = _scope(page, scope_name, {"labels": labels})
    if scope is None:
        return False
    btn = scope.get_by_role("button", name=re.compile(r"\+?\s*Add", re.I))
    if not btn.count():
        return False
    btn.first.click()
    page.wait_for_timeout(300)
    return True


def _step(log_ok: str, fn, missing: list, key: str) -> bool:
    try:
        ok = bool(fn())
    except Exception as e:  # noqa: BLE001 — một bước lỗi không làm hỏng cả form
        log(f"  ⚠ {key}: {e}")
        ok = False
    mark = "✓" if ok else t("✗ CHƯA ĐIỀN ĐƯỢC — điền tay")
    log(f"  {mark} {log_ok}")
    if not ok:
        missing.append(key)
    return ok


def create_goods(ctx: BrowserContext, plan: dict, auto: dict, mode: str = "manual") -> dict:
    base = auto["nc_base_url"].rstrip("/")
    code, label = plan.get("app_group", "l2msa"), plan.get("app_group_label", "")
    price, name = plan["price_usd"], plan["name"][:NAME_MAX]
    page = new_page(ctx)
    log("\n=== " + t("Tạo gói {key} — {name} (giá {price})", key=plan["product_key"], name=name, price=price) + " ===")
    open_logged_in(page, f"{base}/MobileGoodsAdmin/goods/new")
    settle(page)
    _set_app_group_fields(page, code, label, ("goodsAppGroupCode", "appGroupCode"))
    missing: list[str] = []
    fields = load_fields()["goods_new"]

    def names():
        ok = all(_set_named(page, n, v) for n, v in (("goodsName", name), ("goodsDisplayName", name)))
        _set_named(page, "goodsDisplayDescription", plan["description"])
        return ok or (fill_field(page, "admin_name", fields["admin_name"], name)
                      and fill_field(page, "customer_name", fields["customer_name"], name))

    def base_price():
        if not _click_add_in(page, "base_price", ["Product base price"]):
            return False
        cur = _last_visible(page, 'select[name^="goodsBasicPricePolicyList"][name$=".currencyGroupId"]', "bp_cur")
        if cur is not None:
            _set_select(cur, str(CURRENCY_GROUP_CASH))
        box = _last_visible(page, 'input[name^="goodsBasicPricePolicyList"][name$=".goodsBasicPrice"]', "bp_val")
        return box is not None and (box.fill(str(price)) or True)

    def monetary_price():
        if not _click_add_in(page, "monetary_price", ["Or a monetary base price", "Monetary base price"]):
            return False
        cur = _last_visible(page, 'select[name^="goodsBasicCurrencyPricePolicyList"][name$=".currencyCode"]', "mp_cur")
        if cur is not None:
            _set_select(cur, "USD")
        box = _last_visible(page, 'input[type=text][name^="goodsBasicCurrencyPricePolicyList"][name$=".goodsBasicCurrencyPrice"]', "mp_val")
        return box is not None and (box.fill(str(price)) or True)

    def pg():
        # Dialog PG là jQuery UI ngay trong trang (không phải popup), control dùng id.
        scope = _scope(page, "store_key", {"labels": ["Store Product Key", "Store product key"]})
        modify = (scope or page).get_by_role("button", name=re.compile(r"Modify", re.I))
        if modify.count():
            modify.first.click()
        page.locator("#selectMobilePgCode").wait_for(state="attached", timeout=5000)
        _set_select(page.locator("#selectMobilePgCode"), "25")  # VNG Store
        page.locator("#pgGoodsKey").fill(plan["store_product_key"])
        page.locator("#paymentReputationScore").fill(str(plan["reputation_score"]))
        page.locator("#btnAddPg").click()
        page.wait_for_timeout(300)
        if page.locator("#btnEditPgListOkay").count():
            page.locator("#btnEditPgListOkay").click()
        return True

    def delivery():
        radio = page.locator('input[name="_isDeliveryConfirmation"][value="true"]')
        if radio.count():
            radio.first.click()  # phải click thật -> hidden isDeliveryConfirmation mới thành true
            hidden = page.locator('input[name="isDeliveryConfirmation"]')
            return not hidden.count() or hidden.first.input_value() == "true"
        return fill_field(page, "delivery_confirm", fields["delivery_confirm"], "Required")

    _step(t("Tên gói ×3 = {name}", name=name), names, missing, "names")
    _step(f"Product base price (Cash) = {price}", base_price, missing, "base_price")
    _step(f"Monetary base price (USD) = {price}", monetary_price, missing, "monetary_price")
    _step(f"PG VNG Store (25) · {plan['store_product_key']} · reputation {plan['reputation_score']}", pg, missing, "pg")
    _step("Need to delivery confirm = Required", delivery, missing, "delivery_confirm")
    for f in ("subscription", "inventory", "refund_unit"):  # thường đã đúng mặc định — điền lại cho chắc
        if f in fields:
            try:
                fill_field(page, f, fields[f], fields[f].get("option"))
            except Exception:  # noqa: BLE001
                pass

    if _has_jquery_fn(page, "addGoodsItem"):
        for it in plan["items"]:
            if not it.get("item_id"):
                missing.append(f"item:{it['excel_name']}")
                log("  ✗ " + t("{name} chưa có Item ID — bỏ qua, thêm tay", name=it["excel_name"]))
                continue
            page.evaluate("([id, grp, name, type]) => window.$.fn.addGoodsItem(id, grp, name, type)",
                          [int(it["item_id"]), code, it["item_name"], ITEM_TYPE_GAME])
            page.wait_for_timeout(400)
            qty = _last_visible(page, 'input[name^="itemList"][name$=".itemQuantity"]', "qty")
            if qty is None and page.evaluate(MARK_LAST_JS, ["quantity", "qty"]):
                qty = page.locator('[data-l2m-mark="qty"]')
            if qty is not None:
                qty.fill(str(it["quantity"]))
                log(f"  ✓ Item {it['item_id']} {it['item_name']} × {it['quantity']}")
            else:
                missing.append(f"quantity:{it['item_id']}")
                log("  " + t("✗ Đã thêm item {item_id} nhưng không thấy ô Quantity — điền tay {qty}",
                             item_id=it["item_id"], qty=it["quantity"]))
    else:
        missing.append("items")
        log("  " + t("✗ Không thấy $.fn.addGoodsItem trên trang — thêm item bằng tay"))

    submitted = _submit(page, mode, missing, "/goods/new")
    goods_id = find_goods_id(page, base, plan["store_product_key"], code) if submitted else None
    if goods_id:
        log(f"  → Product #{goods_id}")
    return {"product_key": plan["product_key"], "filled": [], "missing": missing, "submitted": submitted, "goods_id": goods_id}


def _submit(page: Page, mode: str, missing: list, url_part: str) -> bool:
    """Nút Register thật có id='submit-form' (tìm theo chữ 'Register' sẽ trúng nút trong dialog PG)."""
    if mode == "auto" and not missing:
        btn = page.locator("#submit-form")
        try:
            if btn.count():
                btn.click()
            else:
                click_button(page, "Register")
            ok = wait_until_left(page, url_part, timeout_s=60)
        except Exception:  # noqa: BLE001
            ok = False
    else:
        if mode == "auto":
            log("  " + t("⚠ Còn trường chưa điền được nên KHÔNG tự bấm Register."))
        log(t("⏸ Kiểm tra form trong trình duyệt rồi tự bấm Register. App đang chờ (tối đa 30 phút)..."))
        ok = wait_until_left(page, url_part)
    log("  " + (t("✓ Đã đăng ký.") if ok else t("✗ Chưa đăng ký (cửa sổ đóng hoặc hết giờ).")))
    return ok


def create_limit(ctx: BrowserContext, plan: dict, goods_id: str, auto: dict, mode: str = "manual") -> dict:
    """Giá trị select Limit Admin (skill §8c.9): limitUserType 3=Account · limitDurationUnitType 5=Week, 6=Month,
    3=Time, 9=Permanent · limitBaseDayOfWeek 2=Monday · limitTargetType 2=Product. Amount limit (limitScore) = 0.
    ⚠️ Renewal unit KHÔNG sửa được sau khi tạo — app luôn để bạn kiểm tra trước khi Register."""
    limit = plan.get("limit") or {}
    base = auto["nc_base_url"].rstrip("/")
    code, label = plan.get("app_group", "l2msa"), plan.get("app_group_label", "")
    name = plan["name"][:NAME_MAX]
    page = new_page(ctx)
    log("\n=== " + t("Tạo purchase limit cho {key} (Product #{goods_id})", key=plan["product_key"], goods_id=goods_id) + " ===")
    open_logged_in(page, f"{base}/MobileLimitAdmin/purchase/goodsgroup/new")
    settle(page)
    _set_app_group_fields(page, code, label, ("appGroupCode", "targetAppGroupCode", "goodsAppGroupCode"))
    missing: list[str] = []
    unit = limit.get("unit_code")
    values = [("limitName", name), ("limitDescription", name), ("limitTargetType", 2), ("limitType", 2),
              ("limitUserType", 3), ("limitDurationType", 1), ("limitQuantity", limit.get("amount")),
              ("limitScore", 0), ("limitBaseTimeType", 1)]
    if unit:
        values.append(("limitDurationUnitType", unit))
    if unit and unit != 9:  # Permanent không có số ngày / mốc thời gian
        values += [("limitDuration", limit.get("duration", 1)), ("limitBaseDayOfWeek", 2)]
    for field, value in values:
        if value is None:
            continue
        try:
            ok = _set_named(page, field, value)
        except Exception as e:  # noqa: BLE001 — một ô lỗi không làm dừng cả form
            log(f"  ⚠ {field}: {e}")
            ok = False
        if not ok and field in ("limitName", "limitQuantity", "limitDurationUnitType"):
            missing.append(field)
        log(f"  {'✓' if ok else '·'} {field} = {value}" + ("" if ok else " " + t("(không thấy ô)")))
    if not unit:
        missing.append("limitDurationUnitType")
        log("  " + t("✗ Chu kỳ '{period}' chưa có mã — chọn tay ô Renewal", period=limit.get("period")))
    log("  " + t("· Countries to Apply: để trống"))

    if _has_jquery_fn(page, "addGoods"):
        page.evaluate("([id, grp, name, cur]) => window.$.fn.addGoods(id, grp, name, name, cur)",
                      [int(goods_id), code, name, [CURRENCY_GROUP_CASH]])
        page.wait_for_timeout(400)
        weight = _last_visible(page, 'input[name*="eight"]', "w")
        if weight is None and page.evaluate(MARK_LAST_JS, ["weight", "w"]):
            weight = page.locator('[data-l2m-mark="w"]')
        if weight is not None:
            weight.fill("1")
        log("  " + t("✓ Thêm Product #{goods_id}, weight 1", goods_id=goods_id))
    else:
        missing.append("limited_product")
        log("  " + t("✗ Không thấy $.fn.addGoods — thêm product bằng tay"))

    submitted = _submit(page, mode, missing, "/goodsgroup/new")
    limit_id = find_limit_id(page, base, name, code, label) if submitted else None
    if limit_id:
        log(f"  → Limit {limit_id}")
    return {"product_key": plan["product_key"], "missing": missing, "submitted": submitted, "limit_id": limit_id}


def read_view(ctx: BrowserContext, url: str) -> dict:
    page = new_page(ctx)
    open_logged_in(page, url)
    settle(page)
    data = page.evaluate(KV_JS)
    return {"url": url, "kv": data["kv"], "text": data["text"]}


def _search_queries(name: str) -> list[str]:
    """Tên trong Excel hay lệch tên trên tool -> thử lần lượt: nguyên văn, bỏ (Bound)/(Khóa), bỏ mọi phần trong ngoặc,
    rồi chỉ 2 từ đầu (vd 'Fancy Soul Crystal' ra được 'Fancy Soul Crystal Stone ...')."""
    no_bound = re.sub(r"\s*\((bound|khóa|khoa)\)\s*", " ", name, flags=re.I).strip()
    base = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
    words = base.split()
    short = " ".join(words[:2]) if len(words) > 2 else ""
    return list(dict.fromkeys(q for q in (name, no_bound, base, short) if q))


NEXT_TEXTS = ("Next", "next", "›", ">", "다음")


def _next_page(page: Page, number: int) -> bool:
    """Sang trang kết quả tiếp theo: ưu tiên nút số trang, sau đó nút Next/›/>."""
    for text in (str(number), *NEXT_TEXTS):
        for role in ("link", "button"):
            loc = page.get_by_role(role, name=text, exact=True)
            if loc.count() and loc.first.is_visible() and loc.first.is_enabled():
                loc.first.click()
                settle(page, 1000)
                return True
    return False


def _max_page_size(page: Page) -> None:
    """Có ô chọn số dòng mỗi trang (10/20/50/100...) thì chọn số lớn nhất để đỡ phải lật trang."""
    for sel in page.locator("select").all():
        options = sel.evaluate(OPTIONS_JS)
        nums = [(int(v), v) for v, t in options if v.isdigit() and t.strip().isdigit() and int(v) >= 10]
        if len(nums) >= 2 and len(nums) == len(options):
            _set_select(sel, max(nums)[1])
            settle(page, 1000)
            log("  " + t("· Hiển thị {n} dòng mỗi trang", n=max(nums)[0]))
            return


def _dump_items_ui(ctx: BrowserContext, auto: dict, app_group: str, app_group_label: str = "", max_pages: int = 300) -> dict:
    """(Dự phòng) Tải danh sách item bằng cách bấm qua giao diện: tìm với tên trống, lật hết các trang."""
    base = auto["nc_base_url"].rstrip("/")
    page = new_page(ctx)
    open_logged_in(page, f"{base}/MobileGoodsAdmin/items")
    settle(page)
    if not _select_app_group(page, app_group, app_group_label):
        return {"_error": t("Không chọn được app group '{group}' trên trang Item lookup", group=app_group_label or app_group)}
    spec = {"labels": ["Item name (administrator)", "Item name", "Item Name"], "kind": "text"}
    fill_field(page, "item_search", spec, "")
    _max_page_size(page)
    search_btn = page.get_by_role("button", name=re.compile(r"^\s*(search|lookup|inquiry|조회|검색)\s*$", re.I))
    if search_btn.count():
        search_btn.first.click()
    else:
        page.locator('[data-l2m-scope="item_search"] input:visible').first.press("Enter")
    settle(page, 1500)
    all_rows, last_first = [], None
    for number in range(1, max_pages + 1):
        rows = [r for r in page.evaluate(TABLE_JS, True) if sum(1 for v in r.values() if str(v).strip()) > 1]
        first = json.dumps(rows[0], ensure_ascii=False, sort_keys=True) if rows else None
        if not rows or first == last_first:
            break
        last_first = first
        all_rows += rows
        if number % 10 == 0:
            log("  " + t("· Đã đọc {pages} trang, {rows} dòng", pages=number, rows=len(all_rows)))
        if not _next_page(page, number + 1):
            break
    log("  " + t("✓ Tải được {n} item", n=len(all_rows)))
    if not all_rows:
        log("  " + t("⚠ Tìm với tên trống không ra kết quả — tool có thể bắt buộc nhập điều kiện tìm"))
    return {"rows": all_rows}


def _item_lookup_ui(ctx: BrowserContext, auto: dict, names: list[str], app_group: str = "l2msa",
                    app_group_label: str = "") -> dict:
    """(Dự phòng) Tra item bằng cách điền ô Item name và bấm Search trên giao diện."""
    base = auto["nc_base_url"].rstrip("/")
    page = new_page(ctx)
    open_logged_in(page, f"{base}/MobileGoodsAdmin/items")
    settle(page)
    out: dict[str, dict] = {}
    spec = {"labels": ["Item name (administrator)", "Item name", "Item Name"], "kind": "text"}
    for name in names:
        if not _select_app_group(page, app_group, app_group_label):  # chọn lại mỗi lần — tool có thể reset sau khi tìm
            return {"_error": t("Không chọn được app group '{group}' trên trang Item lookup", group=app_group_label or app_group), **out}
        rows, used = [], name
        for query in _search_queries(name):
            if not fill_field(page, "item_search", spec, query):
                return {"_error": t("Không thấy ô 'Item name' trên trang Item lookup"), **out}
            search_btn = page.get_by_role("button", name=re.compile(r"^\s*(search|lookup|inquiry|조회|검색)\s*$", re.I))
            if search_btn.count():
                search_btn.first.click()
            else:
                page.locator('[data-l2m-scope="item_search"] input:visible').first.press("Enter")
            settle(page, 1500)
            rows = [r for r in page.evaluate(TABLE_JS, True)
                    if sum(1 for v in r.values() if str(v).strip()) > 1]  # bỏ dòng "There are no item details."
            used = query
            if rows:
                break
        out[name] = {"query": used, "rows": rows[:30]}
        log(f"  {name}: " + t("{n} kết quả", n=len(rows)) + (t(" (tìm theo '{query}')", query=used) if used != name else ""))
    return out


# ---------------------------------------------------------------------------
# Tra cứu bằng POST trực tiếp — cách đã chạy ổn định trong các phiên Cowork (skill package-creation §8c.7):
# POST vào /MobileGoodsAdmin/items | goods với mode=search + pageSize=100, truyền app group TƯỜNG MINH
# (tool tự nhảy về jmsa sau khi login — §8a), rồi parse HTML. Không phụ thuộc giao diện.
# ---------------------------------------------------------------------------
NAME_MAX = 40
SEARCH_BASE = {"pageIndex": "1", "naviSize": "10", "totalCount": "", "defaultRegion": "GMT+07;VN", "mode": "search",
               "pageSize": "100"}
POST_SEARCH_JS = """
async ([path, params]) => {
  const r = await fetch(path, {method: 'POST', body: new URLSearchParams(params), credentials: 'same-origin',
                               headers: {'Content-Type': 'application/x-www-form-urlencoded'}});
  const html = await r.text();
  const d = new DOMParser().parseFromString(html, 'text/html');
  const rows = [...d.querySelectorAll('table tr')].filter(tr => tr.cells.length >= 5)
    .map(tr => [...tr.cells].map(c => (c.getAttribute('title') || c.textContent || '').trim().replace(/\\s+/g, ' ')));
  return {status: r.status, rows, has_table: !!d.querySelector('table'),
          login: !!d.querySelector('input[type=password]')};
}
"""


def _post_search(page: Page, path: str, params: dict) -> dict:
    return page.evaluate(POST_SEARCH_JS, [path, {**SEARCH_BASE, **{k: str(v) for k, v in params.items()}}])


def _item_rows(rows: list[list[str]], app_group: str) -> list[dict]:
    """Dòng kết quả Item lookup: ô [1] = Item number, [3] = Item name, [4] = Item type; chỉ lấy dòng đúng app group."""
    out = []
    for cells in rows:
        if app_group and app_group not in " ".join(cells):
            continue
        item_id = cells[1] if len(cells) > 1 and cells[1].isdigit() else next((c for c in cells if c.isdigit()), None)
        name = cells[3] if len(cells) > 3 and cells[3] else max(cells, key=len)
        if item_id:
            out.append({"Item number": item_id, "Item name": name, "Item type": cells[4] if len(cells) > 4 else ""})
    return out


def search_items(page: Page, app_group: str, item_name: str = "", game_item_key: str = "", page_index: int = 1) -> dict:
    res = _post_search(page, "/MobileGoodsAdmin/items", {
        "itemId": "", "itemName": item_name[:NAME_MAX], "itemAppGroupCode": app_group, "gameItemKey": game_item_key,
        "pageIndex": page_index})
    return {**res, "items": _item_rows(res["rows"], app_group)}


def _open_items_page(ctx: BrowserContext, auto: dict) -> Page:
    page = new_page(ctx)
    open_logged_in(page, f"{auto['nc_base_url'].rstrip('/')}/MobileGoodsAdmin/items")
    settle(page)
    return page


def item_lookup(ctx: BrowserContext, auto: dict, names: list[str], app_group: str = "l2msa",
                app_group_label: str = "") -> dict:
    """Tra Item ID theo tên. Tên trên tool bị cắt ở 40 ký tự nên query luôn cắt còn 40, rồi thử các biến thể ngắn hơn."""
    page = _open_items_page(ctx, auto)
    probe = search_items(page, app_group, "Diamonds")
    if probe["status"] != 200 or probe["login"] or not probe["has_table"]:
        log("  " + t("⚠ Tra bằng POST không được (có thể phiên đăng nhập hết hạn) — chuyển sang bấm qua giao diện"))
        return _item_lookup_ui(ctx, auto, names, app_group, app_group_label)
    out: dict[str, dict] = {}
    for name in names:
        rows, used = [], name
        for query in dict.fromkeys(q[:NAME_MAX] for q in _search_queries(name)):
            rows, used = search_items(page, app_group, query)["items"], query
            if rows:
                break
        out[name] = {"query": used, "rows": rows[:30]}
        log(f"  {name}: " + t("{n} kết quả", n=len(rows)) + (t(" (tìm theo '{query}')", query=used) if used != name else ""))
    return out


def dump_items(ctx: BrowserContext, auto: dict, app_group: str, app_group_label: str = "", max_pages: int = 300) -> dict:
    """Tải toàn bộ item của app group: POST tìm với tên trống, 100 dòng/trang, lật pageIndex tới khi hết."""
    page = _open_items_page(ctx, auto)
    first = search_items(page, app_group, "", page_index=1)
    if first["status"] != 200 or first["login"] or not first["has_table"]:
        log("  " + t("⚠ Tra bằng POST không được — chuyển sang bấm qua giao diện"))
        return _dump_items_ui(ctx, auto, app_group, app_group_label, max_pages)
    items, seen = list(first["items"]), {r["Item number"] for r in first["items"]}
    for page_index in range(2, max_pages + 1):
        batch = [r for r in search_items(page, app_group, "", page_index=page_index)["items"] if r["Item number"] not in seen]
        if not batch:
            break
        items += batch
        seen.update(r["Item number"] for r in batch)
        if page_index % 5 == 0:
            log("  " + t("· Đã đọc {pages} trang, {n} item", pages=page_index, n=len(items)))
    log("  " + t("✓ Tải được {n} item của {group}", n=len(items), group=app_group))
    return {"rows": items}


def find_goods_id(page: Page, base: str, store_key: str, app_group: str = "l2msa") -> str | None:
    """Product number theo Store Product Key (pgGoodsKey) — POST search trên Product lookup, app group tường minh."""
    try:
        if "/MobileGoodsAdmin/" not in page.url:
            page.goto(f"{base}/MobileGoodsAdmin/goods", wait_until="domcontentloaded")
            settle(page)
        res = _post_search(page, "/MobileGoodsAdmin/goods", {
            "goodsId": "", "goodsName": "", "goodsAppGroupCode": app_group, "gameItemKey": "", "displayKey": "",
            "pgId": "", "pgGoodsKey": store_key})
        for cells in res["rows"]:
            if app_group in " ".join(cells):
                number = next((c for c in cells if re.fullmatch(r"\d{2,7}", c)), None)
                if number:
                    return number
    except Exception as e:  # noqa: BLE001
        log("  " + t("⚠ Không tự tìm được Product # ({error}) — nhập tay ở bước audit", error=e))
    return None


FIND_LIMIT_JS = """
async ([name]) => {
  const f = document.querySelector('form');
  const b = new URLSearchParams(f ? new FormData(f) : undefined);
  b.set('limitName', name); b.set('pageSize', '100'); b.set('mode', 'search');
  const r = await fetch(location.pathname, {method: 'POST', body: b, credentials: 'same-origin',
                                            headers: {'Content-Type': 'application/x-www-form-urlencoded'}});
  const d = new DOMParser().parseFromString(await r.text(), 'text/html');
  return [...d.querySelectorAll('tr')].map(t => t.textContent.replace(/\\s+/g, ' ').trim()).filter(x => x.includes(name));
}
"""


def find_limit_id(page: Page, base: str, limit_name: str, app_group: str, app_group_label: str = "") -> str | None:
    """GUID của limit theo tên. Trang Limit lookup lọc theo app group trên header -> chọn lại trước khi tìm."""
    try:
        page.goto(f"{base}/MobileLimitAdmin/purchase/goodsgroup", wait_until="domcontentloaded")
        settle(page)
        _select_app_group(page, app_group, app_group_label)
        for line in page.evaluate(FIND_LIMIT_JS, [limit_name]):
            m = re.search(r"[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}", line)
            if m:
                return m.group(0)
    except Exception as e:  # noqa: BLE001
        log("  " + t("⚠ Không tự tìm được Limit GUID ({error}) — nhập tay ở bước audit", error=e))
    return None


def inspect(ctx: BrowserContext, url: str) -> list[dict]:
    page = new_page(ctx)
    open_logged_in(page, url)
    settle(page)
    return page.evaluate(INSPECT_JS)


def calibrate(dump: list[dict], form: dict) -> dict:
    """Từ danh sách ô trên trang thật -> selector theo name/id cho từng trường logic."""
    def match(label_text: str, labels: list[str]) -> bool:
        t = norm(label_text)
        return any(t == norm(l) or t.startswith(norm(l) + " ") for l in labels)

    out = {}
    for field, spec in form.items():
        labels, kind = spec.get("labels", []), spec.get("kind", "text")
        # <select> của dropdown tuỳ biến bị ẩn nhưng vẫn là ô thật cần điền -> không lọc theo hiển thị.
        rows = [d for d in dump if (d["visible"] or d["tag"] == "select") and match(d["row_label"], labels)]
        chosen = None
        if kind == "text":
            chosen = next((d for d in rows if d["tag"] in ("input", "textarea") and d["type"] not in ("radio", "checkbox", "button", "submit")), None)
        elif kind == "select":
            chosen = next((d for d in rows if d["tag"] == "select"), None)
        else:
            chosen = next((d for d in rows if d["type"] == "radio" and norm(d["own_label"]) == norm(spec.get("option", ""))), None) \
                or next((d for d in rows if d["tag"] == "select"), None)
        if chosen:
            sel = f'#{chosen["id"]}' if chosen["id"] else f'[name="{chosen["name"]}"]'
            if chosen["type"] == "radio" and not chosen["id"]:
                sel += f'[value="{chosen["value"]}"]'
            out[field] = {"selector": sel}
    return out
