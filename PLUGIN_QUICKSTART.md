# Building an L2M Ops plugin with AI — quickstart for team members

No programming needed:
1. You describe your app.
2. An AI (any AI) writes the code.
3. The platform checks it automatically.
4. The admin publishes it on the team website.

Each app becomes a **plugin**: its own entry in the website menu, sharing sign-in and data with the whole team.

> The website menu and page names below are shown in English when you pick **English** in the sidebar's 🌐 Language box
> (Vietnamese names in brackets).

## What you need

- An L2M Ops website account (ask the admin if you don't have one).
- Any AI, of one of two kinds:
  - **Chat AI**: ChatGPT, Gemini, Microsoft Copilot, Claude.ai… → follow **Option 1**.
  - **Folder-based AI**: Cursor, Claude Code, GitHub Copilot in VS Code, Codex, Gemini CLI… → follow **Option 2**.
- The file **`AI_PROMPT.md`**: download it from **Team → Team plugins (Plugin của team) → Get started (Bắt đầu)**, or get
  it from the admin. It contains every rule, the platform's tools and a sample plugin, so any AI that reads it builds the
  plugin correctly.

> Only use AI tools the company allows for internal data. Never paste passwords, keys or database addresses into an AI.

## Option 1 — Chat AI

1. **Start a new conversation with the AI.**
   - **Attach** the file `AI_PROMPT.md`.
   - If the AI does not accept files, paste its whole content instead. If the AI says it is too long, you must attach the file.
2. **Send a message** (edit the parts in `< >`; you can write in English or Vietnamese):
   ```
   Read AI_PROMPT.md carefully and follow all of its instructions.
   My app: <what it does, who uses it, data in / out, concrete examples>.
   My L2M Ops website account: <account>.
   My old app's code (if any): <attach or paste it here>.
   ```
3. **Answer the AI's questions.** At the end the AI returns the files as `FILE: plugins/<id>/…` blocks, ending with
   `END OF FILES`.
4. **Check:**
   - On the website go to **Team → Team plugins → Check & submit (Kiểm tra & gửi)**.
   - Paste the AI's **whole** answer into the *Paste your AI's answer* box → click **Check**.
   - **Problems found:** click the copy button on the problem list and paste it back to the AI with: "The checker reports
     these problems, fix them all and return every file:". Then check again.
   - **Passed:** ideally try it on your machine (see *Try it on your machine* below), then click **Send the plugin to the admin**.

## Option 2 — Folder-based AI

1. Download the **Starter kit** (Team plugins → Check & submit) and unzip it into its own folder.
2. Open that folder with your AI tool. Each tool reads its own instruction file automatically, and they all point to the
   same rules:
   - Cursor, Codex: `AGENTS.md`;
   - Claude Code: `CLAUDE.md`;
   - Gemini CLI: `GEMINI.md`;
   - GitHub Copilot: `.github/copilot-instructions.md`.
3. Ask the AI: *"Build a plugin for my app following AGENTS.md and PLUGIN_GUIDE.md. My app: … My website account: …"*.
4. The AI checks its own work with `tools\check_plugins.py`. You try it with `run.bat`.
5. Zip the folder `plugins\<id>` → Team plugins → Check & submit → upload the zip → **Send the plugin to the admin**.

## Try it on your machine (recommended)

1. Download the **Starter kit** and unzip it.
2. Create the plugin inside the kit:
   - Option 1: open `ai-answer.txt`, paste the AI's **whole** answer, save, then double-click **`make-plugin.bat`**. It
     creates the plugin folder and checks it.
   - Option 2: the AI has already created the plugin.
3. Double-click **`run.bat`**: the website opens on your machine and your plugin is in the left menu. The first run
   installs Python by itself (a few minutes, needs Internet).

Test data stays on your machine only and never mixes with the team's real data.

## After submitting

- The admin reviews and publishes it; the plugin then appears in everyone's website menu. See its status in the
  **Plugin list** tab.
- **Data from your old app:** use the plugin's "Import data" button (ask your AI to build one).
- **Changes / new features:**
  - Go back to the same conversation with your AI. In a new conversation, attach `AI_PROMPT.md` again together with the
    plugin's current files.
  - Ask for the change; the AI bumps `version`.
  - Check and submit again.
- **Needs the platform does not cover yet** (scheduled runs, VPN / NC tool / MyTool, new libraries, keys): your AI writes
  them in the plugin README section "Needs from the platform". Tell the admin.
- **The team's next step** (Roadmap tab): once everyone's apps are in, the admin links information between plugins. That is
  why data must use the **shared ID fields** (Product Key, Item ID, market…) — the prompt already tells your AI.
