from pathlib import Path


session = Path("codex/rootfs/usr/local/bin/codex-session")
text = session.read_text(encoding="utf-8")
old = '''if [[ "$session_persist" == "true" ]]; then
  tmux_socket="${user_root}/tmux.sock"
  if [[ -e "$tmux_socket" && ! -S "$tmux_socket" ]]; then
    rm -f "$tmux_socket" || true
  fi

  su-exec "$session_uid:$session_gid" env "${session_env[@]}" \\
    tmux -S "$tmux_socket" new-session -A -s codex -c "$work_dir" \\
    "exec /usr/local/bin/codex-shell"
  tmux_status=$?

  if [[ "$tmux_status" -ne 0 ]]; then
    echo "[WARN] Persistent tmux session failed with exit code ${tmux_status}; starting Codex without tmux for this connection." >&2
    exec su-exec "$session_uid:$session_gid" env "${session_env[@]}" \\
      /usr/local/bin/codex-shell
  fi

  exit 0
fi
'''
new = '''if [[ "$session_persist" == "true" ]]; then
  tmux_socket="${user_root}/tmux.sock"
  if [[ -e "$tmux_socket" && ! -S "$tmux_socket" ]]; then
    rm -f "$tmux_socket" || true
  fi

  tmux_env=(su-exec "$session_uid:$session_gid" env "${session_env[@]}")

  if ! "${tmux_env[@]}" tmux -S "$tmux_socket" has-session -t codex 2>/dev/null; then
    if ! "${tmux_env[@]}" tmux -S "$tmux_socket" new-session -d -s codex -c "$work_dir" \\
      "exec /usr/local/bin/codex-shell"; then
      echo "[WARN] Persistent tmux session could not be created; starting Codex without tmux for this connection." >&2
      exec su-exec "$session_uid:$session_gid" env "${session_env[@]}" \\
        /usr/local/bin/codex-shell
    fi
  fi

  # Browser terminals need xterm/ttyd to own mouse selection and scrollback.
  # Match the Home Assistant Advanced SSH & Web Terminal behavior: tmux
  # persistence remains enabled, but tmux mouse reporting is disabled under ttyd.
  if ! "${tmux_env[@]}" tmux -S "$tmux_socket" set-option -g mouse off; then
    echo "[WARN] Unable to disable tmux mouse mode for the ttyd session." >&2
  fi

  "${tmux_env[@]}" tmux -S "$tmux_socket" attach-session -t codex
  tmux_status=$?

  if [[ "$tmux_status" -ne 0 ]]; then
    echo "[WARN] Persistent tmux session failed with exit code ${tmux_status}; starting Codex without tmux for this connection." >&2
    exec su-exec "$session_uid:$session_gid" env "${session_env[@]}" \\
      /usr/local/bin/codex-shell
  fi

  exit 0
fi
'''
if text.count(old) != 1:
    raise SystemExit(f"persistent tmux block: expected 1 match, got {text.count(old)}")
session.write_text(text.replace(old, new, 1), encoding="utf-8")


test = Path("codex/tests/test_modernization.py")
t = test.read_text(encoding="utf-8")
constant_marker = 'SHELL = CODEX_DIR / "rootfs/usr/local/bin/codex-shell"\n'
if t.count(constant_marker) != 1:
    raise SystemExit("SESSION constant marker mismatch")
t = t.replace(
    constant_marker,
    constant_marker + 'SESSION = CODEX_DIR / "rootfs/usr/local/bin/codex-session"\n',
    1,
)

method_marker = "    def test_prepare_mcp_keeps_bearer_value_out_of_server_json(self):\n"
method = '''    def test_persistent_ttyd_session_disables_tmux_mouse(self):
        session_text = SESSION.read_text(encoding="utf-8")
        patch = MOBILE_PATCH.read_text(encoding="utf-8")
        self.assertIn('tmux -S "$tmux_socket" set-option -g mouse off', session_text)
        self.assertIn('tmux -S "$tmux_socket" attach-session -t codex', session_text)
        self.assertNotIn("installDesktopShiftSelectionScroll", patch)
        self.assertNotIn("desktopSelectionAnchor", patch)

'''
if t.count(method_marker) != 1:
    raise SystemExit("test method insertion marker mismatch")
test.write_text(t.replace(method_marker, method + method_marker, 1), encoding="utf-8")
