# Promptfoo — CartFlow recovery copy matrix

See **`../docs/operational/ENTERPRISE_TESTING.md`** for the full runbook (k6, Sentry, Playwright, CI exports).

Quick start:

```bash
npm install
python ../scripts/generate_promptfoo_scenarios.py
npx promptfoo eval -c promptfooconfig.yaml --no-cache
```

The stub provider (`cartflowStubProvider.js`) does not call external LLMs. Swap the `providers` block in `promptfooconfig.yaml` for Anthropic/OpenAI when auditing `main.generate_recovery_message` with real keys.
