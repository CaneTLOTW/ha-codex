# Home Assistant coding-agent app ecosystem (Issue #16)

Snapshot checked 2026-11-22 using latest visible public commits, not a ranking or claim of functional equivalence.

| Project | Last visible commit | Focus/overlap |
| --- | --- | --- |
| [ambient-home-systems/ha-codex](https://github.com/ambient-home-systems/ha-codex) | 2026-11-20 | Codex sidebar app; frequent bundled CLI updates (0.171.0) |
| [jgassens/codex-terminal-pro](https://github.com/jgassens/codex-terminal-pro) | 2026-11-01 | Broad terminal, sign-in and upload features |
| [moryoav/home-assistant-codex](https://github.com/moryoav/home-assistant-codex) | 2026-11-21 | Worker plus HA integration; GPT-6.2 models |
| [christinloehner/haos-codex-addon](https://github.com/christinloehner/haos-codex-addon) | 2026-03-14 | Simpler terminal App |
| [samabsalom/codexhass](https://github.com/samabsalom/codexhass) | 2026-03-27 | Simpler persistent tmux terminal |
| [magnusoverli/opencode](https://github.com/magnusoverli/opencode) | 2026-11-20 | OpenCode App; direct LAN access beta |
| [ESJavadex/claude-code-ha](https://github.com/ESJavadex/claude-code-ha) | 2026-11-17 | Claude terminal; mobile clipboard improvements |

## Practical observations

- **Shared transport concern:** another terminal project reports 'Press Enter to Reconnect' under Home Assistant ingress (https://github.com/magnusoverli/opencode/issues/218). Cross-project information should inform HA-Codex Issue #34 without assuming the exact same root cause.
- **Uploads:** Codex Terminal Pro and Claude terminal may provide architecture/UI references for #13, but file-transfer APIs, credentials and licensing must be independently reviewed before copying.
- **Worker architecture:** moryoav's integration addresses HA automations/background actions rather than replacing the interactive terminal; separate design track, not a drop-in.
- **Tool lifecycle:** public activity in several projects is recent, but a recent commit by itself does not prove security review or functional maturity.
- **Maintainer outreach:** prefer specific, independently reproducible bug reports/patches with links and attribution, not bulk cross-posting or reusing someone else's project source without license review.

## Recommendation

Keep the current stable Codex terminal architecture, fix WebSocket reliability (#34) and permission startup (#32) first, then investigate upload UX (#13). Consider the worker-plus-HA-integration model only as a companion.

This research fulfills the dated refresh requirement, but remains historical the moment new commits ship. No third-party code was copied.
