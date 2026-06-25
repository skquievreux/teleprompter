# Changelog

Ab hier gepflegt von [release-please](https://github.com/googleapis/release-please) —
neue Einträge werden automatisch aus Commit-Messages (Conventional Commits)
generiert, sobald ein Release-PR gemerged wird.

## [1.5.0](https://github.com/skquievreux/teleprompter/compare/v1.4.1...v1.5.0) (2026-06-25)


### Features

* auto-update Scoop manifest from the release workflow ([02acad9](https://github.com/skquievreux/teleprompter/commit/02acad99b39517b3dd36cba6f5b5e4b93fa9e444))
* introduce semantic releases via release-please, professional README ([1f466ed](https://github.com/skquievreux/teleprompter/commit/1f466edd8b9a24e7a5846c2b69c02e29dadd76c5))

## [1.4.1] - 2026-06-25

- fix: Fenster-/Taskbar-Icon wurde nie gesetzt (nur das Datei-Icon der `.exe`)
- fix: `VERSION`-Konstante lief manuell gepflegt aus dem Tag — jetzt von CI synchronisiert
- fix: Update-Hinweis öffnet die Downloadseite statt der GitHub-Releases-Seite

## [1.4.0] - 2026-06-25

- fix: Installer schließt eine laufende Instanz automatisch (`CloseApplications=force`) —
  vorher blockierte ein offenes Fenster Update/Uninstall unbemerkt
- feat: In-App-Update-Check (Hintergrund-Thread, Menüpunkt „Nach Updates suchen")

## [1.3.0] - 2026-06-25

- feat: App-Icon (generiert, Mikrofon-Design) — Exe, Tray, Installer, Landingpage-Favicon

## [1.2.0] - 2026-06-24

- feat: Start ohne Nachfrage/Dialog (kein MotionDesk-API-Zwang mehr), Fallback auf zuletzt
  genutztes Skript statt blockierendem Datei-Dialog
- feat: `.docx`-Import (stdlib `zipfile`+`xml`, keine neue Abhängigkeit)
- feat: professioneller Windows-Installer (Inno Setup, Startmenü-Eintrag, Uninstaller)

## [1.1.0] - 2026-06-24

- Initiales Release als eigenständiges Open-Source-Projekt (vorher Teil eines Monorepos)
- GitHub-Actions-Pipeline: PyInstaller-Build → GitHub Release → Cloudflare-R2-CDN-Upload
