# Codex model selection and usage

Tracking: #15. Reviewed 2026-11-22. This guide is about **Codex sessions launched from the Home Assistant App**, not Home Assistant's own LLM integrations.

## Choosing a model

- **Quick configuration inspection, log triage and narrow YAML changes:** prefer a smaller/cost-efficient model supported by your installed Codex CLI.
- **Complex Home Assistant issues, multi-file code changes and security review:** choose a more capable coding model; check its output and run validation before deployment.
- **Uncertain work:** start with a scoped diagnosis, ask Codex to show a diff and run tests; escalate the model only when necessary.

The available model names change with Codex releases. The `default_model` select list in `codex/config.yaml` describes the available **startup options** in this particular App version; `/model` inside Codex can change the session model where supported. This does not guarantee your account has access to every model in the list.

## Defaults and billing

The current stable image keeps the already established startup default `gpt-5.6-sol`. We **do not silently change this setting**: changing it alters task quality and usage for existing users. Users may choose a more economical option in the HA App configuration.

Check the [official Codex pricing and usage documentation](https://learn.chatgpt.com/docs/pricing) before comparing plans, fast modes, purchased credits or token rates. Model rates and promotional periods change; **do not treat copied older issue tables as permanent prices**. Subscription-included usage, purchased credit overages and API billing are different accounting contexts.

A useful practice is to review resource use after large sessions rather than assume that faster/cheaper per-token models always result in a lower total task cost. Repeated tool calls, large logs and long context windows matter.

## Safety for Home Assistant edits

1. Explain scope and affected files before editing.
2. Keep secrets and tokens out of prompts, Git history and terminal output.
3. For YAML: check syntax and configuration, inspect the full diff, then deploy.
4. For changes to automations or devices, prefer an explicit rollback path and a real HA readback.
5. Avoid granting `full_access` merely because a task is difficult.
