"""Đọc file Excel master "All Product Information".

Sheet dùng: Item Mapping (nội dung gói), Webshop (giá theo thị trường), Webshop Packages Name & Des
(tên/mô tả), Timeline Selling (thời gian bán). Cột được dò theo tên header vì vị trí hay xê dịch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .excel import cell_text, find_col, find_header_row, find_sheet, get, norm, open_workbook, sheet_rows, to_number, tokens
from .i18n import t, tr_value


class Msg(str):
    """Thông báo cần giữ nguyên tiếng Việt khi ghi file / lưu lịch sử nhưng hiển thị theo ngôn ngữ giao diện
    (ghi chú gói của master, lý do loại / cảnh báo của case nạp lỗi). Giá trị chuỗi là bản tiếng Việt; tr() dịch."""

    template: str
    kw: dict

    def __new__(cls, template: str, **kw):
        obj = super().__new__(cls, template.format(**kw) if kw else template)
        obj.template, obj.kw = template, kw
        return obj

    @classmethod
    def t(cls, template: str, /, **kw) -> "Msg":
        """Tạo Msg từ chuỗi gốc có bản dịch (tên t để tests/test_i18n.py kiểm tra chuỗi gốc có trong core/locales)."""
        return cls(template, **kw)

    def tr(self) -> str:
        return t(self.template, **{k: tr(v) for k, v in self.kw.items()})


def tr(value):
    """Giá trị để hiển thị: Msg -> bản dịch; chuỗi khác -> bản dịch nếu trùng nguyên văn một chuỗi gốc."""
    return value.tr() if isinstance(value, Msg) else tr_value(value)


MARKETS = ["SG", "ID", "PH", "MY", "TH", "VN"]
SEA_MARKETS = ["SG", "ID", "PH", "MY", "TH"]
MARKET_ALIASES = {
    "VN": {"vn", "vnd", "vietnam"},
    "TH": {"th", "thb", "thai", "thailand"},
    "SG": {"sing", "sg", "sgd", "singapore"},
    "MY": {"my", "myr", "malaysia"},
    "PH": {"ph", "php", "philippines"},
    "ID": {"indo", "id", "idr", "indonesia"},
}
CURRENCY_BY_MARKET = {"VN": "VND", "TH": "THB", "SG": "SGD", "MY": "MYR", "PH": "PHP", "ID": "IDR"}
DIAMOND_NAMES = {"diamond", "diamonds", "diamond s"}


def short_key(key) -> str:
    """'com.ncv.l2m.web.item153' / 'Web.Item 153 ' -> 'web.item153' (master thật có key lẫn dấu cách).
    Bỏ tiền tố 'com.ncv.<game>.' của mọi game NCV."""
    s = re.sub(r"\s+", "", cell_text(key))
    s = re.sub(r"^com\.ncv\.[a-z0-9_]+\.", "", s, flags=re.I)
    return s.lower()


def key_variants(product_key: str) -> list[str]:
    """Các cách viết cùng một key: có/không tiền tố 'web.' (MyTool và master đôi khi khác nhau)."""
    k = short_key(product_key)
    return [k, k[4:]] if k.startswith("web.") else [k, "web." + k]


def looks_like_key(value) -> bool:
    s = short_key(value)
    return bool(re.match(r"^[a-z]+(\.[a-z0-9_]+)+$", s))


def markets_for(product_key: str) -> list[str]:
    """web.sa.* / sa.* -> 5 shop SEA, web.vn.* / vn.* -> VN, web.itemXXX -> cả 6 shop."""
    parts = short_key(product_key).split(".")
    if "sa" in parts[:-1]:
        return list(SEA_MARKETS)
    if "vn" in parts[:-1]:
        return ["VN"]
    return list(MARKETS)


def twin_key(product_key: str) -> str | None:
    """web.sa.key12 <-> web.vn.key12 (cùng số thường có nội dung y hệt)."""
    parts = short_key(product_key).split(".")
    for a, b in (("sa", "vn"), ("vn", "sa")):
        if a in parts[:-1]:
            parts[parts.index(a)] = b
            return ".".join(parts)
    return None


def _package_name(value) -> str:
    """Ô tên có thể là 'Hot deal⏎Weekly Top-up Class box' (dòng đầu là nhóm) -> lấy dòng cuối."""
    lines = [ln.strip() for ln in cell_text(value).splitlines() if ln.strip()]
    return lines[-1] if lines else ""


def _split_item(name: str, qty) -> tuple[str, float | None]:
    """Quantity trống nhưng số lượng nằm trong tên: '40 Diamonds', 'Diamonds x 20'."""
    if qty is not None:
        return name, qty
    m = re.match(r"^\s*([\d][\d,.]*)\s*[x×]?\s+(.+?)\s*$", name)
    if m and to_number(m.group(1)) is not None:
        return m.group(2), to_number(m.group(1))
    m = re.match(r"^\s*(.+?)\s*[x×]\s*([\d][\d,.]*)\s*$", name)
    if m and to_number(m.group(2)) is not None:
        return m.group(1), to_number(m.group(2))
    return name, None


@dataclass
class PackageItem:
    name: str
    quantity: float


@dataclass
class MasterPackage:
    product_key: str
    raw_key: str
    name: str
    price_usd: float | None = None
    purchase_limit: str = ""
    rebate: str = ""
    diamonds: int | None = None
    items: list[PackageItem] = field(default_factory=list)
    source: str = "Item Mapping"
    row: int = 0
    note: str = ""


class Master:
    """warnings viết theo ngôn ngữ giao diện lúc đọc file (bản cache phải tách theo ngôn ngữ); note của gói là Msg."""

    def __init__(self, src, timeline_start_row: int = 121):
        self.warnings: list[str] = []
        self.packages: dict[str, MasterPackage] = {}
        self.webshop: dict[str, dict] = {}
        self.names: dict[str, dict] = {}
        self.timeline: list[tuple[int, list]] = []
        self.timeline_header: list = []
        self.sheetnames: list[str] = []
        wb = open_workbook(src)
        try:
            self.sheetnames = list(wb.sheetnames)
            self._parse_item_mapping(wb)
            self._parse_webshop(wb)
            self._parse_names(wb)
            self._parse_timeline(wb, timeline_start_row)
        finally:
            wb.close()

    # ---- tra cứu --------------------------------------------------------
    def get(self, product_key: str) -> MasterPackage | None:
        """Item Mapping trước; không có thì thử bản sa/vn cùng số; cuối cùng dựng từ sheet Webshop/Name & Des."""
        k = short_key(product_key)
        for variant in key_variants(k):
            if variant in self.packages:
                return self.packages[variant]
        k = next((v for v in key_variants(k) if v in self.webshop or v in self.names), k)
        twin = twin_key(k)
        if twin and twin in self.packages:
            p = self.packages[twin]
            return MasterPackage(
                product_key=k, raw_key=product_key, name=p.name, price_usd=p.price_usd,
                purchase_limit=p.purchase_limit, rebate=p.rebate, diamonds=p.diamonds, items=p.items,
                source=f"Item Mapping (lấy theo {twin})", row=p.row,
                note=Msg.t("Không có {key} trong Item Mapping — dùng nội dung của {twin}", key=k, twin=twin),
            )
        if k in self.webshop or k in self.names:
            ws = self.webshop.get(k, {})
            return MasterPackage(
                product_key=k, raw_key=product_key, name=self.display_name(k) or ws.get("name", ""),
                price_usd=ws.get("price_usd"), source="Webshop / Name & Des", row=ws.get("row", 0),
                note=Msg.t("Không có trong Item Mapping — kiểm tra nội dung gói trong mô tả (Name & Des)"),
            )
        return None

    def display_name(self, product_key: str) -> str:
        variants = key_variants(product_key)
        k = next((v for v in variants if v in self.packages or v in self.names or v in self.webshop), variants[0])
        if k in self.packages and self.packages[k].name:
            return self.packages[k].name
        rec = self.names.get(k)
        if rec:
            for header, value in rec.items():
                words = tokens(header)
                if "name" in words and ({"en", "eng", "english"} & words) and value:
                    return cell_text(value)
            for header, value in rec.items():
                if "name" in tokens(header) and value:
                    return cell_text(value)
        return self.webshop.get(k, {}).get("name", "")

    def all_keys(self) -> list[str]:
        keys = list(self.packages) + [k for k in self.webshop if k not in self.packages]
        return keys

    # ---- parse từng sheet -----------------------------------------------
    def _parse_item_mapping(self, wb) -> None:
        ws = find_sheet(wb, "Item Mapping")
        if ws is None:
            self.warnings.append(t("Không thấy sheet '{sheet}'", sheet="Item Mapping"))
            return
        rows = sheet_rows(ws)
        h = find_header_row(rows, ["product key"])
        if h is None:
            self.warnings.append(t("{sheet}: không thấy header 'Product Key'", sheet="Item Mapping"))
            return
        header = rows[h]
        c_key = find_col(header, "product key", "product id")
        c_name = find_col(header, "package name", "packages name", "name")
        if c_name is None or c_name == c_key:
            c_name = 0
        c_price = find_col(header, "price", "price usd")
        c_limit = find_col(header, "purchase limit", "limit")
        c_items = find_col(header, "included items", "items", "item")
        c_qty = find_col(header, "quantity", "qty")
        c_rebate = find_col(header, "rebate")
        c_dia = find_col(header, "diamonds", "diamond")
        if c_items is None or c_qty is None:
            self.warnings.append(t("Item Mapping: không thấy cột Included Items / Quantity"))

        current: MasterPackage | None = None
        dia_col_values: dict[str, float] = {}
        for offset, row in enumerate(rows[h + 1:], start=h + 2):
            if not any(cell_text(c) for c in row):
                current = None  # dòng trống = hết block (bên dưới bảng còn bảng khác)
                continue
            key = get(row, c_key)
            if looks_like_key(key):
                k = short_key(key)
                current = MasterPackage(
                    product_key=k, raw_key=cell_text(key), name=_package_name(get(row, c_name)),
                    price_usd=to_number(get(row, c_price)), purchase_limit=cell_text(get(row, c_limit)),
                    rebate=cell_text(get(row, c_rebate)), row=offset,
                )
                if k in self.packages:
                    self.warnings.append(t("Item Mapping: {key} xuất hiện nhiều lần (dòng {row}) — dùng bản đầu tiên", key=k, row=offset))
                    current = None
                    continue
                self.packages[k] = current
                d = to_number(get(row, c_dia))
                if d is not None:
                    dia_col_values[k] = d
            elif cell_text(key) and current is not None:
                # Ô Product Key có chữ nhưng không phải key (vd tiêu đề nhóm) -> kết thúc block.
                current = None
                continue
            if current is None:
                continue
            item_name = cell_text(get(row, c_items))
            if item_name:
                item_name, qty = _split_item(item_name, to_number(get(row, c_qty)))
                current.items.append(PackageItem(item_name, qty if qty is not None else 0))
                if not current.purchase_limit:
                    current.purchase_limit = cell_text(get(row, c_limit))

        for k, p in self.packages.items():
            from_items = sum(i.quantity for i in p.items if norm(i.name) in DIAMOND_NAMES)
            if from_items:
                p.diamonds = int(from_items)
            elif k in dia_col_values:
                p.diamonds = int(dia_col_values[k])

    def _parse_webshop(self, wb) -> None:
        ws = None
        for name in wb.sheetnames:
            if norm(name) == "webshop":
                ws = wb[name]
                break
        if ws is None:
            self.warnings.append(t("Không thấy sheet '{sheet}'", sheet="Webshop"))
            return
        rows = sheet_rows(ws)
        h = find_header_row(rows, ["product key"])
        if h is None:
            self.warnings.append(t("{sheet}: không thấy header 'Product Key'", sheet="Webshop"))
            return
        header = rows[h]
        c_key = find_col(header, "product key", "product id")
        c_name = find_col(header, "package name", "packages name", "package", "name")
        c_usd = find_col(header, "price usd", "usd", "price")
        market_cols: dict[str, int] = {}
        for i, cell in enumerate(header):
            words = tokens(cell)
            # "Product ID" / "Package ID" không phải cột giá Indonesia.
            if i in (c_key, c_name) or words & {"product", "package", "key", "name", "item", "stt", "no"}:
                continue
            for market, aliases in MARKET_ALIASES.items():
                if market not in market_cols and words & aliases and i not in market_cols.values():
                    market_cols[market] = i
        if len(market_cols) < 6:
            missing = [m for m in MARKETS if m not in market_cols]
            self.warnings.append(t("Webshop: không dò được cột giá cho {markets}", markets=", ".join(missing)))
        for offset, row in enumerate(rows[h + 1:], start=h + 2):
            key = get(row, c_key)
            if not looks_like_key(key):
                continue
            k = short_key(key)
            if k in self.webshop:
                continue
            self.webshop[k] = {
                "name": cell_text(get(row, c_name)),
                "price_usd": to_number(get(row, c_usd)) if c_usd not in market_cols.values() else None,
                "prices": {m: to_number(get(row, c)) for m, c in market_cols.items()},
                "row": offset,
            }

    def _parse_names(self, wb) -> None:
        ws = find_sheet(wb, "Webshop Packages Name & Des", "Packages Name")
        if ws is None:
            self.warnings.append(t("Không thấy sheet '{sheet}'", sheet="Webshop Packages Name & Des"))
            return
        rows = sheet_rows(ws)
        h = find_header_row(rows, ["product key"])
        if h is None:
            h = find_header_row(rows, ["product id"])
        if h is None:
            self.warnings.append(t("{sheet}: không thấy header 'Product Key'", sheet="Name & Des"))
            return
        header = rows[h]
        c_key = find_col(header, "product key", "product id")
        for row in rows[h + 1:]:
            key = get(row, c_key)
            if not looks_like_key(key):
                continue
            k = short_key(key)
            self.names.setdefault(k, {
                cell_text(header[i]) or f"col{i + 1}": row[i] for i in range(min(len(header), len(row))) if i != c_key
            })

    def _parse_timeline(self, wb, start_row: int) -> None:
        ws = find_sheet(wb, "Timeline Selling", "Timeline")
        if ws is None:
            self.warnings.append(t("Không thấy sheet '{sheet}'", sheet="Timeline Selling"))
            return
        rows = sheet_rows(ws)
        h = find_header_row(rows, ["product"], scan=10)
        self.timeline_header = rows[h] if h is not None else (rows[0] if rows else [])
        for idx, row in enumerate(rows, start=1):
            if idx >= start_row and any(c not in (None, "") for c in row):
                self.timeline.append((idx, row))
