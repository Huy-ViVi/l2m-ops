"""Nhập lịch sử setup gói đã làm với Claude Cowork (skill package-creation) vào lịch sử của app.

Nguồn (thư mục 07_Package-Creation):
- SKILL.md §8d "Setup History": bảng gói webshop (Trigger 1) + các bảng NPID Key/Membership (Trigger 2)
- counter.md: lịch sử dùng số key/mem (bổ sung các đợt NPID không có trong SKILL.md)
- SKILL.md bảng "Item ID đã tra được" -> bổ sung vào bảng Item ID dùng chung
- outputs/YYYY-MM-DD_*.md: log chi tiết, đính kèm vào bản ghi cùng ngày
Chạy lại nhiều lần không tạo trùng (bỏ qua bản ghi cùng tiêu đề đã nhập).
"""
from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

from . import store

DEFAULT_DIR = Path(r"G:\Claude Cowork Checking\07_Package-Creation")
SOURCE = "cowork"


def _cells(line: str) -> list[str]:
    return [c.strip().strip("`").strip() for c in line.strip().strip("|").split("|")]


def _table_rows(lines: list[str], start: int) -> list[list[str]]:
    """Các dòng bảng markdown liền nhau bắt đầu từ `start` (bỏ dòng header và dòng ---)."""
    rows, i = [], start
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = _cells(lines[i])
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            rows.append(cells)
        i += 1
    return rows[1:] if rows else []  # dòng đầu là header


def parse_skill(text: str) -> tuple[list[dict], list[dict], list[dict]]:
    """-> (gói webshop theo dòng, các đợt NPID, item ID)."""
    lines = text.splitlines()
    webshop, npid, items = [], [], []
    for i, line in enumerate(lines):
        if line.startswith("| Date | Product #"):
            j = i + 2
            while j < len(lines) and (lines[j].strip().startswith("|") or not lines[j].strip()):
                if lines[j].strip().startswith("|"):
                    c = _cells(lines[j])
                    if len(c) >= 6 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", c[0]):
                        webshop.append({"date": c[0], "product": c[1].strip("*"), "name": c[2], "key": c[3],
                                        "items": c[4], "limit": c[5]})
                j += 1
                if j < len(lines) and lines[j].startswith("**Trigger 2"):
                    break
        m = re.match(r"\*\*Trigger 2 — (.+?) \((\d{4}-\d{2}-\d{2})\):\*\*\s*(.*)", line)
        if m:
            k = i + 1
            while k < len(lines) and not lines[k].strip().startswith("|"):
                k += 1
            rows = _table_rows(lines, k)
            npid.append({"title": m.group(1), "date": m.group(2), "scale": m.group(3).strip(),
                         "rows": [dict(zip(["Package", "Counter", "Item ID", "Price", "Products", "Limit"], r)) for r in rows]})
        if line.startswith("| Item | ID |"):
            for r in _table_rows(lines, i):
                if len(r) >= 2 and r[1].strip("*").isdigit():
                    items.append({"name": re.sub(r"\*+", "", r[0]).strip(), "id": int(r[1].strip("*")),
                                  "key": re.sub(r"\D", "", r[2]) if len(r) > 2 else ""})
    return webshop, npid, items


def parse_counter(text: str) -> list[dict]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("| Date | Type | Used N"):
            return [dict(zip(["date", "type", "n", "package"], r)) for r in _table_rows(lines, i) if len(r) >= 4]
    return []


def _clean_name(name: str) -> str:
    """'Scroll of Combat (Bound) — sheet ghi "Combat Scroll"' -> ('Scroll of Combat (Bound)', alias 'Combat Scroll')."""
    return re.split(r"\s+[—–]\s+", name)[0].replace("*(typo trong DB)*", "").strip()


