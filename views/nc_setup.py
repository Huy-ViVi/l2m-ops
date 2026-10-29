import json

import streamlit as st

from core import config, store
from core import nc_setup as nc
from core.ai import AIError
from core.i18n import t, tr_value
from core.master import short_key
from ui import auth, common

common.page_header(t("🛒 Tạo gói nạp trên NC tool"),
                   t("Item Mapping → plan Goods Admin + Limit Admin → điền form (bạn duyệt & bấm Register) → audit"))
settings = config.load_settings()
auto = settings["automation"]
base = auto["nc_base_url"].rstrip("/")
g = common.game()
gid, app_group = g["id"], g["nc_app_group"]


def K(name: str) -> str:
    """Khoá session theo game — đổi game không lẫn plan / kết quả của game khác."""
    return f"{name}_{gid}"


nc_ok = common.reachability_warning(base, "NC tool (RC)")
if not app_group or not g["store_key_prefix"]:
    st.warning(t("Game **{name}** chưa khai báo đủ app group / tiền tố Store Product Key. "
                 "Admin vào **Cài đặt → Game** để bổ sung (có nút lấy danh sách app group từ NC tool).", name=g["name"]), icon="🎮")
    nc_ok = False

master = common.master_widget("nc")
if master is None:
    st.stop()
catalog = nc.ItemCatalog(gid)


def _plan_rows(plans: dict) -> list[dict]:
    """Bảng tóm tắt plan để lưu vào lịch sử (khoá cột tiếng Việt, common.df dịch khi hiển thị)."""
    return [{
        "Gói": k, "Tên": p["name"], "Store Product Key": p["store_product_key"], "Giá USD": p["price_usd"],
        "Items": "; ".join(f"{it['item_id']} {it['item_name']} × {it['quantity']}" for it in p["items"]),
        "Limit": (p.get("limit") or {}).get("raw") or "—",
    } for k, p in plans.items()]


def _reset_item_editors(plans: dict) -> None:
    for k in plans:
        st.session_state.pop(K(f"nc_items_{k}"), None)


def _reset_pickers(names) -> None:
    """Ô chọn item nhận lại lựa chọn mặc định — sau khi ứng viên đổi (tra / tải danh sách) hoặc AI vừa gợi ý."""
    for name in names:
        st.session_state.pop(K(f"lk_{name}"), None)


# ---- 1. Chọn gói -------------------------------------------------------------
st.subheader(t("1. Chọn gói cần setup"))
options = list(master.packages)
c1, c2 = st.columns([3, 2])
picked = c1.multiselect(t("Gói trong Item Mapping"), options,
                        format_func=lambda k: f"{k} — {master.packages[k].name}", key=K("nc_pick"))
pasted = c2.text_area(t("Hoặc dán Product Key (mỗi dòng 1 key)"), height=100, key=K("nc_paste"))
keys = list(dict.fromkeys(picked + [short_key(x) for x in pasted.replace(",", "\n").split() if x.strip()]))
unknown = [k for k in keys if k not in master.packages]
if unknown:
    st.error(t("Không có trong Item Mapping: {keys} — kiểm tra lại key hoặc tải master mới nhất.", keys=", ".join(unknown)))
keys = [k for k in keys if k in master.packages]

plans: dict = st.session_state.setdefault(K("nc_plans"), {})
for k in keys:
    if k not in plans:
        plans[k] = nc.build_plan(master.packages[k], catalog, app_group, g["store_key_prefix"], g["nc_app_group_label"])
for k in list(plans):
    if k not in keys:
        del plans[k]
if not plans:
    st.info(t("Chọn ít nhất một gói."))
    st.stop()

with st.expander(t("Convention cố định (áp cho mọi gói)")):
    a, b = st.columns(2)
    a.markdown("**Goods Admin**")
    a.table(common.df([{"Trường": "App group", "Giá trị": f"{g['nc_app_group_label'] or app_group} ({app_group})"}]
                      + [{"Trường": f, "Giá trị": v} for f, v in nc.FIXED_GOODS]))
    b.markdown("**Limit Admin**")
    b.table(common.df([{"Trường": f, "Giá trị": v} for f, v in nc.FIXED_LIMIT]))

