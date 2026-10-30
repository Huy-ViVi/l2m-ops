# Instructions for GitHub Copilot — L2M Ops repository

Follow `AGENTS.md` at the repository root (shared rules for every AI) and `PLUGIN_GUIDE.md` when working on a plugin. Summary:

- Members' plugins live in `plugins/<id>/`; only create / change files in the plugin being worked on. New plugin: copy
  `plugins/_template`.
- Use the platform only through `from core import sdk`; never import other `core.*` modules, `ui`, `views`, `automation`
  or another plugin.
- Save data with `sdk.save` / `sdk.load` using the shared ID fields (`product_key`, `item_id`, `market`, `region`, `date`…).
- Widget / `st.session_state` keys use `sdk.key("…")`; displayed text `sdk.t("…")` with `locales.py` for the other
  language; check `sdk.can_edit()` before saving; secrets via `sdk.secret("NAME")`; current time via `sdk.now()`.
- After changes run `python tools/check_plugins.py plugins/<id>` until it reports `OK`.
