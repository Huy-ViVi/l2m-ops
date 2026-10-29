import streamlit as st

from core import config, db, i18n, netcheck, store, sync
from core.ai import PROVIDERS, AIClient, AIError
from core.i18n import t
from core.master import MARKETS
from ui import auth, common

common.page_header(t("⚙️ Cài đặt"))
if not auth.is_admin():
    st.error(t("Chỉ admin mới sửa được cài đặt."))
    st.stop()
settings = config.load_settings()

# ---- AI ------------------------------------------------------------------------
st.subheader("AI")
provider = st.selectbox(t("AI dùng mặc định"), list(PROVIDERS), index=list(PROVIDERS).index(settings["ai"]["provider"]),
                        format_func=lambda p: t(PROVIDERS[p]["label"]))
settings["ai"]["provider"] = provider
tabs = st.tabs([t(PROVIDERS[p]["label"]) for p in PROVIDERS])
for tab, p in zip(tabs, PROVIDERS):
    conf = settings["ai"][p]
    with tab:
        conf["api_key"] = st.text_input("API key", value=conf.get("api_key", ""), type="password", key=f"key_{p}")
        if p == "gateway":
            conf["base_url"] = st.text_input(t("Base URL (OpenAI-compatible, vd LiteLLM)"), value=conf.get("base_url", ""),
                                             placeholder="https://ai-gateway.example.vn", key="gw_url")
        models = st.session_state.get(f"models_{p}")
        current = conf.get("model") or PROVIDERS[p]["model"]
        if models:
            conf["model"] = st.selectbox("Model", models, index=models.index(current) if current in models else 0, key=f"model_sel_{p}")
        else:
            conf["model"] = st.text_input("Model", value=current, key=f"model_{p}",
                                          help=t("Bấm 'Lấy danh sách model' để chọn từ các model key này được dùng."))
        if st.button(t("📋 Lấy danh sách model"), key=f"list_{p}"):
            try:
                st.session_state[f"models_{p}"] = AIClient(settings, p, require_model=False).list_models()
                st.rerun()
            except AIError as e:
                st.error(str(e))
if db.is_remote():
    st.caption(t("API key lưu trong CSDL chung (website và bản local cùng dùng), chỉ admin thấy ở trang Cài đặt. "
                 "Có thể đặt qua biến môi trường / secrets (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GATEWAY_API_KEY, GATEWAY_BASE_URL)."))
else:
    st.caption(t("API key lưu ở `data/settings.json` trên máy chạy app, không hiển thị cho thành viên khác. "
                 "Có thể đặt qua biến môi trường (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, GATEWAY_API_KEY, GATEWAY_BASE_URL)."))

# ---- CSDL dùng chung (website + bản local) -------------------------------------------
st.subheader(t("CSDL dùng chung của team"))
if db.is_remote():
    st.success(t("Đang dùng CSDL chung `{where}`: website và bản local của mọi người cùng đọc/ghi CSDL này.", where=db.describe()))
    if config.env("DATABASE_URL"):
        st.caption(t("Địa chỉ CSDL lấy từ biến môi trường / secrets DATABASE_URL."))
    elif auth.is_host_request() and st.button(t("Ngắt CSDL chung trên máy này")):
        local = config.load_local()
        local.pop("database_url", None)
        config.save_local(local)
        common.flash(t("Đã ngắt CSDL chung: máy này quay về dữ liệu riêng (data/app.db)."))
        st.rerun()
elif auth.is_host_request():
    with st.expander(t("🔗 Nối máy này vào CSDL chung của team (Supabase)")):
        st.caption(t("Dán địa chỉ CSDL admin gửi cho bạn (Supabase → Connect → Session pooler → URI, đã điền mật khẩu). "
                     "Địa chỉ chỉ lưu ở data/local.json trên máy này. Nối xong, app chuyển sang màn hình đăng nhập: "
                     "dùng tài khoản admin cấp cho bạn trên website."))
        db_url = st.text_input(t("Địa chỉ CSDL (Postgres URI)"), type="password", key="db_url_input",
                               placeholder="postgresql://postgres.xxxx:PASSWORD@aws-0-xxx.pooler.supabase.com:5432/postgres").strip()
        # Nút không khoá theo ô trống: dán xong bấm ngay thì ô mới nhận giá trị trong cùng lượt bấm.
        c1, c2 = st.columns(2)
        test, save = c1.button(t("🔌 Kiểm tra kết nối"), key="db_test"), c2.button(t("💾 Lưu và dùng CSDL chung"), type="primary", key="db_save")
        if (test or save) and not db_url:
            st.warning(t("Chưa có địa chỉ CSDL: dán địa chỉ vào ô trên rồi bấm lại."))
        elif test:
            ok, msg = db.test_connection(db_url)
            (st.success if ok else st.error)(msg)
        elif save:
            ok, msg = db.test_connection(db_url)
            if ok:
                config.save_local({**config.load_local(), "database_url": db_url})
                st.rerun()
            st.error(msg)

