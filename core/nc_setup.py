"""Task 9 — Lập kế hoạch setup gói webshop trên NC Goods Admin + Limit Admin (Olive BillingV2).

Plan được dựng từ sheet Item Mapping, áp convention đã chốt (đối chiếu item152 = Product #793).
Plan là dict thuần để truyền sang tiến trình browser automation dưới dạng JSON.
"""
from __future__ import annotations

import difflib
import math
import re

from . import store
from .excel import norm
from .i18n import ai_language, t, tr_value
from .master import MasterPackage

STORE_KEY_PREFIX = "com.ncv.l2m."

FIXED_GOODS = [
    ("Store Product Key — PG", "VNG Store (value 25)"),
    ("Purchase type / Subscription", "General purchase / No"),
    ("Need to delivery confirm", "Required ⚠️"),
    ("Refund unit / Inventory / Delivery type", "Product / Not in use / Not used"),
    ("Valid date", "Mặc định (now → 2099-12-31 21:59:59)"),
    ("TriggerItemId", "None"),
    ("Sale status sau khi tạo", "Sale pending → bấm Start sale ở Product lookup để mở bán"),
]
FIXED_LIMIT = [
    ("Subject / Type", "Product / Purchase Limit"),
    ("Application Standard", "Account (limitUserType=3)"),
    ("Base Time Standard", "Base Time / Monday / 0"),
    ("Countries to Apply", "ĐỂ TRỐNG — không check nước nào"),
    ("Limited product", "Quantity weight 1"),
]
# Mã limitDurationUnitType trên Limit Admin (skill package-creation §8c): 3=Time(giờ), 5=Week, 6=Month, 9=Permanent.
PERIODS = {
    "daily": ("Day", None), "day": ("Day", None),
    "weekly": ("Week", 5), "week": ("Week", 5),
    "monthly": ("Month", 6), "month": ("Month", 6),
}
PERMANENT = ("Permanent", 9)
NAME_MAX = 40  # itemName / goodsName / goodsDisplayName trên NC tool tối đa 40 ký tự (dài hơn bị cắt im lặng)


def _num(value):
    if value is None:
        return None
    return int(value) if float(value).is_integer() else value


def setup_price(price_usd) -> int | None:
    """Giá setup trên tool = giá USD làm tròn LÊN số nguyên (19.99 -> 20), dùng cho Base price, Monetary price, Reputation."""
    return None if price_usd in (None, "") else math.ceil(float(price_usd) - 1e-9)


def parse_limit(text: str) -> dict | None:
    """Các cách ghi gặp trong master thật:
    '2 / Account / Weekly', '1 Time / Account / Daily', '2 Times / Account / Week', '1 / Account / Day' -> có chu kỳ;
    '1 / Account', '1 Time / Account' -> không gia hạn (giới hạn trọn đời); 'No' -> không giới hạn."""
    s = (text or "").strip()
    if norm(s) in ("", "no", "none", "no limit", "unlimited", "khong gioi han", "không giới hạn", "-"):
        return None
    m = re.match(r"^\s*(\d+)\s*(?:times?)?\s*/\s*([A-Za-z ]+?)\s*(?:/\s*([A-Za-z]+)\s*)?$", s, re.I)
    if not m:
        return {"raw": s, "error": t("Không hiểu Purchase Limit '{value}' — nhập tay", value=s)}
    amount, who, period = int(m.group(1)), m.group(2).strip().title(), m.group(3)
    if not period:
        # Không ghi chu kỳ = giới hạn trọn đời -> Permanent / 1 (như gói 500D Anniversary, product 963).
        return {"raw": s, "amount": amount, "user_type": who, "duration": 1, "period": PERMANENT[0], "unit_code": PERMANENT[1],
                "note": t("Không gia hạn → Permanent / 1")}
    unit = PERIODS.get(period.lower())
    if not unit:
        return {"raw": s, "error": t("Chu kỳ '{period}' chưa được hỗ trợ — nhập tay", period=period)}
    return {"raw": s, "amount": amount, "user_type": who, "duration": 1, "period": unit[0], "unit_code": unit[1]}


