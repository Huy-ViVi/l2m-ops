# L2M Ops plugin rules

> For team members **and the AI helping them** (ChatGPT, Gemini, Copilot, Claude, Cursor…).
> AI: read this whole file before writing code, follow every section, and run `tools/check_plugins.py` until it reports OK.
> The automatic checker (on your machine, on the website and on GitHub) blocks everything listed in section 12.

## 1. What a plugin is

- Each member's feature (app) is **one plugin**: **one folder** `plugins/<id>/` in the platform's code repository.
- The platform handles the shared parts: sign-in, permissions, game selection, language, menu, shared data storage,
  activity history, AI.
- A plugin only handles its own business logic and uses the platform through **one single entry point**: `from core import sdk`.
- A plugin **never calls another plugin's code**. Plugins are linked through **shared data** (section 5). This is what makes
  linking everyone's information possible in phase 2.
- **Who can change what:**
  - Members have full control over their own plugin folder.
  - Only the platform admin changes the core: `core/`, `ui/`, `views/`, `automation/`, `tools/`, `app.py`, `requirements.txt`.

## 2. Folder structure (required)

```
plugins/<id>/
├── plugin.toml     manifest (section 3)
├── __init__.py     empty
├── README.md       plugin description, following the template (section 9)
├── page.py         a page; more pages = more files
├── locales.py      (optional) translations, section 8
└── …               helper code files, small images
```

- `<id>`:
  - Lowercase ASCII letters, digits and `_`, 3–32 characters, starting with a letter. Examples: `update_tracker`,
    `translation_hub`, `package_monitor`.
  - Set it once and **never change it**: saved data is tied to the id.
- Size: the whole folder at most 5 MB, each file at most 2 MB. Large data is saved through sdk (section 5).
- Quickest start: copy `plugins/_template` (the sample plugin) to `plugins/<id>`.

## 3. plugin.toml

```toml
id = "update_tracker"              # same as the folder name
name = "Overseas updates"          # name shown in the menu
description = "Collects and summarises KR/TW/JP updates."
version = "0.1.0"                  # bump on every update
owners = ["myly"]                  # website accounts of the people in charge (one or more)
icon = ":material/public:"         # :material/<name>: (fonts.google.com/icons) or one emoji
section = "Market"                 # menu group; empty = "Plugin"
access = "all"                     # all = everyone signed in; admin = admins only
games = []                         # [] = every game; ["l2m"] = only when Lineage2M SEA is selected

[[pages]]
file = "page.py"
title = "Overseas updates"
icon = ":material/public:"

[[pages]]                          # a second page (if any)
file = "report.py"
title = "Update report"
```

Do not use the platform's own menu groups as `section`: "Functions" / "Chức năng", "Team", "System" / "Hệ thống".

## 4. Writing a page

- A page is a **Streamlit** Python file. It reruns from top to bottom every time the user interacts, like any Streamlit app.
- First line of the page: `sdk.header(sdk.t("Title"))`.
- **Do not** call `st.set_page_config`, `st.navigation` or `st.Page` — the platform does that.
- **Widget keys and `st.session_state` keys must start with `<id>_`**, because every page shares one session. The easy way is
  `sdk.key("name")`:
  ```python
  st.text_input("Keyword", key=sdk.key("q"))      # -> "update_tracker_q"
  st.session_state[sdk.key("picked")] = 5
  ```
- Import your own helper code with `from . import helpers` or `from plugins.<id> import helpers`.
- From the platform, import only `core.sdk`. Never import `core.store`, `core.db`, `ui`, `views`, `automation` or another plugin.
- **View-only** users: check `sdk.can_edit()` before showing save / edit / delete buttons.
- If a plugin crashes while running, the platform catches it and shows the error on that plugin's page only. Still, catch
  business errors yourself (wrong file template, missing columns…) and explain them clearly.
- Slow work: wrap it in `st.spinner`. Data read many times: use `st.cache_data` (include `sdk.game_id()` in its arguments).
- Current time: use `sdk.now()` (Vietnam time), not `datetime.now()` — the server runs on UTC.

## 5. Data

### 5.1 Saving and reading

- Data that must be kept is **saved only through sdk**, into the team's shared database.
- Do not write files to disk to keep data: the website's disk is wiped on every restart.
- Do not use your own database (sqlite, a separate Postgres) or your own Google Sheet as the main storage.