# ---- Server team ---------------------------------------------------------------
team = settings["team"]
if config.team_mode() and not db.is_remote():
    st.subheader(t("Server team"))
    ip = common.lan_ip()
    api = st.session_state.get("api_status")
    if not api:
        api_text = t("chưa chạy")
    elif api.get("ok"):
        api_text = t("đang chạy ở cổng {port}", port=api["port"])
    else:
        api_text = t("lỗi: {error}", error=api.get("error", ""))
    st.markdown(t("App đang chạy **chế độ team**. Gửi cho thành viên cùng mạng LAN địa chỉ: **`{url}`**", url=f"http://{ip}:8501")
                + "\n\n" + t("API nhận kết quả từ bản local: `{url}` ({status})",
                             url=f"http://{ip}:{team.get('api_port', 8502)}", status=api_text))
    st.dataframe(common.df([{
        "IP": f"http://{r['ip']}:8501", "Card mạng": r.get("name", ""), "Mô tả": r.get("desc", ""),
        "Dùng cho team?": "⚠️ IP VPN — máy khác thường KHÔNG vào được" if r["vpn"] else "✅ dùng được nếu cùng mạng",
    } for r in common.network_addresses()]), hide_index=True, width="stretch")
    team["api_port"] = int(st.number_input(t("Cổng API đồng bộ"), min_value=1024, max_value=65535,
                                           value=int(team.get("api_port", 8502)), help=t("Đổi cổng cần khởi động lại app.")))
    st.caption(t("Máy server phải đang bật, cửa sổ run-team.bat phải mở, và thành viên phải cùng mạng LAN với máy server. "
                 "Thành viên làm việc từ xa qua VPN thường không vào được máy của nhau — khi đó cần server riêng (VM nội bộ do IT cấp)."))
elif not config.team_mode():
    st.subheader(t("Server team"))
    st.caption(t("Bản local này có thể tự đẩy mọi kết quả đã lưu lên server team. Admin của team cấp token ở trang Thành viên."))
    team["server_url"] = st.text_input(t("Địa chỉ API server team"), value=team.get("server_url", ""),
                                       placeholder="http://10.x.x.x:8502")
    team["token"] = st.text_input(t("Token đồng bộ"), value=team.get("token", ""), type="password")
    if st.button(t("🔌 Kiểm tra kết nối server team"), disabled=not sync.configured(settings)):
        ok, msg = sync.ping(settings)
        (st.success if ok else st.error)(msg)

# ---- Thư mục -------------------------------------------------------------------
st.subheader(t("Thư mục lưu kết quả"))
settings["output_root"] = st.text_input(t("Thư mục gốc"), value=settings["output_root"],
                                        help=t("Case nạp lỗi lưu vào <thư mục gốc>\\Payment-Error-Cases\\<YYYY-MM-DD>\\"))

# ---- Automation (dùng chung mọi game) ------------------------------------------------
st.subheader(t("Trình duyệt & NC tool (dùng chung mọi game)"))
auto = settings["automation"]
c1, c2 = st.columns(2)
channels = ["msedge", "chrome", "chromium"]
auto["browser_channel"] = c1.selectbox(t("Trình duyệt mặc định"), channels,
                                       index=channels.index(auto.get("browser_channel", "msedge")),
                                       format_func=lambda c: config.BROWSERS.get(c, c),
                                       help=t("Dùng cho người chưa tự chọn trình duyệt (ô Trình duyệt ở thanh bên trái — mỗi người chọn "
                                              "cho riêng mình). Microsoft Edge có sẵn trên Windows; Chromium của Playwright không "
                                              "cài sẵn cùng agent."))