# ---- 2. Duyệt plan -------------------------------------------------------------
st.subheader(t("2. Duyệt plan từng gói"))
for k, plan in plans.items():
    issues = nc.validate_plan(plan)
    with st.expander(f"{'✅' if not issues else '⚠️'} {k} — {plan['name']}", expanded=bool(issues)):
        # Tên trên tool tối đa 40 ký tự (dài hơn bị cắt im lặng) -> cho sửa tên setup ngay tại đây.
        st.session_state.setdefault(K(f"nc_name_{k}"), plan["name"])
        new_name = st.text_input(t("Tên setup trên tool (tối đa {max} ký tự; tên Excel: {excel})",
                                   max=nc.NAME_MAX, excel=master.packages[k].name), key=K(f"nc_name_{k}"))
        plan["name"] = plan["description"] = new_name.strip()
        if len(plan["name"]) > nc.NAME_MAX:
            st.caption(t("⚠ {n} ký tự — tool sẽ cắt thành: “{cut}”", n=len(plan["name"]), cut=plan["name"][:nc.NAME_MAX]))
        limit = plan.get("limit")
        if not limit:
            limit_text = t("Không giới hạn — không tạo limit")
        elif limit.get("error"):
            limit_text = limit["error"]
        elif not limit.get("period"):
            limit_text = t("{amount} / {user_type} / không gia hạn — {note}",
                           amount=limit["amount"], user_type=limit["user_type"], note=limit["note"])
        else:
            limit_text = (f"{limit['amount']} / {limit['user_type']} / {limit['duration']} {limit['period']}"
                          + (f" (unit={limit['unit_code']})" if limit.get("unit_code") else ""))
        st.table(common.df([
            {"Trường": "Product name (admin/customer) + Description", "Giá trị": plan["name"]},
            {"Trường": "Store Product Key", "Giá trị": f"VNG Store (25) — {plan['store_product_key']}"},
            {"Trường": "Payment Reputation Score", "Giá trị": str(plan["reputation_score"])},
            {"Trường": "Base price (Cash) / Monetary base price (USD)",
             "Giá trị": t("{price} / {price} USD (Excel ${excel} → làm tròn lên)", price=plan["price_usd"],
                          excel=plan.get("excel_price_usd"))},
            {"Trường": "Purchase Limit (master)", "Giá trị": plan["purchase_limit_raw"] or "—"},
            {"Trường": t("Limit sẽ tạo"), "Giá trị": limit_text},
            {"Trường": t("Diamonds trong gói"), "Giá trị": str(plan.get("diamonds"))},
            {"Trường": t("Dòng trong master"), "Giá trị": str(plan.get("master_row"))},
        ]))
        st.markdown(t("**Item composition** — sửa trực tiếp Item ID / Quantity nếu cần, tick *Xác nhận* khi đã chắc chắn"))
        # Bảng đọc lại theo tên cột -> không dịch tự động; cột "Cách khớp" chỉ dịch để hiển thị, dữ liệu giữ nhãn gốc.
        originals = plan["items"]
        edited = st.data_editor(
            common.df([{**it, "match": tr_value(it.get("match"))} for it in originals], translate=False),
            key=K(f"nc_items_{k}"), hide_index=True, width="stretch",
            disabled=["excel_name", "match", "note"],
            column_config={
                "excel_name": st.column_config.TextColumn(t("Tên trong Excel")),
                "quantity": st.column_config.NumberColumn("Quantity", min_value=0),
                "item_id": st.column_config.NumberColumn("Item ID", min_value=1, step=1),
                "item_name": st.column_config.TextColumn(t("Tên item trên tool")),
                "match": st.column_config.TextColumn(t("Cách khớp")),
                "confirmed": st.column_config.CheckboxColumn(t("Xác nhận")),
                "note": st.column_config.TextColumn(t("Ghi chú")),
            },
        )
        new_items = []
        for i, row in enumerate(edited.to_dict("records")):
            if i < len(originals):
                row["match"] = originals[i].get("match")
            row["item_id"] = int(row["item_id"]) if row.get("item_id") == row.get("item_id") and row.get("item_id") else None
            q = row.get("quantity")
            row["quantity"] = (int(q) if float(q).is_integer() else float(q)) if q == q and q is not None else None
            row["confirmed"] = bool(row.get("confirmed"))
            new_items.append(row)
        plan["items"] = new_items
        for it in new_items:
            if it.get("note"):
                st.info(f"Item {it['item_id']} — {it['note']}", icon="📌")
        for issue in nc.validate_plan(plan):
            st.write("⚠ " + issue)

