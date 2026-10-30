# L2M Ops platform roadmap

Goal: every team member's app runs on one shared platform — one sign-in, shared data, one menu — and the information in
those apps is then **linked together** so the team can work as smoothly as possible.

Principles throughout:
- Each feature is a plugin.
- Plugins use the platform only through `core.sdk`.
- Plugins link to each other through shared data, never by calling each other's code.

That way, when the platform moves to the internal server or changes internally, plugins do not need changes.

## Phase 1 — Bring everyone's apps onto the platform *(in progress)*

**The platform already has:**
- The plugin frame:
  - The menu is built automatically from `plugins/<id>/plugin.toml`.
  - A broken plugin does not break the rest.
- `core.sdk`:
  - Saves data to the shared database, with edit / delete history.
  - Permissions, the selected game, the master file, the Item ID table, AI, secrets.
- The rules `PLUGIN_GUIDE.md`, the quickstart `PLUGIN_QUICKSTART.md`, and AI instructions:
  - `AI_PROMPT.md` for chat AIs;
  - `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `.github/copilot-instructions.md` for folder-based AIs.
- The **Team plugins** page:
  - announcement, plugin list;
  - AI prompt download, paste-and-check of AI answers, zip check, submission;
  - starter kit, rules, roadmap.
- Automatic checks: `tools/check_plugins.py`, and CI after every push.

**Admin tasks:**
1. Send the announcement to the team, with the link to the **Team plugins** page.
2. Add plugin authors to the code repository. People without access submit a zip through the website.
3. Pick up submitted plugins (Activity history, type *Plugin submission*) and put them in `plugins/<id>/`.
4. Add the libraries / secrets plugins need.
5. Collect the "Needs from the platform" sections of plugin READMEs to build in phase 3.

**Member tasks:**
1. Give `AI_PROMPT.md` to your AI (or open the starter kit with a folder-based AI).
2. Turn your existing app into a plugin.
   - Save data through sdk, using the **shared ID fields** (section 5.2).
   - Include an import button for your old app's data.
3. Check, try it, submit.

**Done when:** every team app runs as a plugin on the website, with real data in the shared database.

## Phase 2 — Link the information

Starts once plugins hold real data.

1. Review the data every plugin saves (the Team plugins page shows record counts per plugin), and agree on any missing
   shared IDs together.
2. **Shared catalogs** kept by the platform: packages (Product Key), items (Item ID), updates (region + version + date),
   translation terms, markets.
3. **A link table** "A → relation → B" that any plugin can write to (e.g. KR update → introduces → item 812;
   package → contains → item; term → is the translation of → item), with sdk functions to write / read links.
4. **Detail pages** for a package / item / update: each plugin contributes a panel (master content, setup history,
   performance, translations, related overseas updates…).
5. **Global search** across every plugin's data.

**Done when:** opening a package or an item shows the information of every related plugin on one page.

## Phase 3 — Background work

1. **Scheduled runs** (e.g. collecting updates every morning): plugins declare a schedule in plugin.toml.
   - CI schedules at first.
   - On the internal server once it is available.
2. **Agent jobs for plugins:** work that needs the VPN / a browser (NC tool, MyTool) runs through the agent on each
   member's machine, like the existing features.
   - The admin reviews every job, since this code runs on the whole team's machines.
3. **File storage** for large files outside the database, so the database does not fill up.

## Phase 4 — Move to the internal servers

When permissions are granted: code on the internal GitLab, website and database on the internal hosting (Dokploy).

1. Set up Postgres and the website there, move the data over from the current database.
2. Run scheduled work there.
3. Switch the agent, the website and users to the new addresses.

Plugins need no changes, because they only use `core.sdk`.

## Phase 5 — AI assistant across plugins

Questions and answers over the linked data of every plugin. Example: "which items in next week's TW update are not
translated yet, which similar packages already sold in SEA and how did they do?"
