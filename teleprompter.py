#!/usr/bin/env python3
"""Standalone teleprompter — reads a script (JSON: {title, text}, plain
.txt/.md/.docx, or a remote API) and scrolls it for reading on camera."""
import argparse
import json
import re
import sys
import threading
import tkinter as tk
import webbrowser
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

# Works both from source and from a PyInstaller --onefile build (assets are
# extracted to a temp dir at runtime, exposed via sys._MEIPASS).
ASSETS_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets"

try:
    import pystray
    from PIL import Image
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

HELP_TEXT = """Bedienung

Datei-Menü → Datei öffnen / Ordner öffnen: Skript laden (.json, .txt, .md)
Leertaste oder Klick auf den Text: Start/Pause (mit 3-2-1 Countdown)
↑ / ↓: Vorlese-Tempo ändern
← / →: Breite (Rand links/rechts) ändern
F11: Vollbild  ·  Esc: Vollbild verlassen
⟲ Reset: zurück zum Anfang

Die Regler unten (Größe, Tempo, Theme) wirken sofort. Die Leiste bleibt
immer sichtbar, auch im Vollbild oder bei maximiertem Fenster.
Menü "Einstellungen" bzw. Button "⚙ Mehr...": Rand (oben/unten/links/rechts)
und Text-Ausrichtung (links/zentriert/rechts).
Anzeige rechts unten: Zeit · Fortschritt in % vom Gesamttext.
Beim Lesen werden automatisch je 3 Wörter hervorgehoben, passend zum Tempo.
Aktuell geladene Datei: siehe Titelleiste und Anzeige links unten.

Einstellungen werden beim Schließen automatisch gespeichert
und beim nächsten Start wieder geladen.

Schließen-Button (X) minimiert ins System-Tray (falls verfügbar) statt
die App zu beenden. Rechtsklick auf das Tray-Icon: Start/Pause,
Einstellungen, Fenster zeigen, Beenden."""

VERSION = "1.3.0"
SETTINGS_PATH = Path.home() / ".teleprompter_settings.json"
SUPPORTED_EXTENSIONS = {".json", ".txt", ".md", ".docx"}
DEFAULT_SCRIPT = {
    "title": "Kein Skript geladen",
    "text": "Öffne über Datei → Datei öffnen / Ordner öffnen ein Skript (.json, .txt, .md, .docx).",
}

GITHUB_REPO = "skquievreux/teleprompter"
LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"


def fetch_latest_version(timeout: float = 4) -> str | None:
    """Returns the latest released version tag (without 'v'), or None on any failure."""
    req = Request(LATEST_RELEASE_API, headers={"Accept": "application/vnd.github+json"})
    try:
        with urlopen(req, timeout=timeout) as res:
            data = json.loads(res.read().decode("utf-8"))
        return data.get("tag_name", "").lstrip("v") or None
    except (URLError, OSError, ValueError):
        return None


def is_newer_version(latest: str, current: str) -> bool:
    parts = lambda v: tuple(int(n) for n in v.split(".") if n.isdigit())
    return parts(latest) > parts(current)

THEMES = {
    "Weiß auf Schwarz": ("white", "black"),
    "Schwarz auf Weiß": ("black", "white"),
    "Grün auf Schwarz": ("#00ff66", "black"),
}

ALIGNMENTS = {"Links": "left", "Zentriert": "center", "Rechts": "right"}


def parse_script(raw: str) -> dict:
    data = json.loads(raw)
    if "text" not in data:
        raise ValueError("Script JSON braucht ein 'text' Feld")
    return {"title": data.get("title", "Untitled"), "text": data["text"]}


def docx_to_text(path: str) -> str:
    """Extracts plain text from a .docx (paragraphs joined by blank lines).
    Uses only the stdlib — .docx is just a zip of XML, no python-docx needed."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        xml = zf.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for p in root.iter(f"{{{ns['w']}}}p"):
        text = "".join(t.text or "" for t in p.iter(f"{{{ns['w']}}}t"))
        paragraphs.append(text)
    return "\n\n".join(paragraphs)


def load_script_from_path(path: str) -> dict:
    """Loads a script from disk — .json uses {title, text}, .txt/.md/.docx are read as plain text."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".json":
        return parse_script(p.read_text(encoding="utf-8"))
    if suffix == ".docx":
        return {"title": p.stem, "text": docx_to_text(path)}
    if suffix in SUPPORTED_EXTENSIONS:
        return {"title": p.stem, "text": p.read_text(encoding="utf-8")}
    raise ValueError(f"Nicht unterstütztes Format: {p.suffix}")