| Function | Use |
|---|---|
| `sdk.save("updates", records, key="id")` | Add or overwrite. Same key = overwrite; the old version is kept in history. Returns how many records changed. |
| `sdk.load("updates", region="KR")` | Read every record, optionally filtered by field. Each record also has `_key`, `_updated_by`, `_updated_at`. |
| `sdk.get("updates", "kr-2026-10-29")` | Read one record by key. |
| `sdk.delete("updates", keys)` | Delete; the old version is kept in history. |
| `sdk.history("updates", key)` | Old versions. Restore with `sdk.save("updates", old["data"])`. |
| `sdk.collections()` | This plugin's collections and record counts. |
| `sdk.record("Title", summary, files)` | Log an entry in the team's Activity history, with result files (Excel, images…). |

- **A record** is a dict; every value must be JSON-serialisable: text, numbers, True/False, None, lists, dicts. Dates and
  times are converted to text by sdk.
- **Keys:**
  - Every record has a stable key, by default the `id` field.
  - Build the key from the content so that running again does not create duplicates. Examples: `kr-2026-10-29`,
    `web.item195-TH-2026-10-28`.
- **Collection** (name of a group of records): lowercase ASCII, digits, `_`. Examples: `updates`, `terms`, `daily_sales`.
- **Game:**
  - By default data belongs to the game selected in the sidebar.
  - Data shared by every game: pass `game=""` to save / load.
- Each record is at most 200 KB. Attach large files with `sdk.record(..., files={"name.xlsx": bytes})`.

### 5.2 Shared ID fields — required, so that phase 2 can link information

Whenever your data contains the information below, you **must** use exactly these field names and formats:

| Field | Meaning | Format | Example |
|---|---|---|---|
| `product_key` | a package's Product Key | as in the master, without `com.ncv.l2m.` (sdk normalises this field; when you build a key yourself use `sdk.product_key(...)`) | `web.item195` |
| `item_id` | Item ID on NC tool | integer | `79` |
| `item_name` | item name as on the tool / master (English) | text | `Fancy Class Card (11 Times) (Bound)` |
| `market` | shop / selling market | `SG` `ID` `PH` `MY` `TH` `VN` | `TH` |
| `region` | overseas server / version | `KR` `TW` `JP` `NA` `EU` `SEA` … | `KR` |
| `version` | version / update | as written by the source | `2026.10.29` |
| `date` | date | `YYYY-MM-DD` | `2026-10-29` |
| `datetime` | point in time, Vietnam time | `YYYY-MM-DD HH:MM:SS` | `2026-10-29 09:30:00` |
| `currency` | currency | ISO code | `THB` |
| `price` | price | number | `19.99` |
| `lang` | language of a text | `vi` `en` `th` `id` `ko` `ja` `zh-TW` … | `th` |
| `url` | source link | full `https://…` | |

- Do not save a `game` field — sdk adds the game itself.
- Other fields: English names, `snake_case`, ASCII only. Examples: `title`, `summary`, `revenue_usd`.
- Once a field name is in use, never rename it or change its meaning. If something must differ, add a new field.
- List every collection and field in the plugin's README.md (section 9).

### 5.3 Shared platform data (read-only)

- `sdk.master()`: the current *All Product Information* master file of the selected game.
  - `.packages`: packages by Product Key, with name, price, limit, diamonds and item list.
  - `.webshop`: prices by market.
  - `.display_name(product_key)`: display name of a package.
  - `.timeline`: selling schedule.
- `sdk.items()`: the team's shared Item ID table.
- Use these two instead of reading the master file yourself or keeping your own Item ID list.

## 6. Secrets, AI, libraries

- **Never** write API keys, passwords, tokens or database addresses into code or files of a plugin. Instead:
  - In code, read them with `sdk.secret("NAME")`.
  - Send the value privately to the admin, who installs it in the website's secrets as `PLUGIN_<ID>_<NAME>`.
- AI: use `sdk.ai()` — the team's shared AI configuration — with `.text(system, prompt)` and `.json(system, prompt, schema)`.
  Do not call an AI API yourself with your own key.
- Libraries:
  - Only the Python standard library and the libraries in the platform's `requirements.txt` (streamlit, pandas, openpyxl,
    requests…).
  - Need another library: ask the admin, with its name, version and why.
- Also never use: `subprocess`, `os.system`, Playwright / Selenium, reading environment variables directly.

## 7. Background, scheduled and VPN work

Phase 1 does **not** support these inside plugins yet:
- scheduled work (e.g. collecting updates every morning);
- work that needs the company VPN or browser automation (NC tool, MyTool);
- heavy work (more than ~30 seconds, or very large files).

Meanwhile:
- Let the user **click a button to run** short work, or **upload a file** for the plugin to process.
- Write the need in the README section "Needs from the platform" so the admin can build it in phase 3.

## 8. Language

