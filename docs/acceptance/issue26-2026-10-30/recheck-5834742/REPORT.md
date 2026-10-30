# Issue 26 / PR 27 — erneute Source- und Testinstallationsabnahme

Datum: 2026-10-30. **Entscheidung: READY FOR TEST INSTALLATION.**

Das Source-Gate und die geforderten isolierten Sicherheitsprüfungen sind grün. Die Freigabe gilt ausschließlich für die separate lokale Supervisor-Testinstallation von **Codex SSH Hotfix Test**. Sie ist keine produktive Freigabe, kein Build-/Runtime-Erfolgsnachweis und kein Merge-/Release-Gate. Die manuelle Store-Prüfung des konkreten Testeintrags muss vor dem Installationsklick erfolgen.

## Quellstand und Zusammenarbeit

- Branch `issue26-local-test`; getesteter HEAD und enthaltene Referenz: **5834742e21c21a23bb7ec8a9630f7f1e912cebf1**.
- Vorheriger Checkout war sauber auf7140a4b; Fetch und Fast-forward auf5834742 ohne Überschreiben lokaler Änderungen.
- Seit7140a4b änderte sich nur `codex/tests/test_ssh_acl_protection.py`. Produktcode unverändert.
- PR27 aktuell `fix/issue-26-protect-ssh-acls`, HEAD **d01d178ea5e1bbd2e6c7606a2efe03c8dca12c34**, Draft, offen, nicht gemergt. Gemeinsamer Helper, Startup, Dockerfile und Regressionstests stimmen überein; Testmanifest ist bewusst separat.
- Zwei parallele **gpt-6-luna**-Unteragenten: A Regression/Sicherheit, B Build/Deployment-Readiness. Koordinator: Synchronisation, Syntax/YAML, produktive Metadaten, unabhängige Prüfung der Fault-Injection-Methode, gemeinsame Abnahme und GitHub-Dokumentation.
- Dieser anschließende Commit enthält ausschließlich Acceptance-Artefakte. Source-Hashes gegen5834742: `coordinator/tested_source_hashes.json`. Keine Änderungen am bestehenden Deployment-Branch oder an main.

## PASS / FAIL / NOT TESTED

| Prüfbereich | Ergebnis | Nachweis / Grenze |
| --- | --- | --- |
| Referenzcommit enthalten; sauberer Fast-forward | PASS | Quellstand5834742 |
| bash -n codex-start / codex-grant-access | PASS | coordinator/source_checks.json |
| Vollständige unittest-Suite | **PASS: 22 Tests, 0 Fehler, 0 Skips** | regression/unittest-discovery.txt, vollständige Ausgabe |
| YAML-Syntax | PASS | 10 Dateien, coordinator/yaml_syntax.json |
| Testmanifest-Konsistenz | PASS | Name/Slug/Version, manual/experimental, kein image, beide Architekturen |
| Dockerfile statisch | PASS im beschriebenen Umfang | 30 logische Instruktionen, 9 RUN-Shell-Syntaxprüfungen, JSON CMD/ENTRYPOINT, COPY-Quellen; build/dockerfile_static_results.txt |
| Helper wird geliefert und durch bash aufgerufen | PASS | COPY rootfs; Startup-Aufruf geprüft |
| Echtes setfacl/getfacl | PASS, 2 Läufe | regression/real_acl_probe.log und acl_metadata_before_after.json |
| .ssh0700, private Schlüssel0600, owner-only-Dateien | PASS, wiederholt | exakte Vorher-/Nachher-Snapshots |
| Normale YAML bearbeitbar, Skripte weiter ausführbar | PASS im isolierten UID22000-Probeumfang | gewöhnliche ACLs sowie chmod0644→0664 /0755→0775 |
| SSH-Verzeichnisse, nested Workdir, Symlinks, Schlüssel außerhalb .ssh | PASS, wiederholt | echte Fixture-Prüfungen und Suite |
| Keine neuen Default-ACLs; vorhandene geschützte ACL unverändert | PASS | ACL-Snapshots |
| setfacl fehlt → echter chmod-Fallback | PASS, 2 Läufe | chmod_missing_setfacl_before_after.json |
| setfacl vorhanden, echter Aufruf schlägt fehl → echter chmod-Fallback | PASS, 2 Läufe | real_setfacl_failure_before_after.json, inkl. vollständiger xtrace-Ausgabe |
| Tatsächliche produktive SSH-/Workspace-Metadaten unverändert | PASS | 12 Pfade, coordinator/production_metadata_comparison.json |
| git diff --check | PASS | Source-/Abschlussprüfung; keine fachfremden Änderungen |
| Tatsächlicher Docker-/Supervisor-Build amd64/aarch64 | NOT TESTED | kein Build-/Management-Client, keine neuen CI-Jobs |
| Teststore: tatsächlicher voller Slug und Kollisionsfreiheit | NOT TESTED / UI-Prüfung vor Installation | manifestseitig separater Slug, keine vollständige Supervisor-Inventur verfügbar |
| Testinstallation, zwei echte Add-on-Starts, SSH/MCP/Dateizugriffe aus Testinstanz | NOT TESTED | nächster freigegebener Schritt; hier nicht ausgeführt |

