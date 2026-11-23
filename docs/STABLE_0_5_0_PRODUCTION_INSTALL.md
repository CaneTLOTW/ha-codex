# Stable Codex 0.5.0 — Produktions-Installationsauftrag

Status: **Vorbereitet, noch nicht ausgeführt.** Die Developer-Version `0.5.0-dev.4` wurde vom Betreiber am 23.11.2026 nach Tests als erfolgreich bestätigt. Die Einzeltests sind nicht durch separate HAOS-Maschinenprotokolle dokumentiert. Stable `0.4.36` wurde nicht aktualisiert.

## 1. Freigabekriterien

- [ ] Stable-Release-PR auf Basis von `main` geprüft und freigegeben (keine direkte Zusammenführung der divergierten `deployment`-Historie).
- [ ] Stable-Version `0.5.0` behält App-Name **Codex**, Ingress, `boot: auto` und sämtliche vorhandenen Benutzeroptionen.
- [ ] `remote_control_enabled` ist optional und standardmäßig `false`; `addons_access` bleibt standardmäßig `read_only`.
- [ ] PR-CI und Stable Build für AMD64 und ARM64, signiertes Multiarch-Manifest, konkrete unveränderliche Image-Digests und Release-Tag nachgewiesen.
- [ ] Betreiber gibt die konkrete Stable-Installation explizit frei, nachdem ihm vorher Versions-/Optionsdaten und Backup vorgelegt wurden.

## 2. Read-only Preflight auf Home Assistant

1. **Live** Supervisor-App-IDs, laufende Versionen, Images, Zustände, Installationsquelle und Update-Optionen für **Codex** und **Codex Deployment** ermitteln. Historische IDs nicht übernehmen.
2. Stable-Konfigurationsoptionen einschließlich `session_persistence` (beim Betreiber bereits aktiviert), `enable_mcp`, Modell, Berechtigungen, `addons_access`, eventuelle Environment-Werte und `auto_update` auslesen. Geheimnisse nur redigiert dokumentieren.
3. Vollständige, restorable Sicherung der Stable-App-`/data` und der Optionen inklusive `state_5.sqlite`, auth, Sessions erstellen und die Rücksicherungsmöglichkeit bestätigen.
4. Vorherige Stable-Version `0.4.36` und Image-Digest sowie einen möglichen Rückweg notieren. Keine Kopie aus dem Developer-`/data` nach Stable.
5. App Store (**Einstellungen → Apps → App Store**, nicht HACS-Marketplace) auf Stable-`#main` aktualisieren; prüfen, dass exakt `0.5.0` angeboten wird. **Auto-Updates ausgeschaltet lassen.**

## 3. Ausführung nur nach Freigabe

1. Stable-Codex anhalten bzw. aktualisieren, ohne andere Home Assistant Apps oder das System neu zu starten.
2. Exakt die freigegebene Stable `0.5.0` installieren; existierendes `/data` und Optionen erhalten.
3. Stable-Codex öffnen: normaler TUI-Start ohne `pytest`, `SQLite code 14` oder Daemon `Permission denied`.
4. `Strg+C → codex → Strg+C → codex resume --last` prüfen; bestehende Sitzungen weiterhin verfügbar.
5. Read-only HA MCP-Abfrage durchführen und /addons-Sandbox in einer synthetischen Testumgebung überprüfen.
6. Firefox/HA-Ingress-WebSocket-Verbindungsabbruch und automatische Wiederverbindung prüfen, ohne zur anderen HA-Seite zu wechseln. tmux-Sitzung muss erhalten bleiben.
7. Externe Datenträger und SSH-Privatdateien nicht mit pauschaler Rechtevergabe verändern. Prüfen, dass keine Rechte unerwartet angepasst wurden.
8. Remote Control optional OFF belassen, sofern gesonderte iOS-Kopplungsabnahme nicht nachgewiesen oder gewünscht ist.
9. Stable- und Developer-Versionsstand, Autoupdate-Einstellungen, Sitzung und Image-Digests nachher erneut auslesen.

## 4. Abbruch und Rollback

Bei verlorenem Zugriff, SQLite-/Auth-Fehlern, verletzten Dateirechten, Abbruch des Reconnects oder kritischen MCP-Problemen **nur Stable Codex** stoppen und auf das bekannte `0.4.36`-Image mit zuvor gesicherten Optionen/`/data` zurückgehen. Keine Datenbank löschen, keine `/data`-AppArmor-Ausführungsrechte erweitern und keine persönlichen Tokens nach GitHub übertragen.

## 5. Abschlussprotokoll

- Freigegebener Stable-PR, Commit und Image-Digest:
- Version/ID und Backup der Stable-App vor dem Update:
- Abnahmeprotokoll `0.5.0-dev.4` / Issue #42:
- CLI-/SQLite-/Restart-/MCP-/WebSocket-Ergebnisse:
- App-Version, Optionen, Image und Session nach Update:
- Rollback-Bereitschaft und Betreiberfreigabe:

Bezug: Developer-Abnahme #42, Produktionsgate #41, Restart-Fix #47.