def item_key(name: str) -> str:
    # Master thật ghi lẫn '(Khóa)' và '(Bound)' cho cùng một item.
    return re.sub(r"\bkh[oó]a\b", "bound", norm(re.sub(r"['’]s\b", "", str(name or ""))))


def _strip_bound(key: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\bbound\b", "", key)).strip()


def is_wrong_tool_item(tool_name: str) -> bool:
    """Item trên tool được đánh dấu sai trong tên (vd 83 '... (Bound) Wrong') — không đưa vào ứng viên."""
    return bool(re.search(r"\bwrong\b", str(tool_name or ""), re.I))


class ItemCatalog:
    """Bảng Item ID dùng chung của team cho một game (CSDL data/app.db; Lineage2M nạp sẵn từ resources/item_ids.json)."""

    def __init__(self, game: str = "l2m"):
        self.game = game
        self.entries: list[dict] = [
            {"id": r["item_id"], "name": r["name"], "aliases": r["aliases"], "note": r.get("note", ""),
             "key": r.get("game_item_key", "")} for r in store.item_rows(game)
        ]
        self.blocked = store.blocked_items(game)
        # Danh sách item tải từ NC tool: tên trùng khớp hoàn toàn thì nhận luôn ID (bỏ item bị chặn, vd 83).
        self.tool_index = {item_key(ti["name"]): ti for ti in store.tool_items(game)
                           if ti["item_id"] not in self.blocked and not is_wrong_tool_item(ti["name"])}
        self._index()

    def _index(self):
        self.index: dict[str, dict] = {}
        for e in self.entries:
            for n in [e["name"], *e.get("aliases", [])]:
                self.index.setdefault(item_key(n), e)

    def lookup(self, name: str) -> dict:
        k = item_key(name)
        if k in self.index:
            e = self.index[k]
            how = "chính xác" if item_key(e["name"]) == k else "alias"
            return {"id": e["id"], "canonical": e["name"], "how": how, "confirmed": True, "note": e.get("note", "")}
        # Tên trên tool bị cắt ở 40 ký tự -> so cả tên đầy đủ lẫn 40 ký tự đầu.
        for kk in (k, item_key(str(name)[:NAME_MAX])):
            if kk in self.tool_index:
                ti = self.tool_index[kk]
                return {"id": ti["item_id"], "canonical": ti["name"], "how": "trùng tên trên tool", "confirmed": True}
        kb = _strip_bound(k)
        for key, e in self.index.items():
            if _strip_bound(key) == kb:
                return {"id": e["id"], "canonical": e["name"], "how": "gần đúng (khác Bound)", "confirmed": False}
        close = difflib.get_close_matches(k, list(self.index), n=1, cutoff=0.82)
        if close:
            e = self.index[close[0]]
            return {"id": e["id"], "canonical": e["name"], "how": "gần đúng (fuzzy)", "confirmed": False}
        return {"id": None, "canonical": "", "how": "chưa có", "confirmed": False}

    def learn(self, name: str, item_id: int, canonical: str | None = None, by: str = "local") -> None:
        """Ghi nhớ tên Excel -> Item ID vào bảng dùng chung (thêm alias nếu ID đã có)."""
        if any(e["id"] == int(item_id) for e in self.entries):
            store.add_alias(int(item_id), name, by, self.game)
        else:
            canonical = canonical or name
            store.upsert_item(int(item_id), canonical, [] if canonical == name else [name], by, self.game)
        self.__init__(self.game)

    def as_text(self) -> str:
        return "\n".join(f"{e['id']} | {e['name']}" for e in self.entries)


def build_plan(pkg: MasterPackage, catalog: ItemCatalog, app_group: str = "l2msa",
               store_prefix: str = STORE_KEY_PREFIX, app_group_label: str = "NCV-Lineage2M") -> dict:
    """app_group / store_prefix / app_group_label lấy từ hồ sơ game đang chọn."""
    items = []
    for it in pkg.items:
        look = catalog.lookup(it.name)
        items.append({
            "excel_name": it.name, "quantity": _num(it.quantity), "item_id": look["id"],
            "item_name": look["canonical"] or it.name, "match": look["how"], "confirmed": look["confirmed"],
            "note": look.get("note", ""),
        })
    price = setup_price(pkg.price_usd)
    return {
        "product_key": pkg.product_key,
        "store_product_key": (store_prefix or STORE_KEY_PREFIX) + pkg.product_key,
        "name": pkg.name,
        "description": pkg.name,
        "excel_price_usd": _num(pkg.price_usd),
        "price_usd": price,
        "reputation_score": price,
        "items": items,
        "purchase_limit_raw": pkg.purchase_limit,
        "limit": parse_limit(pkg.purchase_limit),
        "app_group": app_group,
        "app_group_label": app_group_label,
        "game": catalog.game,
        "diamonds": pkg.diamonds,
        "master_row": pkg.row,
    }


def validate_plan(plan: dict) -> list[str]:
    issues = []
    if not plan.get("name"):
        issues.append(t("Thiếu tên gói"))
    elif len(plan["name"]) > NAME_MAX:
        issues.append(t("Tên gói {n} ký tự > {max} — tool sẽ cắt im lặng. Rút gọn tên setup "
                        "(vd 901 dùng 'Einhasad Shirt Superb Blessing Pack')", n=len(plan["name"]), max=NAME_MAX))
    if plan.get("price_usd") in (None, ""):
        issues.append(t("Thiếu giá USD"))
    if not plan.get("items"):
        issues.append(t("Gói chưa có item nào"))
    for it in plan.get("items", []):
        if not it.get("item_id"):
            issues.append(t("Item '{name}' chưa có Item ID — tra Item lookup trên NC tool", name=it["excel_name"]))
        elif not it.get("confirmed"):
            issues.append(t("Item '{name}' khớp {match} với '{tool_name}' (ID {item_id}) — cần xác nhận",
                            name=it["excel_name"], match=tr_value(it["match"]), tool_name=it["item_name"], item_id=it["item_id"]))
        if not it.get("quantity") or float(it["quantity"]) <= 0:
            issues.append(t("Item '{name}' có Quantity không hợp lệ — đọc lại cột Quantity", name=it["excel_name"]))
    limit = plan.get("limit")
    if limit and limit.get("error"):
        issues.append(limit["error"])
    return issues


ITEM_MATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "matches": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "excel_name": {"type": "string"},
                    "item_id": {"type": "integer"},
                    "catalog_name": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "reason": {"type": "string"},
                },
                "required": ["excel_name", "item_id", "catalog_name", "confidence", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["matches"],
    "additionalProperties": False,
}