pending = [(k, it) for k, p in plans.items() for it in p["items"] if not it.get("confirmed")]
pending_names = list(dict.fromkeys(it["excel_name"] for _, it in pending))
group_label = g["nc_app_group_label"] or app_group
tool_list = store.tool_items(gid)
n_tool, tool_updated = store.tool_items_info(gid)
# Item nào đã nằm trong bao nhiêu gói trước đó (master hiện tại, trừ các gói đang setup) -> gợi ý ⭐ ở ô chọn item.
usage, known_share = nc.item_usage(master.packages, catalog, exclude=plans) if pending_names else ({}, 0.0)

st.markdown(t("**Tìm Item ID cho các item chưa xác nhận**"))
st.caption(t("Danh sách item {group} đã tải từ NC tool: **{n}** item", group=group_label, n=n_tool)
           + (t(" (cập nhật {at})", at=tool_updated) if tool_updated else t(" — chưa tải")) + ". "
           + t("Tên trong Excel hay khác tên trên tool, nên app so khớp gần đúng với danh sách này; AI chỉ chọn trong các item thật đó."))
if pending_names:
    st.caption(t("Cạnh mỗi item là số gói trong master đã dùng nó và gói gần nhất (gói mới thêm ở cuối sheet Item Mapping). "
                 "⭐ = nên dùng: trong các item cùng tên, item có trong nhiều gói gần đây nhất. "
                 "Chỉ đếm được dòng item app đã biết Item ID ({pct:.0%} dòng trong master) — tải danh sách item từ NC tool để đếm đủ hơn.",
                 pct=known_share))
c1, c2, c3 = st.columns(3)
if c1.button(t("📥 Tải danh sách item từ NC tool ({group})", group=group_label), disabled=not auth.automation_allowed() or not nc_ok,
             help=t("Tìm với tên trống rồi lật hết các trang kết quả. Chạy lại khi tool có item mới.")):
    res = common.run_job("nc_item_dump", {}, t("Đang tải danh sách item"))
    if res and res.get("ok"):
        n = store.save_tool_items(gid, nc.lookup_candidates(res["rows"]))
        fresh = nc.ItemCatalog(gid)
        auto_matched = 0
        for p in plans.values():  # item chưa xác nhận mà trùng tên trên tool -> nhận luôn
            for it in p["items"]:
                look = fresh.lookup(it["excel_name"])
                if not it.get("confirmed") and look["confirmed"]:
                    it.update(item_id=look["id"], item_name=look["canonical"], match=look["how"], confirmed=True)
                    auto_matched += 1
        _reset_item_editors(plans)
        _reset_pickers(pending_names)
        common.flash(t("Đã lưu {n} item của {group}. Tự khớp được {matched} item trùng tên.", n=n, group=group_label, matched=auto_matched))
        st.rerun()
if c2.button(t("🔎 Tra riêng {n} item trên NC tool", n=len(pending_names)),
             disabled=not pending or not auth.automation_allowed() or not nc_ok):
    res = common.run_job("nc_item_lookup", {"names": pending_names}, t("Đang tra Item lookup"))
    if res and res.get("results"):
        st.session_state[K("nc_lookup")] = res["results"]
        found = [c for r in res["results"].values() for c in nc.lookup_candidates(r.get("rows", []))]
        store.save_tool_items(gid, found)  # kết quả tra được cũng thành dữ liệu so khớp cho lần sau
        _reset_pickers(pending_names)
if not auth.automation_allowed():
    st.caption("ℹ️ " + common.automation_reason())

