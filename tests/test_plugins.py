"""Nền tảng plugin: kiểm tra quy định (core/plugins.py), sdk lưu dữ liệu (core/sdk.py), chạy trang trong khung cô lập lỗi
(ui/plugin_host.py), menu + trang "Plugin của team". Chạy trên SQLite và thư mục plugin tạm, không đụng dữ liệu thật.

    .venv\\Scripts\\python.exe tests\\test_plugins.py
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
WORK = Path(tempfile.mkdtemp(prefix="l2m-plugins-test-"))
PLUGINS = WORK / "plugins"
PLUGINS.mkdir()
os.environ.pop("DATABASE_URL", None)
os.environ.update(L2M_DATA_DIR=str(WORK / "data"), L2M_PLUGINS_DIR=str(PLUGINS), L2M_APP_MODE="local", L2M_NO_AUTOMATION="1")

from core import bundle, i18n, plugins, sdk, store  # noqa: E402

TEMPLATE = ROOT / "plugins" / "_template"


def _from_template(pid: str, root: Path = PLUGINS) -> Path:
    dest = root / pid
    shutil.copytree(TEMPLATE, dest)
    toml = dest / "plugin.toml"
    toml.write_text(toml.read_text(encoding="utf-8").replace('"doi_thanh_ten_thu_muc"', f'"{pid}"'), encoding="utf-8")
    return dest


def _plugin(pid: str, page: str, manifest_extra: str = "", files: dict[str, str] | None = None) -> Path:
    d = PLUGINS / pid
    d.mkdir()
    (d / "__init__.py").write_text("", encoding="utf-8")
    (d / "README.md").write_text(f"# {pid}\n", encoding="utf-8")
    (d / "plugin.toml").write_text(
        f'id = "{pid}"\nname = "{pid.title()}"\ndescription = "test"\nversion = "1.0.0"\nowners = ["alice"]\n{manifest_extra}\n'
        '[[pages]]\nfile = "page.py"\ntitle = "Trang"\n', encoding="utf-8")
    (d / "page.py").write_text(page, encoding="utf-8")
    for name, text in (files or {}).items():
        (d / name).write_text(text, encoding="utf-8")
    return d


def test_template_passes_rules():
    _from_template("sample_notes")
    p = plugins.validate(PLUGINS / "sample_notes")
    assert p.ok, p.problems
    assert p.name == "Ghi chú gói nạp" and p.owners == ["ten_tai_khoan"] and [pg.file for pg in p.pages] == ["page.py"]
    assert "sample_notes" in [x.id for x in plugins.discover()]
    assert "requests" in plugins.allowed_third_party() and "pandas" in plugins.allowed_third_party()


def test_rules_catch_problems():
    _plugin("bad_one", "\n".join([
        "import os",
        "import sqlite3",
        "import notalib_xyz",
        "import streamlit as st",
        "from core import store",
        "from ui import common",
        "import plugins.other_plugin",
        "from .. import other_plugin",
        "st.set_page_config(layout='wide')",
        "st.text_input('x', key='q')",
        "st.session_state['picked'] = 1",
        "st.session_state.get('other')",
        "st.text_input('y', key='bad_one_ok')",
        "token = os.environ['X']",
        "URL = 'postgresql://user:secret@db.example.com/postgres'",
    ]), manifest_extra='access = "everyone"', files={"local.json": "{}", "broken.py": "def x(:\n"})
    (PLUGINS / "bad_one" / "big.bin").write_bytes(b"0" * (plugins.MAX_FILE + 1))
    p = plugins.validate(PLUGINS / "bad_one")
    text = "\n".join(p.problems)
    expected = ["'access' chỉ nhận", "không dùng sqlite3", "thư viện 'notalib_xyz'", "đang import store", "đang import ui.common",
                "plugin khác (plugins.other_plugin)", "import ra ngoài thư mục plugin", "không gọi st.set_page_config",
                "key 'q' phải bắt đầu bằng 'bad_one_'", "key 'picked'", "key 'other'", "không đọc biến môi trường",
                "địa chỉ CSDL kèm mật khẩu", "local.json: không đưa file bí mật", "broken.py:1: lỗi cú pháp", "big.bin"]
    for needle in expected:
        assert needle in text, (needle, text)
    assert "bad_one_ok" not in text and not p.ok

    _plugin("Wrong_Id", "x = 1\n")
    assert any("id phải là chữ thường" in x for x in plugins.read_manifest(PLUGINS / "Wrong_Id").problems)
    (PLUGINS / "no_toml").mkdir()
    assert plugins.read_manifest(PLUGINS / "no_toml").problems == ["Thiếu file plugin.toml"]
    (PLUGINS / "_hidden").mkdir()
    assert "_hidden" not in [x.id for x in plugins.discover()]


def test_zip_self_check():
    src = _from_template("zip_notes", WORK / "zipsrc")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for f in src.rglob("*"):
            z.write(f, "my-folder-name/" + f.relative_to(src).as_posix())  # tên thư mục trong zip khác id: vẫn nhận
    p = plugins.validate_zip(buf.getvalue())
    assert p.ok and p.id == "zip_notes", p.problems
    evil = io.BytesIO()
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../plugin.toml", "id = 'x'")
    assert "ra ngoài thư mục" in plugins.validate_zip(evil.getvalue()).problems[0]
    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w") as z:
        z.writestr("readme.txt", "x")
    assert "không có file plugin.toml" in plugins.validate_zip(empty.getvalue()).problems[0]
    assert plugins.validate_zip(b"not a zip").problems == ["Không đọc được file zip"]


def test_sdk_records_and_history():
    with sdk.use("sample_notes"):
        assert sdk.save("notes", [{"id": "a", "product_key": "com.ncv.l2m.web.item 195", "item_id": "79", "note": "x"},
                                  {"id": "b", "product_key": "web.item1", "note": "y", "_key": "ignored"}]) == 2
        a = sdk.get("notes", "a")
        assert a["product_key"] == "web.item195" and a["item_id"] == 79 and a["_updated_by"] == "script"
        assert "_key" not in sdk.get("notes", "b") or sdk.get("notes", "b")["_key"] == "b"
        assert [r["_key"] for r in sdk.load("notes", product_key="com.ncv.l2m.web.item195")] == ["a"]
        assert sdk.save("notes", {"id": "a", "product_key": "web.item195", "item_id": 79, "note": "x"}) == 0  # không đổi
        assert sdk.save("notes", {**{k: v for k, v in a.items()}, "note": "x2"}) == 1
        old = sdk.history("notes", "a")
        assert len(old) == 1 and old[0]["action"] == "update" and old[0]["data"]["note"] == "x"
        assert sdk.delete("notes", ["a", "zzz"]) == 1 and sdk.get("notes", "a") is None
        assert [h["action"] for h in sdk.history("notes", "a")] == ["delete", "update"]
        sdk.save("notes", sdk.history("notes", "a")[0]["data"])  # khôi phục bản trước khi xoá
        assert sdk.get("notes", "a")["note"] == "x2"
        sdk.save("terms", {"id": "t1", "lang": "th"}, game="")  # dùng chung mọi game
        assert sdk.load("terms") == [] and len(sdk.load("terms", game="")) == 1
        assert sdk.collections() == {"notes": 2}
        for bad in (lambda: sdk.save("Bad Name", {"id": 1}), lambda: sdk.save("notes", {"note": "no key"}),
                    lambda: sdk.save("notes", {"id": "big", "x": "y" * (sdk.MAX_RECORD + 1)}), lambda: sdk.secret("lower")):
            try:
                bad()
                raise AssertionError("phải báo SDKError")
            except sdk.SDKError:
                pass
        assert sdk.key("q") == "sample_notes_q" and sdk.secret("NOT_SET") == ""
        assert sdk.product_key("com.ncv.l2m.web.item 195") == "web.item195"
    with sdk.use("other_plugin"):
        assert sdk.load("notes") == []  # mỗi plugin chỉ thấy dữ liệu của mình
    try:
        sdk.load("notes")
        raise AssertionError("ngoài trang plugin phải báo lỗi")
    except sdk.SDKError:
        pass
    stats = {(r["plugin"], r["collection"], r["game"]): r["n"] for r in store.plugin_stats()}
    assert stats[("sample_notes", "notes", "l2m")] == 2 and stats[("sample_notes", "terms", "")] == 1


def test_sdk_translations():
    i18n.set_lang("en")
    try:
        with sdk.use("sample_notes"):
            assert sdk.t("Ghi chú gói nạp") == "Package notes"  # locales.py của plugin
            assert sdk.t("Tổng hợp {n} ghi chú", n=3) == "Summary of 3 notes"
            assert sdk.t("Lịch sử hoạt động") != "Lịch sử hoạt động"  # rơi về bản dịch của nền tảng
            assert sdk.t("Chuỗi chưa dịch") == "Chuỗi chưa dịch"
    finally:
        i18n.set_lang(None)


HOST = """
import streamlit as st
from core import plugins
from ui import plugin_host
p = next(x for x in plugins.discover() if x.id == st.session_state["pid"])
plugin_host.run_page(p, p.pages[0])
st.markdown("after-plugin")
"""


def test_page_runs_isolated():
    from streamlit.testing.v1 import AppTest

    _plugin("boom", "from core import sdk\nimport streamlit as st\nsdk.header('Boom')\nraise ValueError('hỏng rồi')\n")
    _plugin("relimp", "from core import sdk\nfrom . import helper\nimport streamlit as st\nst.markdown(helper.TEXT + sdk.key('x'))\n",
            files={"helper.py": "TEXT = 'helper-ok:'\n"})
    at = AppTest.from_string(HOST, default_timeout=60)
    at.session_state["pid"] = "boom"
    at.run()
    assert not at.exception, at.exception
    assert any("Boom" in e.value and "hỏng rồi" in e.value for e in at.error), [e.value for e in at.error]
    assert any("alice" in c.value for c in at.caption) and any(m.value == "after-plugin" for m in at.markdown)

    at = AppTest.from_string(HOST, default_timeout=60)
    at.session_state["pid"] = "relimp"
    at.run()
    assert not at.exception and not at.error, (at.exception, [e.value for e in at.error])
    assert any(m.value == "helper-ok:relimp_x" for m in at.markdown)  # relative import + sdk.key trong trang plugin

    at = AppTest.from_string(HOST, default_timeout=60)  # plugin mẫu: lưu ghi chú qua form
    at.session_state["pid"] = "sample_notes"
    at.run()
    assert not at.exception and not at.error, (at.exception, [e.value for e in at.error])
    at.text_input(key="sample_notes_product_key").input("com.ncv.l2m.web.item 7")
    at.text_area(key="sample_notes_text").input("ghi chú từ test")
    at.button[0].click().run()
    assert not at.exception, at.exception
    with sdk.use("sample_notes"):
        saved = [n for n in sdk.load("notes") if n.get("note") == "ghi chú từ test"]
    assert saved and saved[0]["product_key"] == "web.item7" and saved[0]["_updated_by"] == "local", saved
    assert saved[0]["_key"].startswith("web.item7-"), saved  # khoá ghép từ Product Key đã chuẩn hoá


def test_menu_and_board():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    assert not at.exception, at.exception
    at.switch_page("views/plugins.py").run()
    assert not at.exception, at.exception
    table = at.dataframe[0].value
    names = set(table["Plugin"])
    assert {"Ghi chú gói nạp", "Boom", "Relimp", "Bad_One"} <= names, names
    status = dict(zip(table["Mã"], table["Trạng thái"]))
    assert status["sample_notes"] == "✅ Đang chạy" and status["bad_one"].startswith("⚠️")
    assert any("bad_one" in e.label.lower() or "Bad_One" in e.label for e in at.expander)
    assert any("Thông báo cho cả team" in i.value for i in at.info)

    from ui import plugin_host

    sections = AppTest.from_string(
        "import streamlit as st\nfrom ui import plugin_host\n"
        "st.session_state['out'] = {k: [p.title for p in v] for k, v in plugin_host.sections().items()}\n")
    sections.run()
    menu = sections.session_state["out"]
    assert "Ghi chú gói nạp" in menu["Plugin"] and "Trang" in menu["Plugin"], menu
    assert all("Bad_One" not in titles for titles in menu.values())  # plugin lỗi khai báo không lên menu
    assert plugin_host  # noqa


def test_starter_kit():
    data = bundle.starter_zip()
    names = set(zipfile.ZipFile(io.BytesIO(data)).namelist())
    assert {"app.py", "run.bat", "core/sdk.py", "tools/check_plugins.py", "plugins/__init__.py", "plugins/_template/plugin.toml",
            "plugins/_template/page.py", "PLUGIN_GUIDE.md", "AGENTS.md", "CLAUDE.md", "ROADMAP.md", "BAT-DAU-LAM-PLUGIN.txt"} <= names
    assert not any(n.startswith("data/") for n in names), "bộ khởi đầu không được có data/ (địa chỉ CSDL)"


def test_check_tool():
    sys.path.insert(0, str(ROOT / "tools"))
    import check_plugins

    assert check_plugins.main([str(PLUGINS / "sample_notes")]) == 0
    assert check_plugins.main([str(PLUGINS / "bad_one")]) == 1


if __name__ == "__main__":
    import time
    import traceback

    failed = 0
    try:
        for name, fn in list(globals().items()):
            if name.startswith("test_") and callable(fn):
                t0 = time.monotonic()
                try:
                    fn()
                    print(f"PASS {name} ({time.monotonic() - t0:.1f}s)")
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    print(f"FAIL {name}: {type(e).__name__}: {e}")
                    traceback.print_exc()
    finally:
        shutil.rmtree(WORK, ignore_errors=True)
    sys.exit(1 if failed else 0)