def ai_suggest_items(ai, names: list[str], catalog: ItemCatalog, game_name: str = "Lineage2M SEA",
                     app_group: str = "l2msa") -> list[dict]:
    system = (
        f"Bạn map tên item trong file Excel master của {game_name} sang Item ID trên NC Goods Admin (app group {app_group}). "
        "Chỉ được chọn ID có trong danh sách đã cho, tuyệt đối không bịa ID. Nếu không chắc, trả item_id = 0 và catalog_name rỗng. "
        "Lưu ý: tên Excel hay viết tắt (bỏ 's, bỏ chữ Stone); bản (Bound) và không Bound có thể là 2 item khác nhau — khi đó confidence tối đa medium. "
        f"Viết reason bằng {ai_language()}."
    )
    prompt = (
        "Danh sách Item ID đã biết (id | tên):\n" + catalog.as_text()
        + "\n\nTên item cần map:\n" + "\n".join(f"- {n}" for n in names)
    )
    data = ai.json(system, prompt, ITEM_MATCH_SCHEMA, effort="low")
    valid_ids = {e["id"] for e in catalog.entries}
    out = []
    for m in data.get("matches", []):
        if m.get("item_id") not in valid_ids:
            m["item_id"] = 0
        out.append(m)
    return out


_DROP = {"bound", "of", "the", "a"}