lookup = st.session_state.get(K("nc_lookup"), {})
candidates: dict[str, list[dict]] = {}
for name in pending_names:
    merged: dict[int, dict] = {}
    for c in nc.lookup_candidates(lookup.get(name, {}).get("rows", [])):
        if c["item_id"] in catalog.blocked or nc.is_wrong_tool_item(c["name"]):
            continue
        merged[c["item_id"]] = {**c, "score": max(nc.similarity(name, c["name"]), nc.similarity(name[:nc.NAME_MAX], c["name"]), 0.5)}
    for c in nc.rank_tool_items(name, tool_list, blocked=catalog.blocked):
        merged.setdefault(c["item_id"], c)
    candidates[name] = sorted(merged.values(), key=lambda c: -c["score"])[:8]

if c3.button(t("🤖 AI chọn giúp ({n} item có ứng viên)", n=sum(1 for v in candidates.values() if v)),
             disabled=not any(candidates.values())):
    ai = common.ai_client()
    if ai:
        try:
            with st.spinner(t("Đang hỏi {ai}...", ai=ai.label)):
                picks = nc.ai_pick_items(ai, {n: c for n, c in candidates.items() if c}, g["name"])
            st.session_state[K("nc_ai_picks")] = picks
            _reset_pickers(candidates)
        except AIError as e:
            st.error(str(e))
ai_picks = st.session_state.get(K("nc_ai_picks"), {})


def _usage_text(item_id: int) -> str:
    u = usage.get(item_id)
    return t("{n} gói, gần nhất {key}", n=u["count"], key=u["last"]) if u else t("chưa gói nào dùng")


def _candidate_label(item_id: int, by_id: dict[int, dict], ai_pick: dict | None, suggested: dict | None) -> str:
    if not item_id:
        return t("— chưa chọn —")
    c = by_id[item_id]
    return (("⭐ " if suggested and suggested["item_id"] == item_id else "")  # đầu dòng: ô hẹp cắt mất phần cuối
            + t("{item_id} — {name}  ·  giống {score:.0%}", item_id=item_id, name=c["name"], score=c["score"])
            + "  ·  " + _usage_text(item_id)
            + (t("  ·  🤖 AI chọn") if ai_pick and ai_pick["item_id"] == item_id else ""))


def _usage_note(name: str, cands: list[dict], suggested: dict, exact: int) -> str:
    """Vì sao ⭐: gói nào đã dùng item đó; item cùng tên nào chưa gói nào dùng; ⭐ khác item trùng tên thì nhắc kiểm tra."""
    u = usage[suggested["item_id"]]
    note = t("⭐ Nên dùng **{item_id}**: có trong {n} gói của master ({recent} gói trong {window} gói gần nhất). "
             "Gói gần nhất dùng nó: {key} — {package}", item_id=suggested["item_id"], n=u["count"], recent=u["recent"],
             window=nc.RECENT_PACKAGES, key=u["last"], package=master.packages[u["last"]].name)
    note += t(" (gói mới nhất).") if u["ago"] == 0 else t(" ({n} gói trước).", n=u["ago"])
    unused = [str(c["item_id"]) for c in cands if c["item_id"] not in usage and c["score"] >= nc.USAGE_MIN_SCORE
              and nc.same_item_name(name, c["name"])]
    if unused:
        note += t(" Cùng tên nhưng chưa gói nào dùng: {ids}.", ids=", ".join(unused))
    if exact and exact != suggested["item_id"]:
        note += t(" ⚠ Khác item trùng tên **{item_id}** — kiểm tra kỹ trước khi chọn.", item_id=exact)
    return note


