# Issue 26 / PR 27 — vorhandenen Deployment-Kanal aktualisiert und geprüft

Datum: 2026-10-30. **SSH-Hotfix: Source, Builds, Publish und geprüfte Runtime bestanden.** Bestehende Testinstanz **Codex Deployment 1e25a555_codex** tatsächlich auf **0.4.10-dev.2** aktualisiert und zweimal gestartet. Am Ende wieder gestoppt. Separater Befund: zusätzlicher **codex_apps-Connector HTTP401**, daher keine uneingeschränkte Abnahme aller App-Connectoren.

## Autorisierung und Quellstand

Der Benutzer hat die Wiederverwendung der vorhandenen Testinstallation samt gezielter Deployment-Branch-Änderung ausdrücklich mit „go“ freigegeben. Dies ersetzt für diesen Hotfix die frühere Vorgabe, deployment unangetastet zu lassen. Produktion e6fb3748_codex und main bleiben ausgeschlossen.

- Deployment-Basis **c79313b0c93c99ee448471a4659c5c10658a04a1**, Version0.4.10-dev.1.
- Minimaler Produkt-/Testcommit **d577b280293d3f24ddb1e0418d47d3d42b5aea1b**, Version **0.4.10-dev.2**, vier Dateien: gefilterter Helper, Startup-Delegation, bereits geprüfte Regressionstests und Entwicklungsversion. Sonstige divergierende Deployment-Funktionen und ttyd-Patch erhalten; kein Gesamtmerge von main/PR27.
- Gemeinsamer Helper und Regressionstest stammen aus PR27 d01d178 / bereits geprüfter Referenz5834742. Startup-Anpassung gezielt auf den älteren Deployment-Stand angewandt.
- Zwei gpt-6-luna-Unteragenten prüften unabhängig lokale Regression/Sicherheit sowie CI-/Deployment-Readiness. Runtime und Integration koordinierte der Hauptagent.
- Nachfolgender Dokumentationscommit enthält nur diese Acceptance-Artefakte und löst nach den vorhandenen Pfadfiltern keinen erneuten Build/Publish aus. Commit-ID steht im abschließenden PR-Kommentar.

## Source-/CI-/Publish-Gates

| Bereich | Ergebnis | Beleg |
| --- | --- | --- |
| Lokale vollständige Regression | PASS:17 Tests, keine Fehler/Skips | regression/RESULTS.md |
| Bash-Syntax/YAML/Whitespace | PASS | Luna-Regression, CI-Schritte |
| Echtes setfacl/getfacl, fehlendes und fehlschlagendes setfacl mit echtem chmod | PASS, jeweils zweimal auf Fixtures | regression/probe-output.txt und JSON-Snapshots |
| Einzel-Build vor Deployment-Push | PASS | Run41022579641, validate+ein amd64-Build, exakt Commitd577b28 |
| Erneute Deployment-Validierung und amd64-Build | PASS | Run41022780042 |
| Deployment amd64/aarch64 bauen und pushen | PASS | Run41022780048 |
| Multiarch-Manifest veröffentlichen und Registry prüfen | PASS | published_manifest.json |

Der ältere Deployment-Zweig enthält insgesamt17 Tests; die zuvor geprüfte neuere PR-/Testbranch-Basis enthält22. Keine Tests entfernt/deaktiviert, um die Zahlen zu senken. Die vollständige CI-Ausgabe aller17 Tests liegt unter **regression/ci_unittest_output.txt**. CI hatte keine Skips. Der bereits grüne22-Test-Bericht auf issue26-local-test bleibt gültige Historie seiner anderen Basis.

Canary-Run: https://github.com/CaneTLOTW/ha-codex/actions/runs/41022579641
Deployment-Validierung: https://github.com/CaneTLOTW/ha-codex/actions/runs/41022780042
Deployment-Publish: https://github.com/CaneTLOTW/ha-codex/actions/runs/41022780048

