# -*- coding: utf-8 -*-
"""
SC BP Watcher — zeigt live an, sobald im SC Deutsch Launcher ein neuer
Bauplan (Blueprint) freigeschaltet wird.

Überwacht:  %APPDATA%\\sc-deutsch-launcher\\blueprints\\sc_bp_erledigt.json
Anzeige:    kleines, immer-im-Vordergrund Overlay-Fenster (verschiebbar).

Reines Python-Standardbibliothek-Tool (tkinter) — keine Zusatzpakete nötig.
Läuft unter Windows mit dem normalen Python.
"""
import os, json, time, threading, queue
import tkinter as tk
from tkinter import font as tkfont
try:
    import winsound
except ImportError:
    winsound = None

__version__ = '1.0.3'

# ---------------------------------------------------------------- Konfiguration
BP_DIR   = os.path.join(os.environ.get('APPDATA', ''), 'sc-deutsch-launcher', 'blueprints')
BP_FILE  = os.path.join(BP_DIR, 'sc_bp_erledigt.json')
TYPE_FILE = os.path.join(BP_DIR, 'bp_item_types.json')
POLL_SEC = 3            # wie oft die Datei geprüft wird (Sekunden)
MAX_ROWS = 200          # so viele Neuzugänge max. in der Liste behalten

# Farben (dunkles Overlay)
BG, FG, ACCENT, SUB, BAR = '#10141c', '#e6edf3', '#47aa42', '#8b98a5', '#1b2230'


# ---------------------------------------------------------------- Daten-Helfer
def load_keys():
    """Liest die freigeschalteten BP-Namen. Gibt set() zurück (leer bei Fehler)."""
    try:
        with open(BP_FILE, encoding='utf-8') as f:
            data = json.load(f)
        return {b['key'] for b in data.get('blueprints', [])}
    except Exception:
        return None   # None = Datei (gerade) nicht lesbar -> Tick überspringen


