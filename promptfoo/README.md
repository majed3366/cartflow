# Promptfoo — CartFlow recovery copy matrix

See **`../docs/operational/ENTERPRISE_TESTING.md`** for the full runbook (k6, Sentry, Playwright, CI exports).

Quick start:

```bash
npm install
python ../scripts/generate_promptfoo_scenarios.py
npm run eval
```

If **`SqliteError: FOREIGN KEY constraint failed`** appears (known with some older promptfoo + local cache), use a fresh CLI and clear the tool cache, then retry:

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.promptfoo" -ErrorAction SilentlyContinue
cd promptfoo
npm run eval:latest
```

Or after `npm install`: `npm run eval:latest` (uses **`npx promptfoo@latest`**).

The stub provider (`cartflowStubProvider.js`) does not call external LLMs. Swap the `providers` block in `promptfooconfig.yaml` for Anthropic/OpenAI when auditing `main.generate_recovery_message` with real keys.