def _tokens(name: str) -> list[str]:
    return [("time" if tok == "times" else tok) for tok in item_key(name).split() if tok not in _DROP]


def similarity(excel_name: str, tool_name: str) -> float:
    """Độ giống tên Excel ↔ tên trên tool (0..1). Số (1 Time / 11 Times) phải khớp; khác Bound bị trừ điểm."""
    ta, tb = _tokens(excel_name), _tokens(tool_name)
    if not ta or not tb:
        return 0.0
    sa, sb = set(ta), set(tb)
    jaccard = len(sa & sb) / len(sa | sb)
    seq = difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()
    score = 0.6 * jaccard + 0.4 * seq
    if {tok for tok in sa if tok.isdigit()} != {tok for tok in sb if tok.isdigit()}:
        score *= 0.6
    if ("bound" in item_key(excel_name).split()) != ("bound" in item_key(tool_name).split()):
        score *= 0.9
    return round(score, 3)


def rank_tool_items(name: str, items: list[dict], n: int = 8, blocked: dict | None = None) -> list[dict]:
    """Ứng viên gần nhất trong danh sách item tải từ NC tool. Tên trên tool bị cắt ở 40 ký tự nên so cả
    tên đầy đủ lẫn 40 ký tự đầu; bỏ item bị chặn / có chữ 'Wrong'."""
    blocked = blocked or {}
    scored = [{"item_id": it["item_id"], "name": it["name"],
               "score": max(similarity(name, it["name"]), similarity(str(name)[:NAME_MAX], it["name"]))}
              for it in items if it["item_id"] not in blocked and not is_wrong_tool_item(it["name"])]
    return sorted((s for s in scored if s["score"] >= 0.3), key=lambda s: -s["score"])[:n]


RECENT_PACKAGES = 30  # "gói gần đây" = 30 gói cuối sheet Item Mapping (gói mới được thêm ở cuối)
USAGE_MIN_SCORE = 0.8  # gợi ý theo lịch sử gói chỉ xét ứng viên giống tên ít nhất chừng này


def item_usage(packages: dict[str, MasterPackage], catalog: ItemCatalog, exclude=()) -> tuple[dict[int, dict], float]:
    """Item ID -> {'count': số gói dùng, 'recent': số gói trong RECENT_PACKAGES gói cuối, 'last': gói gần nhất dùng nó,
    'ago': số gói thêm sau gói đó (0 = gói mới nhất)} theo thứ tự dòng Item Mapping, bỏ các gói trong `exclude` (đang setup).
    Chỉ đếm dòng item đã biết chắc ID (bảng Item ID / trùng tên trên tool); kèm tỉ lệ dòng item đã biết ID."""
    order = sorted((k for k in packages if k not in exclude), key=lambda k: packages[k].row)
    ids: dict[str, int | None] = {}
    usage: dict[int, dict] = {}
    known = total = 0
    for pos, k in enumerate(order):
        ago, found = len(order) - 1 - pos, set()
        for it in packages[k].items:
            if it.name not in ids:
                look = catalog.lookup(it.name)
                ids[it.name] = look["id"] if look["confirmed"] else None
            total += 1
            if ids[it.name]:
                known += 1
                found.add(ids[it.name])
        for item_id in found:
            u = usage.setdefault(item_id, {"count": 0, "recent": 0})
            u["count"] += 1
            u["recent"] += ago < RECENT_PACKAGES
            u["last"], u["ago"] = k, ago
    return usage, (known / total if total else 0.0)