auto["submit_mode"] = c2.selectbox(t("Mặc định khi tạo gói NC"), ["manual", "auto"],
                                   index=0 if auto.get("submit_mode") == "manual" else 1,
                                   format_func=lambda m: t("Tôi tự bấm Register") if m == "manual" else t("App tự bấm Register"))
auto["nc_base_url"] = st.text_input("NC Billing Admin (RC)", value=auto["nc_base_url"])

# ---- Game -------------------------------------------------------------------------
st.subheader("🎮 Game")
st.caption(t("Mỗi game có app group riêng trên NC tool, tiền tố Store Product Key, URL MyTool, bảng Item ID, master và lịch sử riêng."))
games = settings["games"]
c1, c2 = st.columns(2)
settings["default_game"] = c1.selectbox(t("Game mặc định khi mở app"), list(games), index=list(games).index(settings["default_game"]),
                                        format_func=lambda x: games[x]["name"] or x)
langs = list(i18n.LANGS)
settings["default_lang"] = c2.selectbox(t("Ngôn ngữ mặc định"), langs, format_func=i18n.LANGS.get,
                                        index=langs.index(settings.get("default_lang")) if settings.get("default_lang") in langs else 0,
                                        help=t("Áp dụng cho trình duyệt chưa tự chọn ngôn ngữ ở thanh bên (ô 🌐 Language)."))
NEW = "__new__"
if "edit_game_next" in st.session_state:  # đổi lựa chọn sau khi tạo/xoá game (không gán trực tiếp key của widget đã hiện)
    st.session_state["edit_game"] = st.session_state.pop("edit_game_next")
if st.session_state.get("edit_game") not in list(games) + [NEW]:
    st.session_state["edit_game"] = common.game()["id"]
edit = st.selectbox(t("Sửa thông số của game"), list(games) + [NEW], key="edit_game",
                    format_func=lambda x: t("➕ Thêm game mới") if x == NEW else (games[x]["name"] or x))
if edit == NEW:
    with st.form("new_game"):
        new_name = st.text_input(t("Tên game (vd Journey of Monarch SEA)"))
        if st.form_submit_button(t("Tạo game"), type="primary") and new_name.strip():
            gid = config.game_id_from_name(new_name)
            while gid in games:
                gid += "2"
            games[gid] = config.blank_game(new_name.strip())
            config.save_settings(settings, by=auth.username())
            store.log(auth.username(), "thêm game", gid, new_name)
            st.session_state["edit_game_next"] = gid
            common.flash(t("Đã tạo game {name}. Điền app group, tiền tố Store Product Key và URL MyTool rồi bấm Lưu cài đặt.",
                           name=new_name.strip()))
            st.rerun()
