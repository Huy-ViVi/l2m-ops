"""Gói agent tải từ website: code app + data/local.json đã điền sẵn địa chỉ CSDL chung và tài khoản người tải.

Người dùng chỉ cần giải nén rồi nháy đúp agent.bat (tự cài Python + thư viện — tools/setup.ps1). Website và agent
cùng tính code_version() trên cùng danh sách file, nên website biết agent nào đang chạy bản cũ.
"""
from __future__ import annotations

import functools
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

from . import config

CODE_DIRS = ("core", "ui", "views", "automation", "tools", "resources")
CODE_FILES = ("app.py", "requirements.txt", "run.bat", "run-team.bat", "agent.bat", "README.md")
SKIP_SUFFIXES = (".pyc", ".pyo")


def code_files(root: Path = config.APP_ROOT) -> list[Path]:
    files = [root / f for f in CODE_FILES if (root / f).is_file()]
    for d in CODE_DIRS:
        if (root / d).is_dir():
            files += [p for p in (root / d).rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts and p.suffix not in SKIP_SUFFIXES]
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def version_of(root: Path) -> str:
    """Mã ngắn của bản code trong thư mục root (đổi khi bất kỳ file code nào đổi). Đọc lại đĩa mỗi lần gọi."""
    h = hashlib.sha256()
    for p in code_files(root):
        h.update(p.relative_to(root).as_posix().encode("utf-8") + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()[:12]


@functools.lru_cache(maxsize=4)
def code_version(root: Path = config.APP_ROOT) -> str:
    """Bản code tiến trình này đang chạy (tính một lần lúc khởi động)."""
    return version_of(root)


def agent_zip(username: str, database_url: str, root: Path = config.APP_ROOT, site_url: str = "") -> bytes:
    """Zip cài agent cho một tài khoản. Chứa mật khẩu CSDL: chỉ đưa cho đúng người đã đăng nhập.
    site_url: địa chỉ website (mục "Mở website" ở menu biểu tượng khay). auto_update: agent tự cập nhật khi website có
    bản mới (automation/updater.py) — thư mục cài từ zip là của agent, chép đè code được."""
    local = {"database_url": database_url, "agent_user": username, "auto_update": True,
             **({"site_url": site_url} if site_url else {})}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in code_files(root):
            z.write(p, p.relative_to(root).as_posix())
        z.writestr("data/local.json", json.dumps(local, ensure_ascii=False, indent=2))
        z.writestr("CHAY-AGENT.txt", (
            "L2M Ops Agent\r\n\r\n"
            "1. Bat VPN cong ty.\r\n"
            "2. Nhay dup agent.bat. Lan dau tu cai Python + thu vien (vai phut, can Internet).\r\n"
            "3. Agent chay ngam: cham tron o khay he thong (goc phai thanh tac vu, co the nam trong nut ^).\r\n"
            "   Bam vao cham tron de xem cua so log; chuot phai de tat agent. Agent tu bat cung Windows.\r\n"
            "   Mo lai agent.bat hoac bam 'Hien cua so agent' tren website cung hien cua so log.\r\n"
            "4. Agent dang tat thi website tu bat: trinh duyet hoi mo 'L2M Ops Agent' -> tick Always allow -> Open.\r\n"
            "5. Website co ban moi thi agent tu cap nhat (tai code tu GitHub, tu khoi dong lai) - khong can tai lai zip.\r\n\r\n"
            f"Agent nay chay lenh cua tai khoan '{username}'. Khong gui thu muc nay cho nguoi khac\r\n"
            "(co san dia chi CSDL chung va tai khoan cua ban).\r\n"))
    return buf.getvalue()


# Tài liệu cho thành viên + file hướng dẫn cho từng loại AI (Codex / Cursor đọc AGENTS.md, Claude Code đọc CLAUDE.md,
# Gemini CLI đọc GEMINI.md, GitHub Copilot đọc .github/copilot-instructions.md — tất cả trỏ về cùng quy định).
# Tài liệu cho thành viên viết bằng tiếng Anh (team có thành viên nước ngoài).
STARTER_DOCS = ("PLUGIN_QUICKSTART.md", "PLUGIN_GUIDE.md", "ROADMAP.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md",
                ".github/copilot-instructions.md", "make-plugin.bat")
PROMPT_FILE = "AI_PROMPT.md"
ANSWER_FILE = "ai-answer.txt"
SAMPLE_ID = "example_notes"


def starter_zip(root: Path = config.APP_ROOT) -> bytes:
    """Bộ khởi đầu cho thành viên làm plugin: code nền tảng (không có data/ — không có địa chỉ CSDL), plugin mẫu, quy định,
    prompt cho AI dạng chat và make-plugin.bat (tách câu trả lời của AI thành thư mục plugin)."""
    files = code_files(root) + [root / f for f in STARTER_DOCS if (root / f).is_file()]
    plug = root / "plugins"
    if (plug / "__init__.py").is_file():
        files.append(plug / "__init__.py")
    if (plug / "_template").is_dir():
        files += [p for p in sorted((plug / "_template").rglob("*"))
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix not in SKIP_SUFFIXES]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files:
            z.write(p, p.relative_to(root).as_posix())
        z.writestr(PROMPT_FILE, ai_prompt(root).encode("utf-8"))
        z.writestr(ANSWER_FILE, "﻿Delete this line, paste your AI's WHOLE answer here, save the file, then double-click "
                   "make-plugin.bat.\r\n".encode("utf-8"))
    return buf.getvalue()


def sdk_reference() -> str:
    """Danh sách hàm của core.sdk (chữ ký + docstring), lấy thẳng từ code nên luôn khớp bản đang chạy."""
    import inspect

    from . import sdk

    funcs = [fn for name, fn in vars(sdk).items()  # sdk.use: chỉ cho script / test, không dùng trong trang plugin
             if inspect.isfunction(fn) and fn.__module__ == sdk.__name__ and not name.startswith("_") and name != "use"]
    funcs.sort(key=lambda fn: inspect.unwrap(fn).__code__.co_firstlineno)
    out = []
    for fn in funcs:
        try:
            sig = str(inspect.signature(fn, eval_str=True))
        except Exception:  # noqa: BLE001 — kiểu không tính được thì để nguyên chữ
            sig = str(inspect.signature(fn))
        out.append(f"### sdk.{fn.__name__}{sig}\n\n{inspect.getdoc(fn) or ''}\n")
    out.append(f"### sdk.SDKError\n\n{inspect.getdoc(sdk.SDKError)}\n")
    return "\n".join(out)


def _template_files(root: Path) -> list[tuple[str, str]]:
    folder = root / "plugins" / "_template"
    order = {"plugin.toml": 0, "__init__.py": 1, "page.py": 2, "locales.py": 3, "README.md": 4}
    out = []
    for p in sorted((p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts),
                    key=lambda p: (order.get(p.name, 9), p.as_posix())):
        text = p.read_text(encoding="utf-8").replace('"rename_to_folder_name"', f'"{SAMPLE_ID}"')
        out.append((p.relative_to(folder).as_posix(), text))
    return out


def ai_prompt(root: Path = config.APP_ROOT) -> str:
    """Prompt tự đủ cho AI bất kỳ (kể cả AI dạng chat không đọc được kho code): vai trò, quy trình, định dạng trả lời,
    toàn bộ quy định, tham khảo core.sdk, thư viện có sẵn, plugin mẫu. Dựng từ file thật nên luôn khớp nền tảng."""
    import importlib.metadata

    from . import plugins

    guide = (root / "PLUGIN_GUIDE.md").read_text(encoding="utf-8")
    req = [re.split(r"[\s;<>=!~\[(]", line.split("#")[0].strip())[0]
           for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines() if line.split("#")[0].strip()]
    # Không liệt kê thư viện nền tảng dùng riêng: CSDL, trình duyệt, AI (plugin dùng AI chung qua sdk.ai()).
    libs = [n for n in dict.fromkeys(req) if n not in ("tomli", "psycopg", "psycopg-pool", "playwright", "anthropic", "openai")]
    libs += [m for m in ("numpy", "requests") if m in plugins.allowed_third_party() and m not in libs]
    try:
        st_version = importlib.metadata.version("streamlit")
    except importlib.metadata.PackageNotFoundError:
        st_version = "1.66"
    sample = "\n\n".join(f"FILE: plugins/{SAMPLE_ID}/{rel}\n```{_LANG.get(Path(rel).suffix, 'text')}\n{text.rstrip(chr(10))}\n```"
                         for rel, text in _template_files(root))
    return AI_PROMPT.format(guide=guide.strip(), sdk=sdk_reference().strip(), libs=", ".join(libs), st_version=st_version,
                            sample=sample, sample_id=SAMPLE_ID)


_LANG = {".py": "python", ".toml": "toml", ".md": "markdown"}

AI_PROMPT = """# Task for the AI: build a plugin for the L2M Ops platform

> **User:** attach this file to your AI (ChatGPT, Gemini, Microsoft Copilot, Claude, Cursor…) or paste all of it, then add:
> what your app does, who uses it, data in / out, your L2M Ops website account, and (if any) your old app's code.

## 1. Your role (AI)

You are a careful Python / Streamlit developer. The user works in game operations and may not be a programmer: explain
briefly and simply, **in the language the user writes in** (English or Vietnamese).

Task: create a new **plugin** for the L2M Ops platform (the team's internal Streamlit website), or turn the user's existing
app into one, following **every** rule in section 4. You cannot run the platform: its checker will read the code you write
and report problems, and the user will paste them back for you to fix.

## 2. Process

1. If important information is missing, ask first — at most 5 questions, all in one message: what the app does, who uses
   it, data in / out (Excel files? manual input? fetched from where?), the user's L2M Ops website account (for `owners`),
   whether there is an existing app / code.
2. Propose briefly: the plugin `id`, the pages, the data collections and fields (use the **shared ID fields**, section 5.2
   of the rules).
3. Return **every** file in exactly the format of section 3.
4. When the user pastes the checker's problem list: fix everything and return **every** changed file, in the same format.
5. Later changes (new features, fixes): bump `version` in plugin.toml and add a line to the "Changes" section of README.md.
6. An existing app with data: add an "Import data" button (upload an Excel / CSV export of the old app → `sdk.save`).
7. Things the platform does not support yet (scheduled runs, VPN / browser automation, libraries outside the list, keys):
   never work around them by breaking the rules — build what can run, write the need in the README section
   "Needs from the platform" and tell the user to contact the admin.

## 3. Answer format — required (the platform splits your answer into files using this format)

Each file is a line `FILE: <path>` immediately followed by one code block with the file's **complete** content:

FILE: plugins/<id>/plugin.toml
```toml
id = "<id>"
...
```

FILE: plugins/<id>/page.py
```python
...
```

END OF FILES

- Paths are always `plugins/<id>/<file name>`; never create files outside that folder.
- Required: `plugin.toml`, `__init__.py` (empty code block), `README.md`, the page files; `locales.py` is recommended.
- Always write each file **in full** — never abbreviate with "… unchanged".
- Never use ``` inside a file's content (README.md included).
- Put explanations (if any) **before** the first FILE line; end your answer with the line `END OF FILES`.

## 4. Platform rules (PLUGIN_GUIDE.md)

{guide}

## 5. Complete `core.sdk` reference

Use only the functions below (`from core import sdk`). There are no others.

{sdk}

## 6. Libraries and versions

- Allowed libraries: the Python standard library + {libs}. No other libraries.
- The platform runs Streamlit {st_version}:
  - use `st.rerun()` (there is no `st.experimental_rerun`), `st.cache_data` / `st.cache_resource`; never `st.experimental_*`;
  - tables: `st.dataframe(..., hide_index=True, width="stretch")` — use `width="stretch"` instead of `use_container_width=True`;
  - never read `st.secrets` directly — use `sdk.secret("NAME")`.
- Python ≥ 3.10.

## 7. Sample plugin (follow this structure and this use of sdk)

The sample below is written in the required answer format; the user's plugin replaces `{sample_id}` with its own id.

{sample}

END OF FILES
"""