def latest_in_folder(folder: str) -> str | None:
    files = [p for p in Path(folder).iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not files:
        return None
    return str(max(files, key=lambda p: p.stat().st_mtime))


def load_script(file: str | None, folder: str | None, url: str | None) -> tuple[dict, str | None]:
    """Resolves the startup script. Returns (script, path) — path is the local
    file actually used (for remembering it as 'last script'), or None for URL/none."""
    if folder:
        latest = latest_in_folder(folder)
        if not latest:
            raise ValueError(f"Kein unterstütztes Skript (.json/.txt/.md/.docx) in {folder}")
        script = load_script_from_path(latest)
        script["source"] = Path(latest).name
        return script, latest
    if file:
        script = load_script_from_path(file)
        script["source"] = Path(file).name
        return script, file
    if url:
        with urlopen(url, timeout=5) as res:
            script = parse_script(res.read().decode("utf-8"))
            script["source"] = "API"
            return script, None
    settings = load_settings()
    last_path = settings.get("last_path")
    if last_path and Path(last_path).exists():
        script = load_script_from_path(last_path)
        script["source"] = Path(last_path).name
        return script, last_path
    return DEFAULT_SCRIPT.copy(), None


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings), encoding="utf-8")


def compute_step(speed_lines_per_sec: float, interval_ms: int) -> float:
    """Lines to scroll per tick — pure function, kept separate from Tk for testing."""
    return speed_lines_per_sec * interval_ms / 1000


def format_time(total_seconds: float) -> str:
    total_seconds = int(total_seconds)
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


GROUP_SIZE = 3
AVG_WORDS_PER_LINE = 9  # rough heuristic to derive a words/sec pace from the line-scroll speed


def build_word_groups(text: str, group_size: int = GROUP_SIZE) -> list[tuple[int, int]]:
    """Character (start, end) offsets for consecutive groups of N words — pure, testable."""
    words = list(re.finditer(r"\S+", text))
    return [
        (words[i].start(), words[min(i + group_size, len(words)) - 1].end())
        for i in range(0, len(words), group_size)
    ]


def group_interval_ms(speed_lines_per_sec: float, group_size: int = GROUP_SIZE) -> float:
    """How long (ms) a word group should stay highlighted — fallback heuristic
    used before real pixel/word measurements are available."""
    words_per_sec = max(0.1, speed_lines_per_sec * AVG_WORDS_PER_LINE)
    return 1000 * group_size / words_per_sec


START_GRACE_MS = 3000  # first line holds still this long after countdown before scrolling starts