- The team has Vietnamese and international members, and website users choose Tiếng Việt or English in the sidebar.
- Write UI text in **English or Vietnamese** — pick one and use it everywhere in the plugin — and wrap every displayed
  text in `sdk.t("…")`. With numbers use `sdk.t("Saved {n} rows", n=5)`, never an f-string inside `sdk.t`.
- Add `locales.py` with the other language, so every user sees their own language:
  ```python
  VI = {"Saved {n} rows": "Đã lưu {n} dòng"}    # UI written in English -> Vietnamese translation
  EN = {"Đã lưu {n} dòng": "Saved {n} rows"}    # UI written in Vietnamese -> English translation
  ```
  The dicts must be written literally: the platform reads this file without running it.

## 9. Plugin README.md (template)

```markdown
# <Plugin name>
Owner: <account>

## What it does
## Pages
## Saved data
| Collection | Key | Fields | Shared IDs used |
|---|---|---|---|
## Data used from the platform / other plugins
## Needs from the platform
(scheduled runs? VPN? extra libraries? secrets?)
## Changes
- 0.1.0 (YYYY-MM-DD): first version
```

## 10. Trying, checking and submitting

Step-by-step guide for users (chat AIs and folder-based AIs alike): `PLUGIN_QUICKSTART.md`.

1. **Try it on your machine:**
   - Download the *Starter kit* from the **Team plugins** (Plugin của team) page on the website and unzip it.
   - Create the plugin in one of two ways:
     - copy `plugins/_template` to `plugins/<id>`;
     - or paste a chat AI's answer into `ai-answer.txt` and double-click `make-plugin.bat`.
   - Double-click `run.bat`. The plugin appears in the left menu; test data is stored on your machine only.
2. **Self-check** — one of three ways:
   - Run `.venv\Scripts\python.exe tools\check_plugins.py plugins\<id>` until it reports `OK`.
   - On the **Team plugins → Check & submit** page, paste a chat AI's whole answer into the check box.
   - Or zip the plugin folder and upload it on that page.
3. **Submit** — one of two ways:
   - **Code repository** (once the admin has added you):
     - Upload the folder to exactly `plugins/<id>/`; only change your own folder.
     - About 1–2 minutes later the website updates itself.
     - The automatic check runs after every push. If it turns red, fix it right away.
   - **Send a zip on the website:** **Team plugins → Check & submit** → check → *Send the plugin to the admin*. The
     admin publishes it.
4. **On every update:**
   - Bump `version` in plugin.toml.
   - Add one line to the "Changes" section of the README.
5. **Data from an old app:** build an "Import data" button in the plugin (upload an Excel / CSV export of the old app →
   `sdk.save`), so no existing data is lost.

## 11. Checklist before submitting

- [ ] `plugin.toml` has every field; `id` equals the folder name; `owners` are correct website accounts.
- [ ] Only `core.sdk` is imported from the platform; no other plugin is imported.
- [ ] Data is saved through sdk. Shared ID fields have the right names and formats (section 5.2). Record keys are stable.
- [ ] Widget / session_state keys start with `<id>_` (use `sdk.key`).
- [ ] `sdk.can_edit()` is checked before saving, editing, deleting.
- [ ] No keys, passwords, tokens, database addresses or large data files in the folder.
- [ ] Displayed text is wrapped in `sdk.t`; `locales.py` has the other language.
- [ ] README.md has every section; `version` was bumped.
- [ ] `tools/check_plugins.py` reports OK; tried with `run.bat`.

## 12. Blocked automatically

| Blocked | Use instead |
|---|---|
| Missing `plugin.toml` / `__init__.py` / `README.md`, invalid manifest | fix following sections 2–3 |
| Importing `core.*` other than `core.sdk`, `ui`, `views`, `automation`, another plugin | `from core import sdk`; link through data |
| `sqlite3`, `psycopg`, `sqlalchemy` | `sdk.save` / `sdk.load` |
| `anthropic`, `openai` | `sdk.ai()` |
| `subprocess`, `os.system`, Playwright, Selenium | wait for phase 3 (agent); write the need in the README |
| `os.environ`, `os.getenv`, `st.secrets` | `sdk.secret` |
| `st.set_page_config`, `st.navigation` | remove — the platform does it |
| `st.experimental_*` (removed in current Streamlit) | `st.rerun`, `st.cache_data`, `st.query_params` |
| Widget / session_state keys without the `<id>_` prefix | `sdk.key("…")` |
| Libraries not in `requirements.txt` | ask the admin to add them |
| Keys / tokens / passwords / database addresses in files; `.env`, `local.json`, `secrets.toml`, `.db` files | `sdk.secret`; data through sdk |
| Files > 2 MB, folder > 5 MB, Python syntax errors | move data to the database; fix the error |
