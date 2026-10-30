"""Nền tảng plugin: mỗi tính năng của thành viên là một thư mục plugins/<id>/ có file khai báo plugin.toml.

Mô-đun này chỉ ĐỌC file, không chạy code plugin: tìm plugin, đọc khai báo, kiểm tra theo quy định (PLUGIN_GUIDE.md).
Website (ui/plugin_host.py) dùng kết quả để dựng menu; tools/check_plugins.py, CI trên GitHub và trang "Plugin của team"
dùng để kiểm tra plugin trước khi đưa lên. Plugin lỗi khai báo không được đưa vào menu, nhưng vẫn hiện ở trang
"Plugin của team" kèm danh sách lỗi để người phụ trách sửa.
"""
from __future__ import annotations

import ast
import functools
import importlib.metadata
import io
import os
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:  # Python 3.10 (máy thành viên) — requirements.txt cài tomli
    import tomli as tomllib

from . import config
from .i18n import t

PLUGINS_DIR = Path(os.environ.get("L2M_PLUGINS_DIR") or config.APP_ROOT / "plugins")
MANIFEST = "plugin.toml"
TEMPLATE = "_template"
DEFAULT_SECTION = "Plugin"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
ICON_RE = re.compile(r"^:material/[a-z0-9_]+:$")
ACCESS = ("all", "admin")
MAX_FILE = 2 * 1024 * 1024  # dữ liệu lớn để trong CSDL (sdk.save), không để trong code
MAX_TOTAL = 5 * 1024 * 1024
REQUIRED_FILES = ("__init__.py", "README.md")
TEXT_SUFFIXES = {".py", ".toml", ".md", ".txt", ".json", ".csv", ".sql", ".yaml", ".yml", ".ini", ".cfg", ".html", ".js"}
# Plugin chỉ dùng nền tảng qua core.sdk: phần lõi khác đổi bất cứ lúc nào (và sẽ đổi khi dời sang server nội bộ).
PLATFORM_PACKAGES = {"core", "ui", "views", "automation", "tools", "tests", "app"}
# Thư viện không dùng trực tiếp trong plugin: dữ liệu đi qua sdk; việc cần trình duyệt / VPN đi qua agent (phase 3).
BLOCKED_MODULES = {
    "sqlite3": "lưu dữ liệu bằng sdk.save() / sdk.load()",
    "psycopg": "lưu dữ liệu bằng sdk.save() / sdk.load()",
    "psycopg2": "lưu dữ liệu bằng sdk.save() / sdk.load()",
    "sqlalchemy": "lưu dữ liệu bằng sdk.save() / sdk.load()",
    "subprocess": "việc cần chạy chương trình ngoài sẽ đi qua agent (lộ trình phase 3)",
    "playwright": "việc cần trình duyệt / VPN sẽ đi qua agent (lộ trình phase 3)",
    "selenium": "việc cần trình duyệt / VPN sẽ đi qua agent (lộ trình phase 3)",
    "anthropic": "dùng AI chung của team qua sdk.ai()",
    "openai": "dùng AI chung của team qua sdk.ai()",
}
BLOCKED_CALLS = {  # st.<tên>(...) mà nền tảng đã lo
    "set_page_config": "nền tảng đã gọi st.set_page_config",
    "navigation": "menu do nền tảng dựng từ plugin.toml",
}
FORBIDDEN_FILE_RE = re.compile(r"(^|/)(\.env[^/]*|local\.json|secrets\.toml|[^/]+\.(db|sqlite|sqlite3|pem|key|pfx|p12))$", re.I)
SECRET_PATTERNS = [
    (re.compile(r"postgres(?:ql)?://[^\s'\"/:@]+:[^\s'\"@]+@"), "địa chỉ CSDL kèm mật khẩu"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "API key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "GitHub token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS key"),
    (re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key"),
]


@dataclass
class Page:
    file: str
    title: str
    icon: str = ""


@dataclass
class Plugin:
    id: str
    path: Path
    name: str = ""
    description: str = ""
    version: str = ""
    owners: list[str] = field(default_factory=list)
    icon: str = ""
    section: str = DEFAULT_SECTION
    access: str = "all"
    games: list[str] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def label(self) -> str:
        return self.name or self.id


# ---------------------------------------------------------------------------
# Tìm plugin và đọc plugin.toml
# ---------------------------------------------------------------------------
def discover(root: Path | None = None, check_code: bool = False) -> list[Plugin]:
    """Mọi thư mục con của plugins/ (bỏ thư mục bắt đầu bằng _ hoặc ., vd _template). Sắp theo tên hiển thị.
    check_code: kiểm tra cả code (chậm hơn — dùng ở trang Plugin của team, CI); không thì chỉ đọc plugin.toml (dựng menu)."""
    root = root or PLUGINS_DIR
    if not root.is_dir():
        return []
    found = [validate(d) if check_code else read_manifest(d) for d in sorted(root.iterdir())
             if d.is_dir() and not d.name.startswith(("_", ".")) and d.name != "__pycache__"]
    return sorted(found, key=lambda p: p.label.lower())


def _str_list(value) -> list[str] | None:
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return [v.strip() for v in value if v.strip()]
    return None


def read_manifest(folder: Path) -> Plugin:
    """plugin.toml -> Plugin; sai chỗ nào ghi vào .problems (không ném lỗi)."""
    p = Plugin(id=folder.name, path=folder)
    path = folder / MANIFEST
    if not path.is_file():
        p.problems.append(t("Thiếu file {file}", file=MANIFEST))
        return p
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        p.problems.append(t("{file} viết sai cú pháp TOML: {error}", file=MANIFEST, error=e))
        return p
    pid = data.get("id")
    if not isinstance(pid, str) or not ID_RE.match(pid):
        p.problems.append(t("id phải là chữ thường không dấu, số hoặc _, 3–32 ký tự, bắt đầu bằng chữ (vd update_tracker)"))
    elif pid != folder.name:
        p.problems.append(t("id '{id}' phải trùng tên thư mục: plugins/{id}/", id=pid))
    for key in ("name", "version", "description"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            p.problems.append(t("Thiếu trường '{key}' trong {file}", key=key, file=MANIFEST))
        else:
            setattr(p, key, value.strip())
    owners = _str_list(data.get("owners"))
    if not owners:
        p.problems.append(t("Thiếu 'owners': danh sách tài khoản website của người phụ trách, vd [\"myly\"]"))
    else:
        p.owners = owners
    p.icon = str(data.get("icon") or "")
    p.section = str(data.get("section") or DEFAULT_SECTION).strip() or DEFAULT_SECTION
    p.access = str(data.get("access") or "all")
    if p.access not in ACCESS:
        p.problems.append(t("'access' chỉ nhận: {values}", values=", ".join(ACCESS)))
    games = _str_list(data.get("games", []))
    if games is None:
        p.problems.append(t("'games' phải là danh sách mã game, vd [\"l2m\"] (để [] = mọi game)"))
    else:
        p.games = games
    raw_pages = data.get("pages")
    if not isinstance(raw_pages, list) or not raw_pages:
        p.problems.append(t("Cần ít nhất một trang: khối [[pages]] có file và title"))
        raw_pages = []
    for i, raw in enumerate(raw_pages, 1):
        if not isinstance(raw, dict) or not isinstance(raw.get("file"), str) or not isinstance(raw.get("title"), str):
            p.problems.append(t("Trang thứ {n} thiếu 'file' hoặc 'title'", n=i))
            continue
        page = Page(raw["file"].strip(), raw["title"].strip(), str(raw.get("icon") or p.icon or ""))
        target = (folder / page.file).resolve()
        if not page.file.endswith(".py") or folder.resolve() not in target.parents:
            p.problems.append(t("Trang '{file}' phải là file .py nằm trong thư mục plugin", file=page.file))
        elif not target.is_file():
            p.problems.append(t("Không thấy file trang '{file}'", file=page.file))
        else:
            p.pages.append(page)
    for icon in {p.icon, *(pg.icon for pg in p.pages)} - {""}:
        if not _icon_ok(icon):
            p.problems.append(t("Icon '{icon}' không hợp lệ — dùng :material/tên_icon: hoặc một emoji", icon=icon))
    return p


def _icon_ok(icon: str) -> bool:
    return bool(ICON_RE.match(icon)) or (len(icon) <= 4 and not icon.isascii())


# ---------------------------------------------------------------------------
# Kiểm tra code (đọc cú pháp, không chạy)
# ---------------------------------------------------------------------------
def _norm_dist(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


@functools.cache
def allowed_third_party() -> frozenset[str]:
    """Tên mô-đun của các thư viện trong requirements.txt (kể cả thư viện chúng kéo theo) — website có sẵn những thư viện này."""
    req = config.APP_ROOT / "requirements.txt"
    names = []
    for line in (req.read_text(encoding="utf-8").splitlines() if req.exists() else []):
        line = line.split("#")[0].strip()
        if line:
            names.append(re.split(r"[\s;<>=!~\[(]", line)[0])
    seen: set[str] = set()
    stack = names
    while stack:
        name = _norm_dist(stack.pop())
        if name in seen:
            continue
        seen.add(name)
        try:
            requires = importlib.metadata.requires(name) or []
        except importlib.metadata.PackageNotFoundError:
            continue
        stack += [re.split(r"[\s;<>=!~\[(]", r)[0] for r in requires if "extra ==" not in r]
    return frozenset(mod for mod, dists in importlib.metadata.packages_distributions().items()
                     if any(_norm_dist(d) in seen for d in dists))


def _rel_target(file_parts: list[str], level: int, module: str | None) -> list[str]:
    """`from ..x import y` trong plugins/<id>/a/b.py -> ['plugins', '<id>', 'x']."""
    package = ["plugins", *file_parts[:-1]]
    base = package[:len(package) - (level - 1)] if level > 1 else package
    return base + (module.split(".") if module else [])


def _check_imports(tree: ast.AST, rel: str, pid: str, problems: list[str]) -> None:
    parts = rel.split("/")
    allowed = allowed_third_party()
    for node in ast.walk(tree):
        targets: list[tuple[list[str], int]] = []
        if isinstance(node, ast.Import):
            targets = [(a.name.split("."), node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                target = _rel_target([pid, *parts], node.level, node.module)
                if len(target) < 2 or target[1] != pid:
                    problems.append(t("{file}:{line}: import ra ngoài thư mục plugin — chỉ import trong plugins/{id}/",
                                      file=rel, line=node.lineno, id=pid))
                continue
            mod = (node.module or "").split(".")
            if mod == ["core"]:  # from core import sdk
                bad = [a.name for a in node.names if a.name != "sdk"]
                if bad:
                    problems.append(t("{file}:{line}: chỉ dùng nền tảng qua core.sdk (đang import {names})",
                                      file=rel, line=node.lineno, names=", ".join(bad)))
                continue
            targets = [(mod + [a.name], node.lineno) for a in node.names]  # from ui import common -> ui.common
        for mod, line in targets:
            top, full = mod[0], ".".join(mod)
            if top == "plugins":
                if len(mod) < 2 or mod[1] != pid:
                    problems.append(t("{file}:{line}: không import code của plugin khác ({module}) — liên kết qua dữ liệu dùng chung",
                                      file=rel, line=line, module=full))
            elif top in PLATFORM_PACKAGES:
                if full != "core.sdk" and not full.startswith("core.sdk."):
                    problems.append(t("{file}:{line}: chỉ dùng nền tảng qua core.sdk (đang import {names})",
                                      file=rel, line=line, names=full))
            elif top in BLOCKED_MODULES:
                problems.append(t("{file}:{line}: không dùng {module} trong plugin — {hint}",
                                  file=rel, line=line, module=top, hint=t(BLOCKED_MODULES[top])))
            elif top not in sys.stdlib_module_names and top not in allowed and top != "__future__":
                problems.append(t("{file}:{line}: thư viện '{module}' chưa có trong requirements.txt của nền tảng — "
                                  "nhắn admin thêm (kèm phiên bản) hoặc dùng thư viện có sẵn", file=rel, line=line, module=top))


def _const_str(node) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _is_session_state(node) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "session_state"


def _check_calls(tree: ast.AST, rel: str, pid: str, problems: list[str]) -> None:
    prefix = pid + "_"
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr in BLOCKED_CALLS and isinstance(f.value, ast.Name) and f.value.id == "st":
                problems.append(t("{file}:{line}: không gọi st.{name} — {hint}",
                                  file=rel, line=node.lineno, name=f.attr, hint=t(BLOCKED_CALLS[f.attr])))
            if isinstance(f, ast.Attribute) and f.attr in ("getenv", "putenv") and isinstance(f.value, ast.Name) and f.value.id == "os":
                problems.append(t("{file}:{line}: không đọc biến môi trường — dùng sdk.secret(\"TÊN\")", file=rel, line=node.lineno))
            if isinstance(f, ast.Attribute) and f.attr in ("system", "popen") and isinstance(f.value, ast.Name) and f.value.id == "os":
                problems.append(t("{file}:{line}: không dùng {module} trong plugin — {hint}", file=rel, line=node.lineno,
                                  module=f"os.{f.attr}", hint=t(BLOCKED_MODULES["subprocess"])))
            for kw in node.keywords:  # key="..." của widget: session_state dùng chung cho mọi trang -> phải có tiền tố
                value = _const_str(kw.value)
                if kw.arg == "key" and value is not None and not value.startswith(prefix):
                    problems.append(t("{file}:{line}: key '{key}' phải bắt đầu bằng '{prefix}' (dùng sdk.key(\"…\"))",
                                      file=rel, line=node.lineno, key=value, prefix=prefix))
            if (isinstance(f, ast.Attribute) and f.attr in ("get", "setdefault", "pop") and _is_session_state(f.value)
                    and node.args and (value := _const_str(node.args[0])) is not None and not value.startswith(prefix)):
                problems.append(t("{file}:{line}: key '{key}' phải bắt đầu bằng '{prefix}' (dùng sdk.key(\"…\"))",
                                  file=rel, line=node.lineno, key=value, prefix=prefix))
        elif isinstance(node, ast.Subscript) and _is_session_state(node.value):
            value = _const_str(node.slice)
            if value is not None and not value.startswith(prefix):
                problems.append(t("{file}:{line}: key '{key}' phải bắt đầu bằng '{prefix}' (dùng sdk.key(\"…\"))",
                                  file=rel, line=node.lineno, key=value, prefix=prefix))
        elif isinstance(node, ast.Attribute) and node.attr == "environ" and isinstance(node.value, ast.Name) and node.value.id == "os":
            problems.append(t("{file}:{line}: không đọc biến môi trường — dùng sdk.secret(\"TÊN\")", file=rel, line=node.lineno))
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "st":
            if node.attr == "secrets":
                problems.append(t("{file}:{line}: không đọc st.secrets — dùng sdk.secret(\"TÊN\")", file=rel, line=node.lineno))
            elif node.attr.startswith("experimental_"):  # AI hay viết theo Streamlit cũ
                problems.append(t("{file}:{line}: st.{name} không còn trong Streamlit mới — dùng st.rerun / st.cache_data / st.query_params",
                                  file=rel, line=node.lineno, name=node.attr))


def validate(folder: Path) -> Plugin:
    """Kiểm tra đủ một thư mục plugin: plugin.toml, file bắt buộc, dung lượng, bí mật, cú pháp, import, cách dùng st/session_state."""
    p = read_manifest(folder)
    if folder.name.startswith(("_", ".")):
        p.problems.append(t("Tên thư mục không được bắt đầu bằng _ hoặc . (thư mục như vậy bị bỏ qua)"))
    for name in REQUIRED_FILES:
        if not (folder / name).is_file():
            p.problems.append(t("Thiếu file {file}", file=name))
    total = 0
    for path in sorted(folder.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        rel = path.relative_to(folder).as_posix()
        size = path.stat().st_size
        total += size
        if FORBIDDEN_FILE_RE.search(rel):
            p.problems.append(t("{file}: không đưa file bí mật / CSDL vào plugin (key để trong secrets, dữ liệu lưu bằng sdk.save)", file=rel))
        if size > MAX_FILE:
            p.problems.append(t("{file}: {size} MB — file trong plugin tối đa {max} MB; dữ liệu lớn lưu bằng sdk.save()",
                                file=rel, size=round(size / 1048576, 1), max=MAX_FILE // 1048576))
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern, what in SECRET_PATTERNS:
            if pattern.search(text):
                p.problems.append(t("{file}: có vẻ chứa {what} — không ghi bí mật vào code, dùng sdk.secret()", file=rel, what=t(what)))
        if path.suffix == ".py":
            try:
                tree = ast.parse(text, filename=rel)
            except SyntaxError as e:
                p.problems.append(t("{file}:{line}: lỗi cú pháp Python — {error}", file=rel, line=e.lineno, error=e.msg))
                continue
            _check_imports(tree, rel, folder.name, p.problems)
            _check_calls(tree, rel, folder.name, p.problems)
    if total > MAX_TOTAL:
        p.problems.append(t("Thư mục plugin {size} MB — tối đa {max} MB", size=round(total / 1048576, 1), max=MAX_TOTAL // 1048576))
    p.problems = list(dict.fromkeys(p.problems))
    return p


# ---------------------------------------------------------------------------
# Câu trả lời của AI dạng chat -> file plugin (định dạng trong AI_PROMPT.md: "FILE: plugins/<id>/x" + khối ```)
# ---------------------------------------------------------------------------
FILE_LINE_RE = re.compile(r"^[\s>#*_-]*FILE\s*:\s*`?([^\s`*]+?)`?[\s*_]*$", re.I)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
END_LINE_RE = re.compile(r"^[\s>#*_-]*(HẾT|HET|END(\s+OF)?)\s+FILES?[\s*_.-]*$", re.I)


def files_from_text(text: str) -> tuple[str, dict[str, str], list[str]]:
    """-> (id, {đường dẫn trong thư mục plugin: nội dung}, vấn đề). Chấp nhận các kiểu AI hay viết: **FILE: x**, ### FILE: `x`,
    đường dẫn thiếu plugins/<id>/; thiếu __init__.py thì tự thêm (luôn để trống)."""
    lines = text.replace("\r\n", "\n").split("\n")
    ends = [i for i, line in enumerate(lines) if END_LINE_RE.match(line)]
    if ends:
        lines = lines[:ends[-1]]
    marks = [(i, m.group(1)) for i, line in enumerate(lines) if (m := FILE_LINE_RE.match(line))]
    problems: list[str] = []
    if not marks:
        return "", {}, [t("Không thấy dòng 'FILE: …' nào — nhờ AI trả lời đúng định dạng ở mục 3 của AI_PROMPT.md")]
    raw: dict[str, str] = {}
    for n, (i, path) in enumerate(marks):
        chunk = lines[i + 1: marks[n + 1][0] if n + 1 < len(marks) else len(lines)]
        fences = [k for k, line in enumerate(chunk) if FENCE_RE.match(line)]
        if len(fences) < 2:
            problems.append(t("{file}: không thấy khối code chứa nội dung file", file=path))
            continue
        body = "\n".join(chunk[fences[0] + 1:fences[-1]]).rstrip("\n")
        raw[re.sub(r"^(\./)+", "", path.strip().replace("\\", "/"))] = body + "\n" if body else ""
    pid = ""
    manifest = next((v for k, v in raw.items() if k.rsplit("/", 1)[-1] == MANIFEST), None)
    if manifest is None:
        problems.append(t("Trong câu trả lời không có file {file}", file=MANIFEST))
    else:
        try:
            pid = str(tomllib.loads(manifest).get("id") or "")
        except tomllib.TOMLDecodeError as e:
            problems.append(t("{file} viết sai cú pháp TOML: {error}", file=MANIFEST, error=e))
    if not ID_RE.match(pid):
        pid = next((k.split("/")[1] for k in raw if k.startswith("plugins/") and k.count("/") >= 2), "") or pid
    if not ID_RE.match(pid):
        problems.append(t("id phải là chữ thường không dấu, số hoặc _, 3–32 ký tự, bắt đầu bằng chữ (vd update_tracker)"))
        return pid, {}, problems
    files: dict[str, str] = {}
    for path, body in raw.items():
        rel = path if path.startswith("plugins/") else (f"plugins/{path}" if path.startswith(pid + "/") else f"plugins/{pid}/{path}")
        prefix = f"plugins/{pid}/"
        if not rel.startswith(prefix) or ".." in rel.split("/") or rel == prefix:
            problems.append(t("{file}: nằm ngoài thư mục plugins/{id}/ — bỏ qua", file=path, id=pid))
            continue
        files[rel[len(prefix):]] = body
    if files and "__init__.py" not in files:
        files["__init__.py"] = ""
    return pid, files, problems


def zip_plugin(pid: str, files: dict[str, str]) -> bytes:
    """{đường dẫn: nội dung} -> zip có thư mục <id>/ (giống zip người dùng tự nén thư mục plugin)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, body in sorted(files.items()):
            z.writestr(f"{pid}/{rel}", body.encode("utf-8"))
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Kiểm tra một file zip (trang Plugin của team: thành viên tự kiểm tra trước khi gửi)
# ---------------------------------------------------------------------------
MAX_ZIP = 10 * 1024 * 1024


def validate_zip(data: bytes) -> Plugin:
    """Giải nén zip vào thư mục tạm (không chạy code) rồi kiểm tra. Zip chứa thẳng plugin.toml hoặc một thư mục chứa nó."""
    tmp = Path(tempfile.mkdtemp(prefix="l2m-plugin-check-"))
    try:
        if len(data) > MAX_ZIP:
            return Plugin(id="?", path=tmp, problems=[t("File zip quá lớn (tối đa {max} MB)", max=MAX_ZIP // 1048576)])
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            return Plugin(id="?", path=tmp, problems=[t("Không đọc được file zip")])
        out = tmp / "x"
        total = 0
        with zf:
            for info in zf.infolist():
                target = (out / info.filename).resolve()
                if out.resolve() not in target.parents and target != out.resolve():
                    return Plugin(id="?", path=tmp, problems=[t("Zip có đường dẫn ra ngoài thư mục — không nhận")])
                total += info.file_size
                if total > MAX_TOTAL * 4:
                    return Plugin(id="?", path=tmp, problems=[t("File zip quá lớn (tối đa {max} MB)", max=MAX_ZIP // 1048576)])
            zf.extractall(out)
        manifests = sorted(out.rglob(MANIFEST), key=lambda m: len(m.parts))
        if not manifests:
            return Plugin(id="?", path=tmp, problems=[t("Trong zip không có file {file}", file=MANIFEST)])
        src = manifests[0].parent
        try:
            pid = str(tomllib.loads(manifests[0].read_text(encoding="utf-8-sig")).get("id") or src.name)
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            pid = src.name
        folder = tmp / "plugins" / (pid if ID_RE.match(pid) else "invalid_id")
        shutil.copytree(src, folder)  # đặt đúng chỗ như trong kho code: plugins/<id>/
        return validate(folder)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