else:
    prof = games[edit]

    def gk(field: str) -> str:
        key = f"g_{edit}_{field}"
        return key

    # Lấy danh sách app group thật từ NC tool để khỏi gõ sai mã (phải đặt trước các ô nhập bên dưới).
    groups = st.session_state.get("nc_app_groups")
    c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
    if c1.button(t("📋 Lấy danh sách app group từ NC tool"), disabled=not auth.automation_allowed()):
        res = common.run_job("nc_app_groups", {}, t("Đang đọc danh sách app group"))
        if res and res.get("ok"):
            st.session_state["nc_app_groups"] = groups = res["app_groups"]
    if groups:
        pick = c2.selectbox(t("App group trên NC tool"), list(range(len(groups))), index=None, key=f"ag_pick_{edit}",
                            format_func=lambda i: f"{groups[i][1]}  ({groups[i][0]})")
        if pick is not None and st.button(t("Dùng app group này cho game")):
            st.session_state[gk("nc_app_group")] = groups[pick][0]
            st.session_state[gk("nc_app_group_label")] = groups[pick][1]
            st.rerun()
    for field, value in (("name", prof["name"]), ("nc_app_group", prof["nc_app_group"]),
                         ("nc_app_group_label", prof["nc_app_group_label"]), ("store_key_prefix", prof["store_key_prefix"]),
                         ("so_SEA", prof["mytool_search_order"].get("SEA", "")), ("so_VN", prof["mytool_search_order"].get("VN", "")),
                         *((f"sold_{m}", prof["mytool_sold_package"].get(m, "")) for m in MARKETS)):
        st.session_state.setdefault(gk(field), value)
    c1, c2 = st.columns(2)
    prof["name"] = c1.text_input(t("Tên game"), key=gk("name"))
    prof["store_key_prefix"] = c2.text_input(t("Tiền tố Store Product Key"), key=gk("store_key_prefix"),
                                             placeholder="com.ncv.l2m.", help=t("Store Product Key = tiền tố + Product Key trong master"))
    c1, c2 = st.columns(2)
    prof["nc_app_group"] = c1.text_input("App group code (NC tool)", key=gk("nc_app_group"), placeholder="l2msa")
    prof["nc_app_group_label"] = c2.text_input(t("Tên app group trên NC tool"), key=gk("nc_app_group_label"), placeholder="NCV-Lineage2M")
    st.markdown("**MyTool — Search Order**")
    c1, c2 = st.columns(2)
    prof["mytool_search_order"]["SEA"] = c1.text_input("SEA", key=gk("so_SEA"))
    prof["mytool_search_order"]["VN"] = c2.text_input("VN", key=gk("so_VN"))
    st.markdown(t("**MyTool — Sold Package (shop LIVE)** — mở từng shop trên MyTool rồi dán URL trang Sold Package vào đây"))
    cols = st.columns(3)
    for i, m in enumerate(MARKETS):
        prof["mytool_sold_package"][m] = cols[i % 3].text_input(m, key=gk(f"sold_{m}"))
    if edit != config.DEFAULT_GAME:
        with st.expander(t("Xoá game này")):
            st.caption(t("Chỉ xoá thông số cấu hình. Lịch sử, bảng Item ID và master của game vẫn được giữ trong CSDL/thư mục data."))
            if st.checkbox(t("Xác nhận xoá"), key=f"del_game_{edit}") and st.button(t("🗑 Xoá game")):
                games.pop(edit)
                if settings["default_game"] == edit:
                    settings["default_game"] = config.DEFAULT_GAME
                config.save_settings(settings, by=auth.username())
                store.log(auth.username(), "xoá game", edit)
                st.session_state["edit_game_next"] = config.DEFAULT_GAME
                st.rerun()

check_game = games.get(edit) if edit != NEW else None
if st.button(t("🌐 Kiểm tra kết nối từ máy này tới các tool")):
    targets = [("NC Billing Admin (RC)", auto["nc_base_url"])]
    if check_game:
        targets += [(f"MyTool Search Order {s}", u) for s, u in check_game["mytool_search_order"].items() if u]
        targets += [(f"MyTool Sold Package {m}", u) for m, u in check_game["mytool_sold_package"].items() if u]
    with st.spinner(t("Đang kiểm tra...")):
        rows = [{"Tool": name, **netcheck.check(url, timeout=4)} for name, url in targets]
    st.dataframe(common.df([{"Tool": r["Tool"], "Kết quả": "✅" if r["ok"] else "❌", "Chi tiết": r["message"], "URL": r["url"]}
                            for r in rows]), hide_index=True, width="stretch")
    if netcheck.system_proxy_configured():
        st.caption(t("Máy đang dùng proxy hệ thống — trình duyệt có thể vẫn vào được dù kiểm tra DNS ở đây báo lỗi."))

st.divider()
c1, c2, c3 = st.columns(3)
if c1.button(t("💾 Lưu cài đặt"), type="primary"):
    config.save_settings(settings, by=auth.username())
    store.log(auth.username(), "sửa cài đặt", "settings",
              f"AI: {t(PROVIDERS[provider]['label'])} / {settings['ai'][provider].get('model')}; "
              + "; ".join(f"{gid}: {p['nc_app_group']}" for gid, p in settings["games"].items()))
    st.success(t("Đã lưu."))
if c2.button(t("🧪 Test kết nối AI")):
    try:
        with st.spinner(t("Đang gọi AI...")):
            reply = AIClient(settings).test()
        st.success(t("{provider} trả lời: {reply}", provider=t(PROVIDERS[provider]["label"]), reply=reply[:60]))
    except AIError as e:
        st.error(str(e))
if c3.button(t("🔐 Mở trình duyệt để đăng nhập SSO"), disabled=not auth.automation_allowed()):
    config.save_settings(settings, by=auth.username())
    common.run_job("login", {}, t("Đăng nhập NC tool & MyTool (đóng trình duyệt khi xong)"))

st.caption(t("Chế độ: **{mode}** · Dữ liệu app: `{path}`", mode=config.app_mode(), path=config.DATA_DIR))