class TeleprompterApp:
    TICK_MS = 50

    def __init__(self, root: tk.Tk, script: dict, path: str | None = None):
        self.root = root
        self.last_path = path
        self.root.title(f"Teleprompter v{VERSION} — {script['title']} ({script.get('source', '—')})")
        self.root.geometry("900x700")
        self.root.minsize(700, 450)

        settings = load_settings()
        self.font_size = tk.IntVar(value=settings.get("font_size", 40))
        self.speed = tk.DoubleVar(value=settings.get("speed", 2))
        self.margin_top = tk.IntVar(value=settings.get("margin_top", 20))
        self.margin_bottom = tk.IntVar(value=settings.get("margin_bottom", 20))
        self.margin_left = tk.IntVar(value=settings.get("margin_left", 40))
        self.margin_right = tk.IntVar(value=settings.get("margin_right", 40))
        self.align = tk.StringVar(value=settings.get("align", "Links"))
        self.theme = tk.StringVar(value=settings.get("theme", "Weiß auf Schwarz"))
        self.running = False
        self._scroll_px_acc = 0.0
        self.elapsed_sec = 0.0
        self.source = script.get("source", "—")
        self.word_groups = build_word_groups(script["text"])
        self.word_group_idx = 0
        self.total_words = len(re.findall(r"\S+", script["text"]))

        # Grid (not pack) for the top-level layout: rows keep fixed height regardless
        # of window resize/maximize/fullscreen, so the toolbar can never get squeezed out.
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)

        self.text = tk.Text(
            root, wrap="word", bd=0, highlightthickness=0,
            font=("Helvetica", self.font_size.get()), cursor="arrow",
        )
        self.text.insert("1.0", script["text"])
        self.text.configure(state="disabled")
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.tag_configure("highlight", background="#facc15", foreground="black")
        self.text.bind("<Button-1>", lambda _e: self.toggle())
        self._apply_margins()
        self._apply_alignment()

        self._build_menu()

        # Any change to these (toolbar OR settings dialog) updates the view immediately
        self.font_size.trace_add("write", lambda *_: self._on_font_change(""))
        for var in (self.margin_top, self.margin_bottom, self.margin_left, self.margin_right):
            var.trace_add("write", lambda *_: self._apply_margins())
        self.align.trace_add("write", lambda *_: self._apply_alignment())
        self.theme.trace_add("write", lambda *_: self._on_theme_change(self.theme.get()))

        # Countdown overlay, shown on top of the text before scrolling starts
        self.countdown_label = tk.Label(root, font=("Helvetica", 120, "bold"), fg="#7c3aed", bg="black")

        # Progress bar — fixed row, always visible
        self.progress_canvas = tk.Canvas(root, height=4, bg="gray20", highlightthickness=0)
        self.progress_canvas.grid(row=1, column=0, sticky="ew")
        self.progress_bar = self.progress_canvas.create_rectangle(0, 0, 0, 4, fill="#7c3aed", width=0)

        controls = tk.Frame(root, bg="black")
        controls.grid(row=2, column=0, sticky="ew", pady=8)

        self.source_label = tk.Label(controls, text=f"📄 {self.source}", fg="#a78bfa", bg="black")
        self.source_label.pack(side="left", padx=(8, 16))

        tk.Label(controls, text="Größe", fg="white", bg="black").pack(side="left", padx=4)
        tk.Scale(controls, from_=20, to=120, orient="horizontal", variable=self.font_size,
                 bg="black", fg="white", troughcolor="gray20", highlightthickness=0).pack(side="left")

        tk.Label(controls, text="Tempo", fg="white", bg="black").pack(side="left", padx=12)
        tk.Scale(controls, from_=0.2, to=10, resolution=0.2, orient="horizontal", variable=self.speed,
                 bg="black", fg="white", troughcolor="gray20", highlightthickness=0).pack(side="left")

        tk.OptionMenu(controls, self.theme, *THEMES).pack(side="left", padx=12)

        self.play_btn = tk.Button(controls, text="▶ Start", command=self.toggle)
        self.play_btn.pack(side="left", padx=12)
        tk.Button(controls, text="⟲ Reset", command=self.reset).pack(side="left")
        tk.Button(controls, text="⚙ Mehr...", command=self.open_settings_dialog).pack(side="left", padx=8)

        self.timer_label = tk.Label(controls, text="00:00 · 0%", fg="white", bg="black", font=("Helvetica", 14, "bold"))
        self.timer_label.pack(side="right", padx=16)

        self.update_label = tk.Label(controls, fg="#2ecc71", bg="black", cursor="hand2")
        self.update_label.bind("<Button-1>", lambda _e: webbrowser.open(RELEASES_PAGE))
        threading.Thread(target=self._check_for_update, daemon=True).start()

        root.bind("<space>", lambda _e: self.toggle())
        root.bind("<Up>", lambda _e: self.speed.set(round(min(10, self.speed.get() + 0.2), 1)))
        root.bind("<Down>", lambda _e: self.speed.set(round(max(0.2, self.speed.get() - 0.2), 1)))
        root.bind("<Right>", lambda _e: self._bump_width(-10))
        root.bind("<Left>", lambda _e: self._bump_width(10))
        root.bind("<F11>", lambda _e: root.attributes("-fullscreen", not root.attributes("-fullscreen")))
        root.bind("<Escape>", lambda _e: root.attributes("-fullscreen", False))
        root.bind("<Shift-MouseWheel>", self._on_shift_wheel)

        self._on_theme_change(self.theme.get())
        self._update_progress()

        self.tray_icon = None
        if TRAY_AVAILABLE:
            self._start_tray()
        else:
            print("Hinweis: System-Tray nicht verfügbar. Installieren mit: pip install pystray pillow")

        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Datei öffnen...", command=self.open_file_dialog)
        file_menu.add_command(label="Ordner öffnen (neuestes Skript)...", command=self.open_folder_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Beenden", command=self._quit)
        menubar.add_cascade(label="Datei", menu=file_menu)

        menubar.add_command(label="Einstellungen", command=self.open_settings_dialog)
        menubar.add_command(label="Nach Updates suchen", command=self.check_for_update_manual)
        menubar.add_command(label="Hilfe", command=self.show_help)
        self.root.config(menu=menubar)

    def open_settings_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Einstellungen")
        dialog.configure(bg="black")
        dialog.transient(self.root)

        def slider(label: str, var: tk.IntVar, lo: int, hi: int) -> None:
            row = tk.Frame(dialog, bg="black")
            row.pack(fill="x", padx=16, pady=6)
            tk.Label(row, text=label, fg="white", bg="black", width=14, anchor="w").pack(side="left")
            tk.Scale(row, from_=lo, to=hi, orient="horizontal", variable=var,
                     bg="black", fg="white", troughcolor="gray20", highlightthickness=0).pack(side="left", fill="x", expand=True)

        tk.Label(dialog, text="Rand (px)", fg="#a78bfa", bg="black", font=("Helvetica", 11, "bold")).pack(pady=(14, 0))
        slider("Oben", self.margin_top, 0, 300)
        slider("Unten", self.margin_bottom, 0, 300)
        slider("Links", self.margin_left, 0, 300)
        slider("Rechts", self.margin_right, 0, 300)

        align_row = tk.Frame(dialog, bg="black")
        align_row.pack(fill="x", padx=16, pady=(16, 14))
        tk.Label(align_row, text="Ausrichtung", fg="white", bg="black", width=14, anchor="w").pack(side="left")
        tk.OptionMenu(align_row, self.align, *ALIGNMENTS).pack(side="left")

    def open_file_dialog(self) -> None:
        path = filedialog.askopenfilename(
            title="Skript öffnen",
            filetypes=[("Teleprompter-Skripte", "*.json *.txt *.md *.docx"), ("Alle Dateien", "*.*")],
        )
        if not path:
            return
        try:
            script = load_script_from_path(path)
            script["source"] = Path(path).name
            self.load_new_script(script, path)
        except (OSError, ValueError) as e:
            messagebox.showerror("Fehler", f"Konnte Skript nicht laden: {e}")

    def open_folder_dialog(self) -> None:
        folder = filedialog.askdirectory(title="Ordner mit Skripten wählen")
        if not folder:
            return
        latest = latest_in_folder(folder)
        if not latest:
            messagebox.showwarning("Kein Skript gefunden", "Keine .json/.txt/.md/.docx Datei in diesem Ordner.")
            return
        script = load_script_from_path(latest)
        script["source"] = Path(latest).name
        self.load_new_script(script, latest)

    def load_new_script(self, script: dict, path: str | None = None) -> None:
        self.last_path = path
        self._save_settings_now()
        self.reset()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", script["text"])
        self.text.configure(state="disabled")
        self._apply_alignment()
        self.word_groups = build_word_groups(script["text"])
        self.word_group_idx = 0
        self.total_words = len(re.findall(r"\S+", script["text"]))
        self.source = script.get("source", "—")
        self.source_label.configure(text=f"📄 {self.source}")
        self.root.title(f"Teleprompter v{VERSION} — {script['title']} ({self.source})")

    def show_help(self) -> None:
        messagebox.showinfo(f"Teleprompter v{VERSION} — Hilfe", HELP_TEXT)

    def _check_for_update(self) -> None:
        """Runs in a background thread — never blocks startup, fails silently."""
        latest = fetch_latest_version()
        if latest and is_newer_version(latest, VERSION):
            self.root.after(0, self._show_update_available, latest)

    def _show_update_available(self, latest: str) -> None:
        self.update_label.configure(text=f"⬆ Update verfügbar: v{latest}")
        self.update_label.pack(side="right", padx=16)

    def check_for_update_manual(self) -> None:
        latest = fetch_latest_version()
        if latest is None:
            messagebox.showwarning("Update-Check", "Konnte nicht prüfen (keine Verbindung?).")
        elif is_newer_version(latest, VERSION):
            if messagebox.askyesno("Update verfügbar", f"v{latest} ist verfügbar (du hast v{VERSION}).\nRelease-Seite öffnen?"):
                webbrowser.open(RELEASES_PAGE)
        else:
            messagebox.showinfo("Update-Check", f"Du hast bereits die neueste Version (v{VERSION}).")

    def _start_tray(self) -> None:
        icon_path = ASSETS_DIR / "icon.png"
        image = Image.open(icon_path) if icon_path.exists() else Image.new("RGB", (64, 64), "#7c3aed")
        menu = pystray.Menu(
            pystray.MenuItem("Fenster zeigen", lambda: self.root.after(0, self._show_window), default=True),
            pystray.MenuItem("Start/Pause", lambda: self.root.after(0, self.toggle)),
            pystray.MenuItem("Einstellungen...", lambda: self.root.after(0, self.open_settings_dialog)),
            pystray.MenuItem("Beenden", lambda: self.root.after(0, self._quit)),
        )
        self.tray_icon = pystray.Icon("teleprompter", image, f"Teleprompter v{VERSION}", menu)
        self.tray_icon.run_detached()

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _save_settings_now(self) -> None:
        save_settings({
            "font_size": self.font_size.get(),
            "speed": self.speed.get(),
            "margin_top": self.margin_top.get(),
            "margin_bottom": self.margin_bottom.get(),
            "margin_left": self.margin_left.get(),
            "margin_right": self.margin_right.get(),
            "align": self.align.get(),
            "theme": self.theme.get(),
            "last_path": self.last_path,
        })

    def _on_close(self) -> None:
        """X button: minimize to tray if available, otherwise quit for real."""
        self._save_settings_now()
        if self.tray_icon:
            self.root.withdraw()
        else:
            self.root.destroy()

    def _quit(self) -> None:
        self._save_settings_now()
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()

    def _on_font_change(self, _value: str) -> None:
        self.text.configure(font=("Helvetica", self.font_size.get()))

    def _bump_width(self, step: int) -> None:
        """← schmälert, → verbreitert den Text — verändert links/rechts Rand gleichzeitig."""
        self.margin_left.set(max(0, min(300, self.margin_left.get() + step)))
        self.margin_right.set(max(0, min(300, self.margin_right.get() + step)))

    def _on_shift_wheel(self, event) -> None:
        """Shift+Mausrad/Drehrad: linker und rechter Rand wachsen/schrumpfen gleichzeitig."""
        step = 5 if event.delta > 0 else -5
        self.margin_left.set(max(0, min(300, self.margin_left.get() + step)))
        self.margin_right.set(max(0, min(300, self.margin_right.get() + step)))

    def _apply_margins(self) -> None:
        self.text.grid_configure(
            padx=(self.margin_left.get(), self.margin_right.get()),
            pady=(self.margin_top.get(), self.margin_bottom.get()),
        )

    def _apply_alignment(self) -> None:
        self.text.tag_configure("align", justify=ALIGNMENTS[self.align.get()])
        self.text.tag_add("align", "1.0", "end")

    def _on_theme_change(self, choice: str) -> None:
        fg, bg = THEMES[choice]
        self.root.configure(bg=bg)
        self.text.configure(bg=bg, fg=fg, insertbackground=bg)
        self.countdown_label.configure(bg=bg)

    def toggle(self) -> None:
        if self.running:
            self.running = False
            self.play_btn.configure(text="▶ Start")
        else:
            _, bottom = self.text.yview()
            if bottom >= 1.0:
                self.reset()
            self._countdown(3)

    def _countdown(self, n: int) -> None:
        if n == 0:
            self.countdown_label.place_forget()
            self.running = True
            self.play_btn.configure(text="⏸ Pause")
            # Erste Zeile bleibt nach dem Countdown noch START_GRACE_MS stehen,
            # damit das Auge ankommen kann, bevor es zu scrollen beginnt.
            self.root.after(START_GRACE_MS, self._tick)
            self.root.after(START_GRACE_MS, self._highlight_tick)
            return
        self.countdown_label.configure(text=str(n))
        self.countdown_label.place(relx=0.5, rely=0.5, anchor="center")
        self.countdown_label.lift()
        self.root.after(600, lambda: self._countdown(n - 1))

    def reset(self) -> None:
        self.running = False
        self.elapsed_sec = 0.0
        self.word_group_idx = 0
        self._scroll_px_acc = 0.0
        self.play_btn.configure(text="▶ Start")
        self.text.yview_moveto(0)
        self.text.tag_remove("highlight", "1.0", "end")
        self._update_progress()

    def _highlight_interval_ms(self) -> float:
        """Highlight pace derived from the *actual* scroll speed (px/sec) and the
        real word density of this script, so it tracks self.speed.get() exactly —
        not the AVG_WORDS_PER_LINE guess group_interval_ms() falls back to."""
        dlineinfo = self.text.dlineinfo("1.0")
        line_height = dlineinfo[3] if dlineinfo else self.font_size.get() * 1.4
        total_px = self.text.count("1.0", "end", "ypixels")[0]
        if total_px <= 0 or self.total_words <= 0:
            return group_interval_ms(self.speed.get())
        px_per_sec = self.speed.get() * line_height
        words_per_sec = max(0.1, px_per_sec * self.total_words / total_px)
        return 1000 * GROUP_SIZE / words_per_sec

    def _highlight_tick(self) -> None:
        if not self.running:
            return
        if self.word_group_idx < len(self.word_groups):
            start, end = self.word_groups[self.word_group_idx]
            self.text.tag_remove("highlight", "1.0", "end")
            self.text.tag_add("highlight", f"1.0+{start}c", f"1.0+{end}c")
            self.word_group_idx += 1
        self.root.after(int(self._highlight_interval_ms()), self._highlight_tick)

    def _tick(self) -> None:
        if not self.running:
            return
        # Pixel-genaues Scrollen statt ganzer Zeilen-Sprünge — vermeidet die
        # ruckartigen Sakkaden, die beim zeilenweisen yview_scroll auftreten.
        dlineinfo = self.text.dlineinfo("1.0")
        line_height = dlineinfo[3] if dlineinfo else self.font_size.get() * 1.4
        self._scroll_px_acc += self.speed.get() * self.TICK_MS / 1000 * line_height

        total_px = self.text.count("1.0", "end", "ypixels")[0]
        max_scroll_px = max(total_px - self.text.winfo_height(), 1)
        fraction = min(self._scroll_px_acc / max_scroll_px, 1.0)
        self.text.yview_moveto(fraction)

        self.elapsed_sec += self.TICK_MS / 1000
        self._update_progress()

        if fraction >= 1.0:
            self.running = False
            self.play_btn.configure(text="▶ Start")
            return

        self.root.after(self.TICK_MS, self._tick)

    def _update_progress(self) -> None:
        _, bottom = self.text.yview()
        width = self.progress_canvas.winfo_width() or self.root.winfo_width()
        self.progress_canvas.coords(self.progress_bar, 0, 0, width * bottom, 4)
        self.timer_label.configure(text=f"{format_time(self.elapsed_sec)} · {round(bottom * 100)}%")


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Standalone teleprompter v{VERSION}")
    parser.add_argument("--file", help="Pfad zu einer Script-Datei (.json, .txt, .md, .docx)")
    parser.add_argument("--folder", help="Ordner — lädt die zuletzt geänderte Skript-Datei darin")
    parser.add_argument("--url", help="API-URL, die Script-JSON liefert (optional, kein Default)")
    args = parser.parse_args()

    # Never blocks on a dialog at startup: falls back to the last-used script,
    # then to an empty placeholder, instead of asking the user anything.
    try:
        script, path = load_script(args.file, args.folder, args.url)
    except (OSError, URLError, json.JSONDecodeError, ValueError) as e:
        print(f"Konnte Skript nicht laden ({e}) — starte mit leerem Teleprompter.")
        script, path = DEFAULT_SCRIPT.copy(), None

    root = tk.Tk()
    TeleprompterApp(root, script, path)
    root.mainloop()


if __name__ == "__main__":
    main()