def build_records(folder: Path) -> tuple[list[dict], list[dict]]:
    skill = (folder / "SKILL.md").read_text(encoding="utf-8")
    counter = (folder / "counter.md").read_text(encoding="utf-8") if (folder / "counter.md").exists() else ""
    webshop, npid, items = parse_skill(skill)
    logs = {p.name[:10]: p for p in sorted((folder / "outputs").glob("20??-??-??_*.md"))} if (folder / "outputs").exists() else {}
    records = []

    by_date: OrderedDict[str, list[dict]] = OrderedDict()
    for r in webshop:
        by_date.setdefault(r["date"], []).append(r)
    for date, rows in by_date.items():
        products = ", ".join(f"#{r['product']}" for r in rows)
        records.append({
            "date": date, "title": f"[Cowork] Setup {len(rows)} gói webshop trên NC ({products})",
            "summary": {"metrics": {"Gói": len(rows), "Loại": "Trigger 1 — webshop (VNG Store)"},
                        "tables": {"Gói đã setup": [{"Product #": r["product"], "Gói": r["name"], "Product Key": r["key"],
                                                     "Items (ID × SL)": r["items"], "Limit": r["limit"]} for r in rows]}},
            "log": logs.get(date)})

    covered = set()
    for batch in npid:
        covered.add(batch["date"])
        records.append({
            "date": batch["date"], "title": f"[Cowork] {batch['title']} — Key/Membership ({batch['scale']})",
            "summary": {"metrics": {"Gói gốc": len(batch["rows"]), "Quy mô": batch["scale"], "Loại": "Trigger 2 — 6 product / gói"},
                        "tables": {"Gói": batch["rows"]}},
            "log": logs.get(batch["date"])})

    # Đợt NPID chỉ có trong counter.md (vd 16/07, 08/09/2026)
    extra: OrderedDict[str, list[dict]] = OrderedDict()
    for r in parse_counter(counter):
        if r["date"] not in covered:
            extra.setdefault(r["date"], []).append(r)
    for date, rows in sorted(extra.items()):
        records.append({
            "date": date, "title": f"[Cowork] NPID Key/Membership {date} ({len(rows)} gói)",
            "summary": {"metrics": {"Gói gốc": len(rows), "Loại": "Trigger 2 — 6 product / gói"},
                        "tables": {"Gói": [{"Ngày": r["date"], "Loại": r["type"], "Số": r["n"], "Gói (product)": r["package"]} for r in rows]}},
            "log": logs.get(date)})

    item_rows = []
    for it in items:
        aliases = re.findall(r'sheet ghi "([^"]+)"', it["name"])
        item_rows.append({"id": it["id"], "name": _clean_name(it["name"]), "aliases": aliases, "key": it["key"]})
    return sorted(records, key=lambda r: r["date"]), item_rows


def import_folder(folder: Path, by: str, game: str = "l2m", dry_run: bool = False) -> dict:
    """Nhập vào CSDL. Trả về số bản ghi mới / đã có, số item mới."""
    records, item_rows = build_records(folder)
    existing = {a["title"] for a in store.list_activities(include_deleted=True, limit=100000, game=game) if a["source"] == SOURCE}
    new_records = [r for r in records if r["title"] not in existing]
    known_ids = {r["item_id"] for r in store.item_rows(game)}
    new_items = [it for it in item_rows if it["id"] not in known_ids]
    if not dry_run:
        for r in new_records:
            files = {r["log"].name: r["log"].read_bytes()} if r.get("log") else None
            store.add_activity("nc_setup", r["title"], r["summary"], by, files, note="Nhập từ lịch sử Claude Cowork (skill package-creation)",
                               status="done", source=SOURCE, game=game, created_at=f"{r['date']} 00:00:00")
        for it in new_items:
            store.upsert_item(it["id"], it["name"], it["aliases"], by, game, game_item_key=it["key"])
    return {"records": len(new_records), "skipped": len(records) - len(new_records), "items": len(new_items),
            "titles": [r["title"] for r in new_records]}