def same_item_name(excel_name: str, tool_name: str) -> bool:
    """Cùng tên item, chỉ khác chữ thêm ở cuối (tool có '... (Bound) Old', '... (Bound) Nw'), cùng số lần, cùng Bound.
    'Greater Class Skin Card' không cùng tên với 'Greater Class Card' (chữ thêm ở giữa)."""
    a, b = _tokens(excel_name), _tokens(tool_name)
    n = min(len(a), len(b))
    return (n > 0 and a[:n] == b[:n] and {x for x in a if x.isdigit()} == {x for x in b if x.isdigit()}
            and ("bound" in item_key(excel_name).split()) == ("bound" in item_key(tool_name).split()))


def suggest_by_usage(name: str, cands: list[dict], usage: dict[int, dict]) -> dict | None:
    """Ứng viên nên dùng theo lịch sử gói: trong các item cùng tên (same_item_name, giống ≥ USAGE_MIN_SCORE), item có trong
    nhiều gói gần đây hơn thắng, rồi tới tổng số gói. Chỉ so item cùng tên: item khác tên mà hay dùng (vd 'Greater Class Skin
    Card' khi cần 'Greater Class Card') không được gợi ý. Không item cùng tên nào từng dùng -> None."""
    used = [c for c in cands if c["item_id"] in usage and c["score"] >= USAGE_MIN_SCORE and same_item_name(name, c["name"])]
    return max(used, key=lambda c: (usage[c["item_id"]]["recent"], usage[c["item_id"]]["count"], c["score"]), default=None)


PICK_SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "excel_name": {"type": "string"},
                    "item_id": {"type": "integer"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "reason": {"type": "string"},
                },
                "required": ["excel_name", "item_id", "confidence", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["picks"],
    "additionalProperties": False,
}


def ai_pick_items(ai, candidates: dict[str, list[dict]], game_name: str = "Lineage2M SEA") -> dict[str, dict]:
    """AI chọn item đúng trong các ứng viên THẬT trên NC tool cho từng tên Excel (không thể bịa ID)."""
    system = (
        f"Bạn khớp tên item trong file Excel master của {game_name} với item trên NC Goods Admin. "
        "Với mỗi tên, chỉ được chọn một item_id trong danh sách ứng viên của chính tên đó; không chắc thì item_id = 0. "
        "Excel hay viết tắt (bỏ 's, bỏ chữ Stone, gõ thiếu/thừa dấu cách). Bản (Bound) và không Bound là 2 item khác nhau; "
        "số lần trong ngoặc (1 Time, 6 Times, 11 Times) phải khớp đúng. "
        f"Viết reason bằng {ai_language()}."
    )
    blocks = []
    for name, cands in candidates.items():
        blocks.append(f"### {name}\n" + "\n".join(f"{c['item_id']} | {c['name']}" for c in cands))
    data = ai.json(system, "Ứng viên (id | tên trên tool):\n\n" + "\n\n".join(blocks), PICK_SCHEMA, effort="low")
    out = {}
    for p in data.get("picks", []):
        valid = {c["item_id"] for c in candidates.get(p.get("excel_name"), [])}
        if p.get("item_id") in valid:
            out[p["excel_name"]] = p
    return out


def lookup_candidates(rows: list[dict]) -> list[dict]:
    """Dòng kết quả trang Item lookup (header -> text) -> [{'item_id', 'name'}]. Dò cột theo tên header."""
    out = []
    for r in rows:
        item_id, name = None, ""
        for header, value in r.items():
            h, v = norm(header), str(value or "").strip()
            if item_id is None and ("number" in h or h in ("id", "item id", "no")) and re.fullmatch(r"\d+", v):
                item_id = int(v)
            elif not name and "name" in h and v:
                name = v
        if item_id is None:  # header không rõ -> ô toàn số đầu tiên
            item_id = next((int(v) for v in r.values() if re.fullmatch(r"\d+", str(v or "").strip())), None)
        if not name:
            name = max((str(v) for v in r.values() if not re.fullmatch(r"\d*", str(v or "").strip())), key=len, default="")
        if item_id is not None:
            out.append({"item_id": item_id, "name": name})
    return out