Vorabversionstag per regulärem öffentlichem Registry-Pull-Grant geprüft:404, also nicht belegt. Keine Supervisor-Zugangsdaten gelesen. Nach Veröffentlichung geprüftes Manifest:

`ghcr.io/canetlotw/ha-codex:0.4.10-dev.2`

Digest **sha256:88e8860ba83857e88436499beda61959a9dfb93974eded871a5e066f4a6081c7**; Linux amd64 und arm64 vorhanden (zusätzliche unknown/unknown-Attestierungsdeskriptoren sind keine Laufzeitarchitektur).

Kein offizielles Release, kein main-/latest-Publish. Moving tag deployment wurde bestimmungsgemäß aktualisiert. Alle Jobs beim ersten Versuch erfolgreich; keine Retry-/Rerun-Schleife. Budget-/Tarifdaten waren mit den vorhandenen Scopes nicht zugänglich. Tatsächliche Jobzeiten und gerundete Jobminuten stehen in coordinator/workflow_runtime_summary.json; das sind keine bestätigten Abrechnungsbeträge.

## Tatsächliches Update und zwei Startzyklen

Es war **keine dritte Installation und kein manueller Installationsklick nötig**. Die vorhandene Instanz wurde über reguläre HA-Dienste aktualisiert:

1. Ausschließlich hassio.addon_stop für1e25a555_codex.
2. **update.install** auf **update.codex_deployment_update**, **backup=true**. Der MCP-Client lief nach10s in sein Zeitlimit; Readback zeigte anschließend update in_progress=true/dev.2 verfügbar und danach **installed_version=latest_version=0.4.10-dev.2, in_progress=false**. Kein zweiter Updateaufruf.
3. Erster addon_start für1e25a555_codex. Ebenfalls10s Client-Zeitlimit; anschließend HTTP200 am internen Test-Terminal und echte Startup-ACL-Wirkung nachgewiesen.
4. addon_stop; HTTP-Endpunkt danach nicht erreichbar.
5. Zweiter addon_start; danach erneut HTTP200 und unveränderte Fixture-ACLs gegenüber dem ersten Start.
6. Diagnosesitzung aus dem normalen tty-Endpunkt der Testinstanz; danach finaler addon_stop. HTTP-Endpunkt am Ende nicht mehr erreichbar.

Ein Werkzeugfeld success=true trotz eingebettetem Timeout wurde **nicht** als alleiniger Erfolg gewertet. Version, HTTP-Erreichbarkeit und ACLs sind die Readback-Belege. Backup wurde über die reguläre Update-Option angefordert; separate Archiv-ID/Backup-Integrität konnte mit dem vorhandenen Zugriff nicht unabhängig geprüft werden.

## Runtime-Matrix

| Prüfung | Ergebnis | Grenze/Nachweis |
| --- | --- | --- |
| Bestehende Instanz aktualisiert | PASS | HA installed_version0.4.10-dev.2 |
| Zwei echte Starts mit Stop dazwischen | PASS | HTTP200 nach beiden Starts; dazwischen nicht erreichbar |
| Dummy .ssh0700 und Schlüssel0600 | PASS | vor/nach beiden Starts identisch |
| Owner-private0600, außerhalb liegende outside.key0644 | PASS | unverändert |
| Normale YAML / Executable | PASS | erwartete ACLs, YAML0664 / Skript0775 |
| Keine neuen Default-ACLs | PASS | frische Runtime-Fixture ohne Default-ACLs vor/nach beiden Starts |
| Test-Terminal und tatsächlicher Codex-Benutzer | PASS | hostname1e25a555-codex, UID22000/GID0 |
| Lesen/Schreiben aus tatsächlicher Testsitzung | PASS | normal.yaml der neuen Fixture gelesen und beschrieben |
| HA-MCP aus tatsächlicher Testsitzung | PASS | regulärer hass-mcp-wrapper;29 Tools, get_version2026.10.4 |
| Zusätzlicher codex_apps-MCP-Connector | **FAIL: HTTP401** | beobachteter Authentifizierungsfehler beim CLI-Start; keine Auth-Reparatur |
| Echte vorhandene SSH-/Workspace-Metadaten | PASS | alle12 erfassten Pfade unverändert |
| Produktive Startup/Shell/Session-Skripte | PASS | unveränderte SHA256-Hashes |
| Produktives Add-on | PASS/unverändert | e6fb3748_codex0.4.28, kein Update in progress, weiter erreichbar |
| Reale SSH-Anmeldung/HA-SSH-Automation | NOT TESTED | kein Gerätestart/SSH-Automation ausgelöst |
| Vollständige Supervisor-Containerlogs | NOT AVAILABLE | keine Log-API in aktuellen Werkzeugen; Terminal/HTTP/ACL statt behaupteter Logprüfung |
| Abschließender Testzustand | PASS | Testinstanz gestoppt, installiert belassen |