choices = {}
for name in pending_names:
    cands = candidates[name]
    with st.container(border=True):
        st.markdown(f"**{name}**" + (t(" · đã tra theo “{query}”", query=lookup[name]["query"])
                                     if name in lookup and lookup[name].get("query") not in (None, name) else ""))
        if not cands:
            st.caption(t("Chưa có ứng viên. Tải danh sách item hoặc tra riêng trên NC tool; vẫn không ra thì nhập Item ID tay ở bảng item phía trên."))
            continue
        by_id = {c["item_id"]: c for c in cands}
        ai_pick = ai_picks.get(name)
        exact = next((c["item_id"] for c in cands if nc.item_key(c["name"]) == nc.item_key(name)), 0)
        by_ai = ai_pick["item_id"] if ai_pick and ai_pick["item_id"] in by_id else 0
        suggested = nc.suggest_by_usage(name, cands, usage)
        default = (exact or by_ai or (suggested or {}).get("item_id")
                   or (cands[0]["item_id"] if cands[0]["score"] >= 0.9 else 0))
        # Giá trị là Item ID chứ không phải vị trí: danh sách ứng viên đổi thứ tự thì lựa chọn cũ vẫn trỏ đúng item.
        options = [0, *by_id]
        pick = st.selectbox(t("Item trên tool"), options, index=options.index(default), key=K(f"lk_{name}"),
                            format_func=lambda i, c=by_id, a=ai_pick, s=suggested: _candidate_label(i, c, a, s))
        if suggested:
            st.caption(_usage_note(name, cands, suggested, exact))
        if ai_pick:
            st.caption(f"🤖 AI ({ai_pick['confidence']}): {ai_pick['reason']}")
        if pick:
            choices[name] = by_id[pick]
if choices and st.button(t("✅ Áp dụng {n} Item ID đã chọn", n=len(choices)), type="primary"):
    for p in plans.values():
        for it in p["items"]:
            c = choices.get(it["excel_name"])
            if c and not it.get("confirmed"):
                it.update(item_id=c["item_id"], item_name=c["name"], match="Tool (đã chọn)", confirmed=True)
    _reset_item_editors(plans)
    st.session_state.pop(K("nc_lookup"), None)
    st.session_state.pop(K("nc_ai_picks"), None)
    common.flash(t("Đã áp dụng {n} Item ID. Bấm 'Lưu Item ID… vào bảng dùng chung' để cả team dùng lại.", n=len(choices)))
    st.rerun()

to_learn = [it for p in plans.values() for it in p["items"]
            if it.get("confirmed") and it.get("item_id") and it["match"] not in ("chính xác", "alias")]
if st.button(t("💾 Lưu {n} Item ID đã xác nhận vào bảng dùng chung", n=len(to_learn)), disabled=not to_learn or not auth.can_run()):
    for it in to_learn:
        catalog.learn(it["excel_name"], int(it["item_id"]), it.get("item_name") or it["excel_name"], by=auth.username())
        it["match"] = "alias"
    st.success(t("Đã lưu vào bảng Item ID của {game} — từ giờ app (và cả team) sẽ tự nhận các item này.", game=g["name"]))

# ---- 3. Setup trên tool ----------------------------------------------------------
st.subheader(t("3. Setup trên NC tool"))
blocking = {k: v for k, v in ((k, nc.validate_plan(p)) for k, p in plans.items()) if v}
if blocking:
    st.warning(t("Còn {n} vấn đề ở {packages} gói — xử lý xong mới setup được.",
                 n=sum(len(v) for v in blocking.values()), packages=len(blocking)))
plan_json = json.dumps(list(plans.values()), ensure_ascii=False, indent=2)
st.download_button(t("⬇ Tải plan (JSON)"), data=plan_json, file_name=f"nc-setup-plan-{gid}.json", mime="application/json")
if auth.can_run() and st.button(t("📝 Lưu plan vào lịch sử (nháp — chưa setup)")):
    aid, msg = common.record("nc_setup", t("Plan setup {n} gói: {keys}", n=len(plans), keys=", ".join(plans)),
                             {"metrics": {"Gói": len(plans), "Vấn đề còn lại": sum(len(v) for v in blocking.values())},
                              "tables": {"Plan": _plan_rows(plans)}, "plans": list(plans.values())},
                             {"nc-setup-plan.json": plan_json.encode("utf-8")}, status="draft")
    st.success(t("Đã lưu plan nháp #{aid}. {msg}", aid=aid, msg=msg))