### Vollständige Testausgaben / Methoden

Die unveränderte Gesamtsuite wurde mit `python3 -m unittest discover -s codex/tests -v` ausgeführt. Die früheren drei Fehler treten nicht mehr auf. Kein Test deaktiviert oder entfernt, kein sicherheitsrelevanter Skip, keine Anpassung des Produktcodes oder des aktualisierten Regressionstests in diesem Lauf.

Alle echten Rechte-/ACL-Änderungen betrafen ausschließlich neue temporäre Fixtures. Die Skripte und vollständigen Logs liegen im Unterverzeichnis `regression/`; Vorher-/Nachher-Daten sind als JSON verfügbar. UID22000 war Eigentümer der Testdateien. Damit ist aktueller Codex-Zugriff nachgewiesen, nicht der Zugriff eines anderen Benutzers im noch ungebauten Testcontainer.

Fehlendes setfacl wurde nur bei der Shell-Verfügbarkeitsprüfung simuliert; chmod war echt. Für den separaten Fehlerfall wurde eine `find()`-Shellfunktion in einen Kind-Bash-Prozess exportiert. Der unveränderte Helper lief als echtes Bash-Skript wie beim Startup. Die Funktion delegiert an echtes `command find` und ersetzt ausschließlich die ACL-Gruppenoperanden durch einen nachweislich nicht vorhandenen Gruppennamen. Echtes GNU find führt damit echtes setfacl aus; je Lauf drei echte Fehlermeldungen, ACL-find-Status1, chmod-find-Status0 und Helper-Status0. Keine ausführbaren Mock-Dateien und keine Sicherheitsumgehung.

Die erste Probe-Methode (`if source ...`) hätte errexit im gesamten Helper unterdrückt und wurde deshalb verworfen. Die weitere Harness-Anomalie `builtin command find` wurde durch einen minimalen Shell-Repro eingegrenzt; die endgültige Probe verwendet gewöhnliches `command find` mit lokaler Statusbehandlung und regulärem Kindskript. Diese Harness-Korrekturen sind im Unterbericht erklärt. Es bleiben keine ungeklärten Fehler dieses Source-/Sicherheitsgates; tatsächlicher Build und Runtime sind ausdrücklich offene nächste Gates.

## Produktive Bestandsaufnahme und Schutz

Produktion: **e6fb3748_codex 0.4.28**, auto_update=false, kein Update in progress, aktiver Containerhostname `e6fb3748-codex`. Zweiter Kanal: **1e25a555_codex / Codex Deployment 0.4.10-dev.1**, auto_update=false, kein Update in progress. Sein Running/Stopped-Zustand ist über die verfügbaren deaktivierten State-Entitäten nicht feststellbar; Update-state off ist kein Laufzeitzustand.

`/homeassistant/.ssh` ist weiterhin nicht vorhanden. Das bekannte aktuelle SSH-Verzeichnis `/data/codex-home/users/anonymous/.ssh` hat0700; die zwei privaten Schlüssel0600. Es wurden nur Eigentümer/Modus/ACL-Metadaten erfasst, keine Schlüsselinhalte. Alle zwölf erfassten Pfade haben vor/nach diesen Prüfungen identische Metadaten. Bestehende Default-/named group:root-ACLs am HA-Mount und bekannten Workspace-Pfaden bleiben unverändert. Keine Reparatur.

Kein produktives Add-on gestartet, gestoppt, aktualisiert oder neu gestartet; kein Image ersetzt, keine Produktionsoption geändert, keine HA-Konfigurationsdatei bearbeitet und kein Schreibzugriff auf /addons. Die Tests installieren oder starten kein Add-on. Kein Merge, Release oder CI-Fan-out; kein HA-Neustart/Reload aus diesem Lauf ausstehend.