Runtime-Fixture: **/share/issue26-runtime-r66c8lll**. Nur neu angelegte Dummy-Dateien; keine echten Schlüssel erzeugt/kopiert/gelesen. Geerbte ACLs wurden ausschließlich an der neu angelegten Fixture-Wurzel vor Aufbau des Tests entfernt, niemals an Bestandsdaten. Runtime-Snapshots und normaler Testdatei-Schreibzugriff sind in coordinator/ dokumentiert.

Die Test-Diagnose nutzte den regulären tty-WebSocket im Add-on-Netz ohne gefälschte Ingress-/Authentifizierungsheader und ohne Auslesen von Credentials. Codex wurde regulär in der Testsession beendet und deren Diagnoseshell verwendet. HA-MCP lief über den vorgesehenen privilegierten Helper; Supervisor-Tokens blieben darin. Kein Docker-/Host-Zugriff oder direkter Dateizugriff auf geschützte Token-Dateien. Es wurden keine AI-Prompts mit Nutzdaten gesendet.

Die rohe Terminalausgabe wurde nicht veröffentlicht; der zusätzliche codex_apps401-Befund und die minimalen Diagnosefelder wurden sanitisiert festgehalten. **coordinator/terminal_session.json** enthält den tatsächlichen Testhostname, UID, Dateizugriff und HA-MCP-Antwort. Das globale Produktions-MCP wurde nicht als Ersatznachweis ausgegeben.

## Restbefunde und Übergabe

- Der codex_apps-Connector der bestehenden Testsession meldet401 („Could not parse your authentication token“). HA-MCP funktioniert davon getrennt. Ursache und vorheriger Zustand dieses Connectors sind nicht nachgewiesen; der Hotfix änderte keine Authentifizierungslogik. Keine Anmeldung/Tokenrotation vorgenommen. Dieser Befund verhindert eine pauschale Freigabe sämtlicher App-Connectoren, nicht den belegten SSH-/HA-MCP-Test.
- Vorhandene breite Default-/named ACLs bleiben erhalten; keine automatische Reparatur. Eigene /data isoliert den Add-on-Zustand, nicht die gemeinsam gemounteten Workspaces.
- Custom-benannte permissive Schlüssel außerhalb geschützter Verzeichnisse bleiben ein Filterrestrisiko. Neue Dateien anderer UIDs erhalten keine neuen Default-ACLs und könnten Schreibzugriff verlieren. Dies ist keine vollständige Privilegientrennung.
- Testdateizugriff ist für den tatsächlichen UID22000 nachgewiesen; andere Dateieigentümer-/UID-Kombinationen wurden nicht vollständig getestet.
- Keine dritte Test-App installiert oder bestehende Test-App entfernt. Dummy-Fixture und Acceptance-Artefakte für Review erhalten.
- PR27/Issue26 bleiben offen für Reporter-/Reviewentscheidung; kein Merge nachmain und kein produktives Rollout. Keine HA-Core-Neustarts oder Reloads aus diesem Lauf ausstehend. Testinstanz ist gestoppt; für weitere UI-Abnahme nur **Codex Deployment** starten, nicht das produktive Add-on ersetzen.
