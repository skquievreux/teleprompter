# Teleprompter

Eigenständige Desktop-App (Python, nur Standardbibliothek — `tkinter`) zum
Vorlesen von Skripten während einer Video-Aufnahme (z.B. mit OBS).

## Download

Fertige `.exe` für Windows: **[Landingpage](https://skquievreux.github.io/teleprompter/)**
oder direkt **[teleprompter.exe](https://cdn.runitfast.xyz/softwaredistro/teleprompter.exe)**
(immer die neueste Version, kein Python nötig).

## Start (aus dem Source)

**Windows, am einfachsten:** Doppelklick auf `start.bat` (oder im Terminal:
`start.bat`). Legt beim ersten Mal automatisch eine eigene virtuelle Umgebung
(`.venv`) an, installiert `requirements.txt` darin und startet die App — ohne
dass irgendwas systemweit installiert wird. Argumente werden durchgereicht:

```bash
start.bat --file pfad/zur/datei.json
start.bat --folder pfad/zum/ordner
```

**Manuell (jedes Betriebssystem):**

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt      # Windows
.venv/bin/pip install -r requirements.txt          # macOS/Linux

.venv\Scripts\python teleprompter.py               # Windows
.venv/bin/python teleprompter.py                   # macOS/Linux
```

Ohne `pystray`/`Pillow` läuft die App ganz normal weiter, nur ohne Tray-Icon
(Schließen-Button beendet dann wie gewohnt die App).

Datei/Ordner lassen sich auch nachträglich über das **Datei**-Menü in der App wählen.

## Unterstützte Formate

| Format | Inhalt |
|--------|--------|
| `.json` | `{"title": "...", "text": "..."}` |
| `.txt` / `.md` | reiner Text, Dateiname (ohne Endung) wird zum Titel |

## Features

- **3-2-1-Countdown** vor jedem Start
- **Auto-Scroll** mit stufenlos einstellbarem Tempo
- **Aufnahme-Timer** (mm:ss) + **Fortschritt in %** vom Gesamttext, rechts unten
- **Fortschrittsbalken** am unteren Fensterrand
- **Auto-Stop** am Textende
- **Schriftgröße** stufenlos regelbar
- **Rand** einzeln für oben/unten/links/rechts einstellbar (Menü „Einstellungen" bzw. „⚙ Mehr...")
- **Text-Ausrichtung**: links / zentriert / rechts
- **Farbthemen**: Weiß auf Schwarz, Schwarz auf Weiß, Grün auf Schwarz (Chroma-Key-taugliche Kontraste)
- **Datei-Dialog**: Skript per Menü öffnen (Datei oder Ordner), kein Neustart nötig
- **Hilfe-Menü**: Übersicht aller Funktionen und Tastenkürzel direkt in der App
- **Einstellungen werden gespeichert** (`~/.teleprompter_settings.json`) und beim nächsten Start automatisch wieder geladen
- **Versionsnummer** in der Titelleiste

## Tastenkürzel

| Taste | Aktion |
|-------|--------|
| Leertaste / Klick auf Text | Start / Pause |
| ↑ / ↓ | Tempo erhöhen / verringern |
| ← / → | Schrift verkleinern / vergrößern |
| F11 | Vollbild an/aus |
| Esc | Vollbild verlassen |

## Tests

Reine Logik (Parsing, Scroll-Berechnung, Zeitformat) ist von der GUI getrennt
und per `assert` getestet, ohne Test-Framework:

```bash
python test_teleprompter.py
```

## Bekannte Grenzen

- Kein Spiegel-Modus (horizontaler Flip für Beamsplitter-Glas-Rigs) — `tkinter.Text`
  unterstützt das nicht nativ, würde eine Canvas-basierte Neuimplementierung erfordern.
- Kein Datei-Upload/Dropzone direkt im Fenster — Datei-Auswahl läuft über den
  nativen Dateidialog im Menü.