if common.automation_notice():
    mode = st.radio(
        t("Cách bấm Register"), ["manual", "auto"], horizontal=True,
        index=0 if auto.get("submit_mode", "manual") == "manual" else 1,
        format_func=lambda m: t("App điền form, tôi tự kiểm tra & bấm Register (khuyến nghị)") if m == "manual"
        else t("App tự bấm Register khi điền đủ mọi trường"),
    )
    create_limit = st.checkbox(t("Tạo purchase limit ngay sau khi có Product #"), value=True)
    confirm = st.checkbox(t("Tôi đã kiểm tra plan của {n} gói {game} và đồng ý tạo trên môi trường RC", n=len(plans), game=g["name"]),
                          key=K("nc_confirm"))
    if st.button(t("🚀 Mở NC tool & điền form"), type="primary", disabled=bool(blocking) or not confirm or not nc_ok):
        res = common.run_job("nc_create", {"plans": list(plans.values()), "mode": mode, "create_limit": create_limit},
                             t("Đang setup trên NC tool"))
        if res and res.get("ok"):
            for r in res["results"]:
                st.session_state.setdefault(K("nc_ids"), {})[r["product_key"]] = {
                    "goods_id": r.get("goods_id") or "", "limit_id": (r.get("limit") or {}).get("limit_id") or ""}
            result_rows = [{
                "Gói": r["product_key"], "Đã đăng ký": "✅" if r["submitted"] else "❌", "Product #": r.get("goods_id"),
                "Trường cần điền tay": ", ".join(r["missing"]),
                "Limit": ("✅" if r.get("limit", {}).get("submitted") else "❌") if "limit" in r else "—",
            } for r in res["results"]]
            st.dataframe(common.df(result_rows), hide_index=True, width="stretch")
            st.info(t("Nhớ bấm **Start sale** ở Product lookup để mở bán (sau khi tạo, gói ở trạng thái Sale pending)."))
            # Thao tác thật trên tool -> luôn ghi lịch sử, không cần bấm lưu.
            ok_count = sum(r["submitted"] for r in res["results"])
            aid, msg = common.record(
                "nc_setup", t("Setup {ok}/{n} gói trên NC: {keys}", ok=ok_count, n=len(plans), keys=", ".join(plans)),
                {"metrics": {"Gói": len(plans), "Đã đăng ký": ok_count},
                 "tables": {"Kết quả setup": result_rows, "Plan": _plan_rows(plans)}, "plans": list(plans.values())},
                {"nc-setup-plan.json": plan_json.encode("utf-8")},
                status="done" if ok_count == len(plans) else "need_check",
            )
            st.session_state[K("nc_activity")] = aid
            st.caption(t("Đã ghi lịch sử #{aid}. {msg}", aid=aid, msg=msg))

# ---- 4. Audit ------------------------------------------------------------------
st.subheader(t("4. Audit sau khi setup (bắt buộc)"))
ids = st.session_state.setdefault(K("nc_ids"), {})
edited_ids = st.data_editor(
    common.df([{"Gói": k, "Product #": ids.get(k, {}).get("goods_id", ""), "Limit GUID": ids.get(k, {}).get("limit_id", "")}
               for k in plans], translate=False),
    hide_index=True, disabled=["Gói"], key=K("nc_ids_editor"), width="stretch",
    column_config={"Gói": st.column_config.TextColumn(t("Gói"))},
)
if st.button(t("🔍 Audit từng gói"), disabled=not auth.automation_allowed() or not nc_ok):
    targets = []
    for row in edited_ids.to_dict("records"):
        k, goods_id, limit_id = row["Gói"], str(row["Product #"] or "").strip(), str(row["Limit GUID"] or "").strip()
        ids[k] = {"goods_id": goods_id, "limit_id": limit_id}
        if goods_id:
            targets.append({"key": k, "kind": "goods", "goods_id": goods_id,
                            "url": f"{base}/MobileGoodsAdmin/goods/view?goodsid={goods_id}&appGroupCode={app_group}"})
        if limit_id:
            targets.append({"key": k, "kind": "limit", "goods_id": goods_id,
                            "url": f"{base}/MobileLimitAdmin/limits/view?limitid={limit_id}&targetAppGroupCode={app_group}"})
    if not targets:
        st.warning(t("Nhập Product # (và Limit GUID nếu có) trước."))
    else:
        res = common.run_job("nc_view", {"targets": targets}, t("Đang đọc trang chi tiết"))
        if res and res.get("ok"):
            st.session_state[K("nc_audit")] = res["views"]
            st.session_state[K("nc_audit_saved")] = False
