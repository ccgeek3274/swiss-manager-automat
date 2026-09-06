"""Smoke test volání Win32 API. Spouští se na Windows runneru ve workflow.

Deklarace ctypes a práce s okny se na Linuxu ani macOS vůbec nevykonají,
takže bez tohohle testu se chyba v nich pozná až u uživatele.
"""
import sys
import tkinter as tk

import naklikej_hrace as m

assert m.IS_WINDOWS, "test má smysl jen na Windows"

okna = m._win_visible_titles()
print(f"EnumWindows OK, viditelnych oken: {len(okna)}")
assert okna, "runner nema zadne viditelne okno"

# _win_activate() nesmí zůstat nespuštěná: hledání podle názvu ji na runneru
# nikdy nezavolá, protože tu žádný Swiss-Manager neběží
hwnd, title = okna[0]
print(f"_win_activate() na {title!r} vratilo {m._win_activate(hwnd)}")

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

    assert m._win_activate_swiss() is False, "bez Swiss-Manageru musi vratit False"
    print("_win_activate_swiss() bez Swiss-Manageru vraci False - OK")

    print("--- diagnostics_report() ---")
    print(m.diagnostics_report())
finally:
    root.destroy()

print("vse OK")
sys.exit(0)
