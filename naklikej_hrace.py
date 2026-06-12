import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
from collections import Counter
from tkinter import messagebox, ttk

IS_WINDOWS = sys.platform == "win32"

API_BASE = "https://api.chess.cz/api"


def resource_path(name):
    """Cesta k přibalenému souboru — funguje i v PyInstaller onefile exe."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)

# Cache odpovědí API, ať se při opakovaném "Načíst" nedotazujeme znovu
# (api.chess.cz agresivně blokuje IP při rychlých sekvenčních requestech).
_member_cache = {}


def fetch_member(id_type, id_val):
    """Načte detail hráče z api.chess.cz podle LOK/FIDE ID. Vrací dict nebo None."""
    key = (id_type, id_val)
    if key in _member_cache:
        return _member_cache[key]

    suffix = "cze" if id_type == "LOK" else "fide"
    url = f"{API_BASE}/members/{id_val}/{suffix}"
    req = urllib.request.Request(url, headers={"User-Agent": "smauto/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if isinstance(data, list):
        data = data[0] if data else None
    _member_cache[key] = data
    return data


# Název procesu Swiss-Manageru nalezený při prvním hledání — díky cache
# je každá další aktivace okamžitá (jediné rychlé osascript volání).
_swiss_proc_name = None


def _activate_mac_process(proc_name):
    quoted = proc_name.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'tell application "System Events" '
        f'to set frontmost of process "{quoted}" to true'
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True)
    return result.returncode == 0


def activate_swiss_window():
    """Zkusí aktivovat okno aplikace Swiss-Manager. Vrací True při úspěchu."""
    global _swiss_proc_name

    if IS_WINDOWS:
        ps = (
            "$w = New-Object -ComObject WScript.Shell; "
            "if ($w.AppActivate('Swiss')) { 'OK' } else { 'NOT_FOUND' }"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.stdout.strip() == "OK"

    if _swiss_proc_name and _activate_mac_process(_swiss_proc_name):
        return True
    _swiss_proc_name = None
    name = _resolve_swiss_proc_name()
    return bool(name and _activate_mac_process(name))


def _resolve_swiss_proc_name():
    """Najde název procesu Swiss-Manageru (trvá pár sekund, proto se cachuje).

    Pod CrossOverem se proces jmenuje "Menu Helper", proto se kromě názvů
    prochází i cesty k aplikacím; match se dělá v Pythonu (case-insensitive).
    """
    global _swiss_proc_name
    list_script = (
        'tell application "System Events"\n'
        '  set out to ""\n'
        "  repeat with p in (every application process)\n"
        '    set pp to ""\n'
        "    try\n"
        "      set pp to POSIX path of application file of p\n"
        "    end try\n"
        "    set out to out & (name of p) & tab & pp & linefeed\n"
        "  end repeat\n"
        "  return out\n"
        "end tell"
    )
    result = subprocess.run(
        ["osascript", "-e", list_script], capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        name, _, path = line.partition("\t")
        if "swiss" in name.lower() or "swiss" in path.lower():
            _swiss_proc_name = name
            return name
    return None


def paste_and_confirm(text):
    """Zkopíruje text do schránky a v aktivní aplikaci provede Vložit + 2× Enter.

    macOS: pbcopy + osascript (System Events), Windows: PowerShell
    (Set-Clipboard + SendKeys). Bez externích závislostí.
    """
    if IS_WINDOWS:
        ps = (
            f"Set-Clipboard -Value '{text}'; "
            "$w = New-Object -ComObject WScript.Shell; "
            "Start-Sleep -Milliseconds 150; "
            '$w.SendKeys("%q"); '
            "Start-Sleep -Milliseconds 300; "
            '$w.SendKeys("^v"); '
            "Start-Sleep -Milliseconds 300; "
            '$w.SendKeys("{ENTER}"); '
            "Start-Sleep -Milliseconds 900; "
            '$w.SendKeys("{ENTER}")'
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            check=False,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        time.sleep(0.15)
        script = (
            'tell application "System Events"\n'
            '  keystroke "q" using command down\n'
            "  delay 0.3\n"
            '  keystroke "v" using command down\n'
            "  delay 0.3\n"
            "  keystroke return\n"
            "  delay 0.9\n"
            "  keystroke return\n"
            "end tell"
        )
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)


class SwissManagerAutomator:
    def __init__(self, root):
        self.root = root
        self.root.title("Swiss-Manager Automation Tool")
        # Výška stačí na 20 hráčů bez posuvníku
        self.root.geometry("880x640")
        self.root.minsize(700, 500)

        try:
            self._icon = tk.PhotoImage(file=resource_path("icon.png"))
            self.root.iconphoto(True, self._icon)
        except tk.TclError:
            pass  # ikona je volitelná, bez ní aplikace běží dál

        # Stavové proměnné
        self.running = False
        self.current_index = 0
        self.parsed_rows = []
        self.load_generation = 0  # zneplatňuje běžící lazy-load po novém "Načíst"

        self.setup_ui()

        # Hledání procesu Swiss-Manageru trvá pár sekund — předehřát cache,
        # ať je aktivace okna při STARTu okamžitá
        if not IS_WINDOWS:
            threading.Thread(target=_resolve_swiss_proc_name, daemon=True).start()

        self.root.after(100, self.show_help)

    # ------------------------------------------------------------------ UI

    def setup_ui(self):
        # --- TOP PANEL: Globální nastavení ---
        top_frame = ttk.LabelFrame(self.root, text=" Globální nastavení ", padding=5)
        top_frame.pack(fill="x", padx=5, pady=2)

        ttk.Label(top_frame, text="Výchozí typ pro nová ID:").pack(side="left", padx=5)
        self.global_type_var = tk.StringVar(value="LOK")
        ttk.Radiobutton(
            top_frame,
            text="LOK",
            value="LOK",
            variable=self.global_type_var,
            command=self.sync_global_type,
        ).pack(side="left", padx=5)
        ttk.Radiobutton(
            top_frame,
            text="FIDE",
            value="FIDE",
            variable=self.global_type_var,
            command=self.sync_global_type,
        ).pack(side="left", padx=5)

        self.auto_focus_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            top_frame,
            text="Automaticky aktivovat okno Swiss-Manageru",
            variable=self.auto_focus_var,
        ).pack(side="left", padx=20)

        ttk.Button(top_frame, text="❓ Nápověda", command=self.show_help).pack(
            side="right", padx=5
        )

        # --- MAIN AREA ---
        main_frame = ttk.Frame(self.root, padding=5)
        main_frame.pack(fill="both", expand=True)

        # Levý panel - surový vstup (úzký, hlavní prostor má tabulka vpravo)
        left_frame = ttk.LabelFrame(
            main_frame, text=" 1. Seznam ID (řádek = ID) ", padding=5
        )
        left_frame.pack(side="left", fill="y", padx=(0, 5))

        self.input_text = tk.Text(left_frame, width=10, height=15)
        self.input_text.pack(fill="both", expand=True, pady=5)

        ttk.Button(left_frame, text="Načíst do editoru ➔", command=self.load_ids).pack(
            fill="x", pady=5
        )

        # Pravý panel - interaktivní tabulka
        right_frame = ttk.LabelFrame(
            main_frame, text=" 2. Kontrola a úprava jednotlivých ID ", padding=5
        )
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        self.canvas = tk.Canvas(right_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            right_frame, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        canvas_window = self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        # Vnitřní frame drží šířku canvasu, jinak řádky přetečou mimo okno
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfigure(canvas_window, width=e.width),
        )
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- BOTTOM PANEL ---
        bottom_frame = ttk.Frame(self.root, padding=5)
        bottom_frame.pack(fill="x", side="bottom")

        self.btn_start = ttk.Button(
            bottom_frame, text="▶ START (Auto)", command=self.start_automation
        )
        self.btn_start.pack(side="left", padx=5)

        self.btn_next = ttk.Button(
            bottom_frame, text="⏭ NEXT (Krok)", command=self.step_automation
        )
        self.btn_next.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(
            bottom_frame, text="⏹ STOP", command=self.stop_automation, state="disabled"
        )
        self.btn_stop.pack(side="left", padx=5)

        self.status_var = tk.StringVar(
            value="Připraven. Vložte ID a klikněte na 'Načíst'."
        )
        ttk.Label(
            bottom_frame,
            textvariable=self.status_var,
            font=("Helvetica", 10, "bold"),
            foreground="blue",
        ).pack(side="right", padx=10)

    # --------------------------------------------------------------- nápověda

    HELP_TEXT = (
        "⚠️  UPOZORNĚNÍ\n"
        "\n"
        "Aplikace pouze emuluje stisky kláves (Alt+Q, Ctrl+V, Enter)\n"
        "v okně Swiss-Manageru. Během vkládání NESAHEJTE na klávesnici\n"
        "ani myš — každý zásah může poslat ID do špatného okna!\n"
        "\n"
        "POSTUP\n"
        "\n"
        "1. Ve Swiss-Manageru otevřete turnaj a dialog pro zadávání\n"
        "    hráčů, aby byl kurzor v poli pro vyhledání podle ID.\n"
        "2. V této aplikaci vlevo vložte seznam ID (každé na vlastní\n"
        "    řádek). Typ ID musí odpovídat výběru v horní liště\n"
        "    (LOK/FIDE). Pak klikněte na „Načíst do editoru“.\n"
        "3. V tabulce zkontrolujte typ ID (LOK/FIDE) a načtená\n"
        "    jména — hosté z jiných oddílů jsou červeně s „(Host)“.\n"
        "4. Klikněte na START. Okno Swiss-Manageru se aktivuje samo;\n"
        "    bez auto-aktivace na něj přepněte během 5s odpočtu.\n"
        "5. Aplikace postupně vloží všechny hráče, stav vidíte\n"
        "    u každého řádku. STOP zastaví po aktuální položce,\n"
        "    NEXT vkládá po jednom.\n"
        "6. Po dokončení zkontrolujte ve Swiss-Manageru počet\n"
        "    a jména vložených hráčů."
    )

    def show_help(self):
        win = tk.Toplevel(self.root)
        win.title("Nápověda — Klikej SM")
        win.transient(self.root)
        win.resizable(False, False)

        ttk.Label(win, text=self.HELP_TEXT, justify="left", padding=15).pack()
        ttk.Button(win, text="Rozumím", command=win.destroy).pack(pady=(0, 12))

        # Modálně: musí se odkliknout
        win.grab_set()
        win.focus_set()

    # --------------------------------------------------- pomocné (thread-safe)

    def ui(self, func, *args):
        """Naplánuje volání do hlavního Tk vlákna (Tkinter není thread-safe)."""
        self.root.after(0, func, *args)

    def set_status(self, text):
        self.ui(self.status_var.set, text)

    def update_row_ui(self, index, text, color):
        if 0 <= index < len(self.parsed_rows):
            label = self.parsed_rows[index]["status_label"]
            self.ui(lambda: label.config(text=text, foreground=color))

    def ui_state_running(self):
        self.btn_start.config(state="disabled")
        self.btn_next.config(state="disabled")
        self.btn_stop.config(state="normal")

    def ui_state_idle(self):
        self.btn_start.config(state="normal")
        self.btn_next.config(state="normal")
        self.btn_stop.config(state="disabled")

    # ------------------------------------------------------------- načítání

    def load_ids(self):
        if self.running:
            return

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.parsed_rows = []
        self.current_index = 0

        raw_text = self.input_text.get("1.0", "end-1c")
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

        if not lines:
            messagebox.showwarning("Varování", "Vstupní pole je prázdné!")
            return

        for idx, id_val in enumerate(lines):
            row_frame = ttk.Frame(self.scrollable_frame)
            row_frame.pack(fill="x", expand=True)

            ttk.Label(
                row_frame, text=f"{idx + 1}. {id_val}", width=12, anchor="w"
            ).pack(side="left", padx=2)

            type_var = tk.StringVar(value=self.global_type_var.get())
            ttk.Combobox(
                row_frame,
                textvariable=type_var,
                values=["LOK", "FIDE"],
                width=5,
                state="readonly",
            ).pack(side="left", padx=2)

            lbl_status = ttk.Label(
                row_frame, text="Čeká", foreground="gray", width=10, anchor="center"
            )
            lbl_status.pack(side="left", padx=2)

            lbl_name = ttk.Label(row_frame, text="⏳", foreground="gray", anchor="w")
            lbl_name.pack(side="left", fill="x", expand=True, padx=4)

            self.parsed_rows.append(
                {
                    "id": id_val,
                    "type_var": type_var,
                    "status_label": lbl_status,
                    "name_label": lbl_name,
                    "member": None,
                }
            )

        self.canvas.yview_moveto(0)
        self.status_var.set(f"Úspěšně načteno {len(self.parsed_rows)} položek.")

        self.load_generation += 1
        threading.Thread(
            target=self.lazy_load_members, args=(self.load_generation,), daemon=True
        ).start()

    def sync_global_type(self):
        new_type = self.global_type_var.get()
        for row in self.parsed_rows:
            row["type_var"].set(new_type)

    # ------------------------------------------------- lazy loading z api.chess.cz

    def ui_row_name(self, row, generation, text, color):
        def apply():
            if generation != self.load_generation:
                return
            try:
                row["name_label"].config(text=text, foreground=color)
            except tk.TclError:
                pass  # řádek už byl zničen novým "Načíst"

        self.ui(apply)

    def lazy_load_members(self, generation):
        rows = self.parsed_rows
        for row in rows:
            if generation != self.load_generation:
                return
            id_type = row["type_var"].get()
            key = (id_type, row["id"])
            if key not in _member_cache:
                time.sleep(1.0)  # pauza mezi requesty (API blokuje rychlé dotazy)
            try:
                member = fetch_member(id_type, row["id"])
            except Exception:
                member = None
            row["member"] = member
            if member:
                name = (member.get("fullName") or "").strip()
                club = (member.get("clubName") or "").strip()
                text = f"{name} — {club}" if club else name
                self.ui_row_name(row, generation, text, "gray")
            else:
                self.ui_row_name(row, generation, "⚠ nenalezeno", "red")

        # Sjednocení barev: nejčastější oddíl černě, ostatní červeně + (Host)
        if generation != self.load_generation:
            return
        clubs = [
            (r["member"].get("clubName") or "").strip() for r in rows if r["member"]
        ]
        clubs = [c for c in clubs if c]
        if not clubs:
            return
        main_club = Counter(clubs).most_common(1)[0][0]
        for row in rows:
            member = row["member"]
            if not member:
                continue
            name = (member.get("fullName") or "").strip()
            club = (member.get("clubName") or "").strip()
            if club == main_club:
                self.ui_row_name(row, generation, f"{name} — {club}", "black")
            else:
                self.ui_row_name(row, generation, f"{name} — {club} (Host)", "red")

    # ------------------------------------------------------------ automatizace

    def execute_paste_logic(self, item):
        id_val = item["id"]
        prefix = "i" if item["type_var"].get() == "LOK" else "f"

        paste_and_confirm(prefix + id_val)
        time.sleep(0.9)

    def process_current_item(self):
        item = self.parsed_rows[self.current_index]
        self.update_row_ui(self.current_index, "▓ Zpracovávám", "orange")
        self.execute_paste_logic(item)
        self.update_row_ui(self.current_index, "✅ Hotovo", "green")
        self.current_index += 1

    def prepare_target_window(self, countdown):
        """Auto režim: aktivuje okno Swiss-Manageru. Ruční: odpočet na přepnutí.

        Vrací False, pokud byl běh zastaven nebo se okno nepodařilo najít
        (v tom případě už nastavila idle stav).
        """
        if self.auto_focus_var.get():
            self.set_status("Aktivuji okno Swiss-Manageru…")
            if not activate_swiss_window():
                self.running = False
                self.ui(self.ui_state_idle)
                self.set_status("❌ Okno Swiss-Manageru nenalezeno!")
                self.ui(
                    messagebox.showwarning,
                    "Chyba",
                    "Nenašel jsem běžící aplikaci 'Swiss…'.\n"
                    "Spusťte Swiss-Manager, nebo vypněte automatickou aktivaci.",
                )
                return False
            time.sleep(0.5)
            return True

        for i in range(countdown, 0, -1):
            if not self.running:
                self.ui(self.ui_state_idle)
                self.set_status("Zastaveno.")
                return False
            self.set_status(f"AKTIVUJTE SWISS-MANAGER! Start za {i}s...")
            time.sleep(1)
        return True

    def automation_loop(self):
        if not self.prepare_target_window(countdown=5):
            return

        total = len(self.parsed_rows)
        while self.running and self.current_index < total:
            self.set_status(f"Vkládám řádek {self.current_index + 1}/{total}...")
            self.process_current_item()

        self.running = False
        self.ui(self.ui_state_idle)
        if self.current_index >= total:
            self.set_status("✅ Všechna ID úspěšně vložena!")
            self.ui(
                messagebox.showinfo, "Hotovo", "Všechna ID byla úspěšně zpracována."
            )
        else:
            self.set_status(f"Zastaveno na položce {self.current_index + 1}.")

    def start_automation(self):
        if not self.parsed_rows:
            messagebox.showwarning("Chyba", "Nejdříve musíte načíst nějaká ID!")
            return
        if self.current_index >= len(self.parsed_rows):
            if messagebox.askyesno(
                "Konec seznamu", "Všechna ID už byla zpracována. Začít znovu?"
            ):
                self.reset_statuses()
            else:
                return

        self.running = True
        self.ui_state_running()
        threading.Thread(target=self.automation_loop, daemon=True).start()

    def step_automation(self):
        if self.running:
            return
        if not self.parsed_rows:
            messagebox.showwarning("Chyba", "Nejdříve musíte načíst nějaká ID!")
            return
        if self.current_index >= len(self.parsed_rows):
            messagebox.showinfo("Konec", "Všechny položky již byly zpracovány.")
            return

        self.running = True
        self.ui_state_running()

        def single_step():
            if not self.prepare_target_window(countdown=5):
                return

            self.set_status(f"Krokování: Vkládám {self.current_index + 1}...")
            self.process_current_item()

            self.running = False
            self.ui(self.ui_state_idle)
            self.set_status(
                f"Krok dokončen. Připraven na položku {self.current_index + 1}."
            )

        threading.Thread(target=single_step, daemon=True).start()

    def stop_automation(self):
        self.running = False
        self.status_var.set("Zastavuji proces...")

    def reset_statuses(self):
        self.current_index = 0
        for idx in range(len(self.parsed_rows)):
            self.update_row_ui(idx, "Čeká", "gray")


if __name__ == "__main__":
    root = tk.Tk()
    SwissManagerAutomator(root)
    root.mainloop()
