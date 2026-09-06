"""Smoke test volání Win32 API. Spouští se na Windows runneru ve workflow.

Deklarace ctypes a práce s okny se na Linuxu ani macOS vůbec nevykonají,
takže bez tohohle testu se chyba v nich pozná až u uživatele.
"""
import sys
import threading
import time
import tkinter as tk

import naklikej_hrace as m

assert m.IS_WINDOWS, "test má smysl jen na Windows"

okna = m._win_visible_titles()
print(f"EnumWindows OK, viditelnych oken: {len(okna)}")
assert okna, "runner nema zadne viditelne okno"

# _win_activate() nesmí zůstat nespuštěná: hledání podle názvu ji na runneru
# nikdy nezavolá, protože tu žádný Swiss-Manager neběží
hwnd, title = okna[0]

# Runner rozhoduje, ve kterém vlakne se preda popredi — musi se opravdu pouzit
pouzity_runner = []


def zaznamenavaci_runner(func):
    pouzity_runner.append(threading.get_ident())
    return func()


uspech = m._win_activate(hwnd, zaznamenavaci_runner)
assert pouzity_runner, "_win_activate musi predani popredi poslat pres runner"
print(f"runner pouzit {len(pouzity_runner)}x - OK")
print(f"_win_activate() na {title!r} vratilo {uspech}")
print(f"_win_describe(): {m._win_describe(hwnd)}")
if uspech:
    assert m.activation_error() == "", "po uspechu nesmi zustat popis chyby"
    print("po uspechu je popis chyby prazdny - OK")

print(f"_win_exe_name() prvniho okna: {m._win_exe_name(hwnd)!r}")

# Regrese: vlastní okno se nesmí vybrat jako cíl. Titulek aplikace obsahuje
# "Swiss-Manager" a při stisku STARTu je okno v popředí, takže ve výčtu vyjde
# první — dřív si aplikace aktivovala sama sebe a vkládala hráče do sebe.
root = tk.Tk()
root.title("Swiss-Manager Automation Tool")
root.update()
try:
    vybrano = m._win_find_swiss()
    assert vybrano is None, (
        f"vlastni okno se nesmi vybrat, ale vybralo se hwnd={vybrano} "
        f"({m._win_title(vybrano)!r})"
    )
    print("vlastni okno se preskakuje - OK")

    primy_runner = (lambda func: func())
    assert m._win_activate_swiss(primy_runner) is False, (
        "bez Swiss-Manageru musi vratit False"
    )
    print("_win_activate_swiss() bez Swiss-Manageru vraci False - OK")
    assert m.activation_error(), "neuspech musi byt popsany pro chybovou hlasku"
    print(f"popis neuspechu: {m.activation_error().strip()}")

    print("--- diagnostics_report() ---")
    print(m.diagnostics_report())
finally:
    root.destroy()

# Regrese: predani popredi musi probehnout v hlavnim vlakne. Z pracovniho
# Windows SetForegroundWindow odmitne a zabere jen vyneseni okna navrch —
# okno ostatni prekryje, ale aktivaci nedostane a GetForegroundWindow pak
# hlasi porad nasi aplikaci.
# Regrese: predani popredi musi probehnout v hlavnim vlakne. Z pracovniho
# Windows SetForegroundWindow odmitne a zabere jen vyneseni okna navrch —
# okno ostatni prekryje, ale aktivaci nedostane a GetForegroundWindow pak
# hlasi porad nasi aplikaci.
#
# Testuje se rozhodovani call_on_ui_thread proti nahradnimu rootu: skutecny
# Tk by sem pritahl vlaknovy model Tcl, ktery s testovanou logikou nesouvisi.


class NahradniRoot:
    def __init__(self):
        self.naplanovane = []

    def after(self, _ms, func, *args):
        self.naplanovane.append(lambda: func(*args))


hlavni_vlakno = threading.get_ident()
app = m.SwissManagerAutomator.__new__(m.SwissManagerAutomator)
app.root = NahradniRoot()
app._ui_thread_id = hlavni_vlakno

vysledek = {}


def z_pracovniho_vlakna():
    try:
        vysledek["vlakno"] = app.call_on_ui_thread(threading.get_ident)
    except Exception as exc:
        vysledek["chyba"] = exc


t = threading.Thread(target=z_pracovniho_vlakna)
t.start()

# Hlavni vlakno odbavi naplanovanou praci, presne jako by to udelal mainloop
konec = time.time() + 10
while not app.root.naplanovane and time.time() < konec:
    time.sleep(0.01)
assert app.root.naplanovane, "z pracovniho vlakna se musi planovat pres root.after()"
app.root.naplanovane.pop()()
t.join(timeout=10)
assert not t.is_alive(), "call_on_ui_thread se po odbaveni musi vratit"

assert "chyba" not in vysledek, f"call_on_ui_thread selhal: {vysledek.get('chyba')!r}"
assert vysledek["vlakno"] == hlavni_vlakno, (
    f"funkce musi probehnout v hlavnim vlakne "
    f"({vysledek['vlakno']} != {hlavni_vlakno})"
)
print("call_on_ui_thread() z pracovniho vlakna bezi v hlavnim - OK")

# Z hlavniho vlakna se musi volat rovnou, jinak by se cekalo samo na sebe
app.root.naplanovane.clear()
assert app.call_on_ui_thread(lambda: 42) == 42
assert not app.root.naplanovane, "z hlavniho vlakna se nic neplanuje"
print("call_on_ui_thread() z hlavniho vlakna volá primo - OK")

print("vse OK")
sys.exit(0)
