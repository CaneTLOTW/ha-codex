# ttyd mobile controls

The Codex App builds ttyd 1.7.7 from source and applies
`ttyd-1.7.7-mobile-keys.patch` before compiling the bundled frontend.

The patch adds a touch-friendly key bar, one-shot `Ctrl` and `Alt` modifiers,
arrow-screen arrow and page-navigation keys, and vertical touch gestures. The
App's tmux configuration maps `PgUp` and `PgDn` to copy-mode navigation when
session persistence is enabled.

This replaces the earlier experimental touch/selection patch. Desktop
selection and normal browser/terminal clipboard behavior remain provided by
ttyd/xterm and are deliberately kept separate from the mobile controls.

To validate the patch against a clean ttyd source tree:

```bash
git clone --depth 1 --branch 1.7.7 https://github.com/tsl0922/ttyd.git /tmp/ttyd-1.7.7
git -C /tmp/ttyd-1.7.7 apply /path/to/ttyd-1.7.7-mobile-keys.patch
cd /tmp/ttyd-1.7.7/html
corepack enable
yarn install --immutable
yarn check
```

The customized ttyd frontend remains covered by ttyd's MIT license, included
beside this file.
