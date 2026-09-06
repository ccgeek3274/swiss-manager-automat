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
root2 = tk.Tk()
root2.withdraw()
app = m.SwissManagerAutomator.__new__(m.SwissManagerAutomator)
app.root = root2
app._ui_thread_id = threading.get_ident()

vysledek = {}


def z_pracovniho_vlakna():
    try:
        vysledek["vlakno"] = app.call_on_ui_thread(threading.get_ident)
    except Exception as exc:
        vysledek["chyba"] = exc
    finally:
        root2.after(0, root2.quit)


t = threading.Thread(target=z_pracovniho_vlakna)
# Vlakno smi startovat az ze smycky udalosti: root.after() z jineho vlakna
# funguje jen pri bezicim mainloop, jinak Tkinter vyhodi RuntimeError
root2.after(50, t.start)
root2.mainloop()
t.join()
root2.destroy()

assert "chyba" not in vysledek, f"call_on_ui_thread selhal: {vysledek.get('chyba')!r}"
assert vysledek["vlakno"] == threading.get_ident(), (
    f"call_on_ui_thread musi bezet v hlavnim vlakne "
    f"({vysledek['vlakno']} != {threading.get_ident()})"
)
print("call_on_ui_thread() z pracovniho vlakna bezi v hlavnim - OK")

root3 = tk.Tk()
root3.withdraw()
app.root = root3
assert app.call_on_ui_thread(lambda: 42) == 42, "z hlavniho vlakna primo"
root3.destroy()
print("call_on_ui_thread() z hlavniho vlakna neblokuje - OK")

print("vse OK")
sys.exit(0)
