# Teleprompter

Eigenständige Desktop-App (Python, nur Standardbibliothek — `tkinter`) zum
Vorlesen von Skripten während einer Video-Aufnahme (z.B. mit OBS).

## Download

Für Windows, kein Python nötig — immer die neueste Version:

- **[Landingpage](https://skquievreux.github.io/teleprompter/)** mit beiden Optionen
- **[teleprompter-setup.exe](https://cdn.runitfast.xyz/softwaredistro/teleprompter-setup.exe)** — Installer mit Startmenü-Eintrag & Deinstallation über „Apps & Features"
- **[teleprompter.exe](https://cdn.runitfast.xyz/softwaredistro/teleprompter.exe)** — portabel, einfach ausführen

Oder per [Scoop](https://scoop.sh):

```powershell
scoop bucket add skquievreux https://github.com/skquievreux/scoop-bucket
scoop install skquievreux/teleprompter
```

> Bitte nur **einen** Weg gleichzeitig benutzen (Installer *oder* Scoop *oder*
> portabel) — sonst tauchen mehrere "Teleprompter"-Einträge in der
> Windows-Suche auf und du startest versehentlich eine alte Version.
> Update: Installer/`.exe` neu herunterladen und ausführen (schließt eine
> laufende alte Version automatisch); Scoop: `scoop update teleprompter`.
> Deinstallieren: über „Apps & Features" (Installer) bzw. `scoop uninstall
> teleprompter` (Scoop). Die App zeigt neue Versionen selbst an (Menü
> „Nach Updates suchen" bzw. ein grüner Hinweis, falls eine neue Version da ist).

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
| `.docx` | Word-Text wird extrahiert (Absätze → Zeilenumbrüche), Dateiname wird zum Titel. Klassisches `.doc` wird nicht unterstützt — vorher in Word als `.docx` speichern. |

## Start ohne Argumente

Ohne `--file`/`--folder`/`--url` öffnet die App immer sofort, ohne Dialog oder
Netzwerkzugriff: zuerst wird versucht, das zuletzt geladene Skript wieder zu
öffnen (`~/.teleprompter_settings.json`), sonst startet sie mit einem leeren
Platzhaltertext. Ein Skript danach jederzeit über das **Datei**-Menü laden.

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