audit_tables = {}
for v in st.session_state.get(K("nc_audit"), []):
    plan = plans.get(v["key"])
    if not plan:
        continue
    rows = nc.audit_goods(plan, v["kv"], v["text"]) if v["kind"] == "goods" else nc.audit_limit(plan, v["goods_id"], v["kv"], v["text"])
    bad = sum(r["Kết quả"] == "❌" for r in rows)
    label = f"{v['key']} — {'Goods' if v['kind'] == 'goods' else 'Limit'}"
    audit_tables[label] = rows
    st.markdown(f"**{label}** " + ("✅" if not bad else t("❌ {n} trường sai", n=bad)))
    st.dataframe(common.df(rows), hide_index=True, width="stretch")
    st.caption(t("❔ = trang không hiển thị đủ để kết luận tự động — mở link kiểm tra bằng mắt: {url}", url=v["url"]))
if audit_tables and not st.session_state.get(K("nc_audit_saved")):
    # Gắn kết quả audit vào bản ghi setup vừa tạo; chưa có thì tạo bản ghi audit riêng.
    n_bad = sum(r["Kết quả"] == "❌" for rows in audit_tables.values() for r in rows)
    aid = st.session_state.get(K("nc_activity"))
    rec = store.get_activity(aid) if aid else None
    if rec and auth.can_edit(rec):
        summary = rec["summary"]
        summary.setdefault("tables", {}).update({f"Audit: {k}": v for k, v in audit_tables.items()})
        summary.setdefault("metrics", {})["Trường sai (audit)"] = n_bad
        store.update_activity(aid, auth.username(), summary=summary, status="done" if not n_bad else "need_check")
    elif auth.can_run():
        aid, _ = common.record("nc_setup", t("Audit setup NC: {keys}", keys=", ".join(plans)),
                               {"metrics": {"Trường sai": n_bad}, "tables": {f"Audit: {k}": v for k, v in audit_tables.items()}},
                               status="done" if not n_bad else "need_check")
    st.session_state[K("nc_audit_saved")] = True
    st.caption(t("Đã ghi kết quả audit vào lịch sử #{aid}.", aid=aid))

# ---- Nâng cao: calibrate -----------------------------------------------------------
with st.expander(t("⚙ Nâng cao: Calibrate form NC tool (chạy 1 lần sau khi đăng nhập)")):
    st.caption(t("App mở form thật, liệt kê mọi ô nhập và tự map với các trường cần điền. "
                 "Kết quả lưu vào data/nc_fields.json để lần sau điền chính xác theo name/id (dùng chung cho mọi game)."))
    cc1, cc2 = st.columns(2)
    for col, form, label in ((cc1, "goods_new", "Form Register product"), (cc2, "limit_new", "Form Register purchase limit")):
        if col.button(f"Calibrate: {label}", disabled=not auth.automation_allowed() or not nc_ok, key=f"cal_{form}"):
            res = common.run_job("nc_inspect", {"form": form}, t("Đang đọc {label}", label=label))
            if res and res.get("ok"):
                st.session_state[f"nc_cal_{form}"] = res
    for form in ("goods_new", "limit_new"):
        res = st.session_state.get(f"nc_cal_{form}")
        if not res:
            continue
        st.markdown(t("**{form}** — map được {n} trường", form=form, n=len(res["mapping"])))
        st.json(res["mapping"])
        with st.popover(t("Xem toàn bộ ô trên trang")):
            st.dataframe(common.df(res["dump"]), width="stretch")
        if st.button(t("Lưu mapping {form}", form=form), key=f"save_{form}"):
            path = config.DATA_DIR / "nc_fields.json"
            data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
            data.setdefault(form, {}).update(res["mapping"])
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success(t("Đã lưu vào {path}", path=path))