# ---------------------------------------------------------------------------
# Audit sau khi tạo (đối chiếu với nội dung trang view của tool)
# ---------------------------------------------------------------------------
def _kv_find(kv: dict, *labels: str) -> str | None:
    for label in labels:
        n = norm(label)
        for k, v in kv.items():
            if n in norm(k):
                return v
    return None


def audit_goods(plan: dict, kv: dict, text: str) -> list[dict]:
    """ok: True/False, hoặc None khi trang không đủ thông tin để kết luận (cần xem tay).
    Khoá dòng giữ tiếng Việt (lưu lịch sử, đọc lại "Kết quả"); common.df dịch tiêu đề cột khi hiển thị."""
    page = text or ""
    res = []

    def add(field, expected, ok, found=""):
        res.append({"Trường": field, "Kỳ vọng": str(expected), "Kết quả": "✅" if ok else ("❌" if ok is False else "❔"), "Thấy trên tool": found})

    n = page.count(plan["name"])
    add(t("Tên gói (admin/customer/description)"), f"{plan['name']} ×3", n >= 3 if n else False, t("xuất hiện {n} lần", n=n))
    add("Store Product Key", plan["store_product_key"], plan["store_product_key"] in page)
    score = _kv_find(kv, "reputation")
    add("Payment Reputation Score", plan["reputation_score"],
        None if score is None else str(plan["reputation_score"]) in score, score or "")
    price = _kv_find(kv, "base price")
    add("Base price Cash/USD", plan["price_usd"], None if price is None else str(plan["price_usd"]) in price, price or "")
    dc = _kv_find(kv, "delivery confirm")
    add("Need to delivery confirm", "Required",
        None if dc is None else ("required" in dc.lower() and "not" not in dc.lower()) or dc.strip().lower() == "true", dc or "")
    for it in plan["items"]:
        found = re.search(rf"(?<!\d){it['item_id']}(?!\d)", page) is not None
        add(f"Item {it['item_name']}", f"ID {it['item_id']} × {it['quantity']}", found if found else False,
            t("có ID trên trang") if found else t("không thấy ID"))
    status = _kv_find(kv, "sale status")
    add("Sale status", "Sale pending / On sale", None if status is None else bool(status.strip()), status or "")
    return res


def audit_limit(plan: dict, goods_id: str, kv: dict, text: str) -> list[dict]:
    page = text or ""
    limit = plan.get("limit") or {}
    res = []

    def add(field, expected, ok, found=""):
        res.append({"Trường": field, "Kỳ vọng": str(expected), "Kết quả": "✅" if ok else ("❌" if ok is False else "❔"), "Thấy trên tool": found})

    add("Limit name", plan["name"], plan["name"] in page)
    add("Subject / Type", "Product / Purchase Limit", "Purchase Limit" in page)
    add("Application Standard", "Account", "Account" in page)
    add("Renewal", f"{limit.get('duration', 1)} {limit.get('period', '')}", (limit.get("period") or "") in page)
    amount = _kv_find(kv, "limit amount", "amount")
    add("Limit amount", limit.get("amount"), None if amount is None else str(limit.get("amount")) in amount, amount or "")
    add("Base time", "Monday 0h", "Monday" in page)
    countries = _kv_find(kv, "countries", "country")
    add("Countries to Apply", t("(trống)"), None if countries is None else not countries.strip(), countries or "")
    add("Product", f"#{goods_id}", bool(goods_id) and re.search(rf"(?<!\d){goods_id}(?!\d)", page) is not None)
    return res