def load_types():
    try:
        with open(TYPE_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


TYPES = load_types()
def art_of(key):
    return TYPES.get(key.lower().replace('\xa0', ' ')) or '—'


# ---------------------------------------------------------------- Watcher-Thread
class Watcher(threading.Thread):
    def __init__(self, out_queue):
        super().__init__(daemon=True)
        self.q = out_queue
        self.known = None
        self.running = True

    def run(self):
        # Basisstand setzen (nicht alle vorhandenen BPs als "neu" melden)
        while self.known is None and self.running:
            self.known = load_keys()
            if self.known is None:
                time.sleep(POLL_SEC)
        self.q.put(('status', f'Überwache {len(self.known)} BPs …'))
        while self.running:
            time.sleep(POLL_SEC)
            cur = load_keys()
            if cur is None:
                continue
            new = cur - self.known
            if new:
                for k in sorted(new):
                    self.q.put(('new', k, art_of(k), time.strftime('%H:%M:%S')))
            gone = self.known - cur
            self.known = cur
            self.q.put(('status', f'Überwache {len(cur)} BPs … '
                                  f'(zuletzt geprüft {time.strftime("%H:%M:%S")})'))

    def stop(self):
        self.running = False


# ---------------------------------------------------------------- GUI / Overlay
class Overlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('SC BP Watcher')
        self.root.configure(bg=BG)
        self.root.overrideredirect(True)          # randloses Overlay
        self.root.attributes('-topmost', True)    # immer im Vordergrund
        self.root.attributes('-alpha', 0.93)      # leicht durchscheinend
        self.root.geometry('340x300+40+40')
        # Fenster-/Taskleisten-Icon setzen, falls icon.ico daneben liegt
        try:
            ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
            if os.path.exists(ico):
                self.root.iconbitmap(ico)
        except Exception:
            pass
        self.count = 0

        self.f_title = tkfont.Font(family='Segoe UI Semibold', size=10)
        self.f_item  = tkfont.Font(family='Consolas', size=9)
        self.f_sub   = tkfont.Font(family='Segoe UI', size=8)

        # --- Titelleiste (Drag-Griff + Schließen) ---
        bar = tk.Frame(self.root, bg=BAR, height=26)
        bar.pack(fill='x', side='top')
        bar.pack_propagate(False)
        tk.Label(bar, text=f'● SC BP Watcher v{__version__}', bg=BAR, fg=ACCENT,
                 font=self.f_title).pack(side='left', padx=8)
        tk.Label(bar, text='✕', bg=BAR, fg=SUB, font=self.f_title,
                 cursor='hand2').pack(side='right', padx=8)
        bar.winfo_children()[-1].bind('<Button-1>', lambda e: self.quit())
        tk.Label(bar, text='🗑', bg=BAR, fg=SUB, font=self.f_title,
                 cursor='hand2').pack(side='right')
        bar.winfo_children()[-1].bind('<Button-1>', lambda e: self.clear())
        for w in (bar, bar.winfo_children()[0]):
            w.bind('<Button-1>', self._drag_start)
            w.bind('<B1-Motion>', self._drag_move)

        # --- Statuszeile ---
        self.status = tk.Label(self.root, text='Starte …', bg=BG, fg=SUB,
                               font=self.f_sub, anchor='w')
        self.status.pack(fill='x', padx=8, pady=(4, 2))

        # --- Liste (scrollbar) ---
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill='both', expand=True, padx=6, pady=(0, 6))
        self.canvas = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(wrap, orient='vertical', command=self.canvas.yview)
        self.list = tk.Frame(self.canvas, bg=BG)
        self.list.bind('<Configure>',
                       lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.create_window((0, 0), window=self.list, anchor='nw', width=312)
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        self._placeholder()

        # Resize-Griff unten rechts
        grip = tk.Label(self.root, text='◢', bg=BG, fg=SUB, cursor='size_nw_se')
        grip.place(relx=1.0, rely=1.0, anchor='se')
        grip.bind('<B1-Motion>', self._resize)

        # Watcher starten
        self.q = queue.Queue()
        self.watcher = Watcher(self.q)
        self.watcher.start()
        self.root.after(200, self._poll_queue)

    # ---- Drag & Resize ----
    def _drag_start(self, e): self._dx, self._dy = e.x, e.y
    def _drag_move(self, e):
        self.root.geometry(f'+{self.root.winfo_x()+e.x-self._dx}+{self.root.winfo_y()+e.y-self._dy}')
    def _resize(self, e):
        w = max(260, self.root.winfo_pointerx() - self.root.winfo_x())
        h = max(160, self.root.winfo_pointery() - self.root.winfo_y())
        self.root.geometry(f'{w}x{h}')

    # ---- Liste ----
    def _placeholder(self):
        self._ph = tk.Label(self.list, text='Warte auf neue Baupläne …',
                            bg=BG, fg=SUB, font=self.f_sub)
        self._ph.pack(anchor='w', padx=4, pady=6)

    def clear(self):
        for w in self.list.winfo_children():
            w.destroy()
        self.count = 0
        self._placeholder()

    def add_new(self, key, art, ts):
        if self.count == 0 and hasattr(self, '_ph') and self._ph.winfo_exists():
            self._ph.destroy()
        self.count += 1
        row = tk.Frame(self.list, bg=BG)
        row.pack(fill='x', anchor='w', padx=2, pady=1)
        tk.Label(row, text='🟢', bg=BG, font=self.f_item).pack(side='left')
        txt = tk.Frame(row, bg=BG); txt.pack(side='left', fill='x', expand=True)
        tk.Label(txt, text=key, bg=BG, fg=FG, font=self.f_item,
                 anchor='w', justify='left').pack(fill='x', anchor='w')
        tk.Label(txt, text=f'{art} · {ts}', bg=BG, fg=SUB, font=self.f_sub,
                 anchor='w').pack(fill='x', anchor='w')
        # neueste oben einsortieren
        row.pack_configure(before=self.list.winfo_children()[0] if self.count > 1 else None)
        self.canvas.yview_moveto(0)
        if winsound:
            try: winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception: pass

    # ---- Queue vom Watcher abarbeiten ----
    def _poll_queue(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == 'status':
                    self.status.config(text=msg[1])
                elif msg[0] == 'new':
                    self.add_new(msg[1], msg[2], msg[3])
        except queue.Empty:
            pass
        self.root.after(300, self._poll_queue)

    def quit(self):
        self.watcher.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    if not os.path.exists(BP_FILE):
        # Minimaler Hinweis, falls der Launcher-Ordner fehlt
        r = tk.Tk(); r.title('SC BP Watcher')
        tk.Label(r, text='Datei nicht gefunden:\n' + BP_FILE +
                 '\n\nIst der SC Deutsch Launcher installiert?',
                 justify='left', padx=20, pady=20).pack()
        r.mainloop()
    else:
        Overlay().run()