## Build-/Supervisor-Vorbereitung und konkrete UI-Schritte

Manifest: **Codex SSH Hotfix Test**, `codex_issue26`, **0.4.28-test.26.1**, `boot: manual`, experimental, kein image-Key. Der Supervisor soll aus dem mitgelieferten `codex/Dockerfile` bauen. Statische Architekturprüfung für amd64/aarch64 ist plausibel; sie beweist weder Image-Verfügbarkeit noch Paketauflösung, Kompilierung oder Lauffähigkeit.

Ein bereits autorisierter Supervisor-Management-Client ist weiterhin nicht verfügbar: HA-MCP hat keine Store/Repository/Build/Install-Schnittstelle, ha-readonly nur Core-Diagnosen, anonymer Supervisor GET/addons liefert HTTP401. Keine Tokens oder sonstige Zugangsdaten ausgelesen und kein Host-/Docker-Bypass versucht. Das ist ein Ausführungsblocker für Codex, **kein rotes Source-Gate**.

**Nächster Schritt ist jetzt freigegeben:**

1. Home Assistant → **Einstellungen → Apps/Add-ons → App-/Add-on-Store → Menü → Repositories**.
2. Zusätzlich hinzufügen: **https://github.com/CaneTLOTW/ha-codex#issue26-local-test**. Vorhandene stabile und #deployment-Quellen weder bearbeiten noch entfernen. Bei Ersetzungs-/Konflikthinweis stoppen.
3. Store aktualisieren; ausschließlich **Codex SSH Hotfix Test**, Version **0.4.28-test.26.1**, aus genau diesem Testbranch öffnen. Tatsächlichen repositoryqualifizierten Supervisor-Slug prüfen/erfassen; er darf keine existierende Produktion/Deployment/Testinstallation überschreiben. Bei mehrdeutigem Eintrag oder bereits bestehender kollidierender Installation stoppen. Der UI muss kein Git-SHA abverlangt werden; Branch/Version plus die hier dokumentierten Git-/Source-Hashes dienen dem Nachweis.
4. Nur bei passendem Eintrag **Installieren**. Supervisor baut lokal. **Start beim Booten ausgeschaltet lassen**; getrennte eigene /data, keine produktiven Add-on-Daten kopieren. Bei Buildfehler/unpassendem Image stoppen und Originalfehler dokumentieren.
5. Danach ursprüngliches Runbook Phase4: Metadaten vor/nach zwei Starts, Logs, Scratch-YAML-Zugriff und MCP aus der tatsächlichen Testinstanz prüfen. Anschließend Testinstanz stoppen; Entfernen nur mit separater Zustimmung. Produktives Codex und Deployment unangetastet lassen.

Ein Build auf beiden Architekturen oder ein Release ist nicht Teil dieser Freigabe. Die lokale Supervisor-Testinstallation dient gerade dazu, das noch offene Build-/Runtime-Gate auf diesem amd64-System zu prüfen.

## Verbleibende Risiken

- Eigene /data isoliert den Add-on-Zustand; /homeassistant, /share und /media bleiben gemeinsam gemountet. Beim späteren Start sind gefilterte ACL-/chmod-Anpassungen an normalen vorhandenen Workspace-Dateien Teil des Helpers. Die Testinstanz ist keine vollständige Dateisystem-Sandbox.
- Vorhandene problematische Default-/named ACLs werden nicht automatisch entfernt und können weiter vererbt werden. Frühere Schäden bleiben opt-in-Reparaturthema.
- Benutzerdefiniert benannte Schlüssel außerhalb geschützter Verzeichnisse mit bereits permissiven Rechten können nicht vollständig erkannt werden.
- Neue Dateien anderer UIDs erhalten keine neuen Default-ACLs mehr; dadurch kann gewünschter Schreibzugriff fehlen.
- Broad group-root workspace access bleibt: Hotfix ist keine vollständige Privilegientrennung.
- Volle Supervisor-Kollisionsfreiheit, tatsächlicher Build, zwei reale Starts, SSH-Authentifizierung und Test-MCP sind erst im nächsten Schritt verifizierbar. Die Freigabe gilt nur nach der beschriebenen Store-Prüfung und ersetzt deren Ergebnis nicht.

Vorheriger roter Bericht bleibt unverändert als Historie erhalten. Dieser Bericht und die neue grüne Ausgabe sind die aktuelle Source-/Testinstallationsentscheidung.
