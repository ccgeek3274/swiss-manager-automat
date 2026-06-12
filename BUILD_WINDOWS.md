# Jak vyrobit naklikej_hrace.exe pro Windows

Skript je multiplatformní — na Windows používá PowerShell (Set-Clipboard + SendKeys),
na macOS pbcopy + osascript. Nepotřebuje žádné pip balíčky.

## Varianta A: Build na libovolném Windows počítači (jednorázově)

1. Nainstalovat Python — 3.13 nebo libovolný novější (stačí jednou,
   na počítači kde se buildí):

   ```
   winget install Python.Python.3.13
   ```

   (nebo z https://python.org — při instalaci zaškrtnout "Add Python to PATH")

2. V příkazové řádce (cmd / PowerShell) ve složce se skriptem:

   ```
   pip install pyinstaller
   pyinstaller --onefile --windowed --name SwissManagerAutomat --icon icon.ico --add-data "icon.png;." naklikej_hrace.py
   ```

   (soubory `icon.ico` a `icon.png` musí ležet vedle skriptu — `icon.ico` je
   ikona exe, `icon.png` se přibalí dovnitř pro titulek okna)

3. Hotový soubor je v `dist\SwissManagerAutomat.exe` — jediný soubor,
   stačí poslat kolegům, spouští se dvojklikem, nic se neinstaluje.

Poznámky:
- První spuštění exe je pomalejší (rozbaluje se do temp složky) — normální.
- Windows SmartScreen může při prvním spuštění varovat ("neznámý vydavatel") —
  kliknout na "Další informace" → "Přesto spustit".

## Varianta B: Bez buildu — poslat .py + start.bat

Pokud není po ruce Windows na build, poslat kolegům `naklikej_hrace.py`
a tento `start.bat` do stejné složky:

```bat
@echo off
where python >nul 2>nul || winget install -e --id Python.Python.3.13
python naklikej_hrace.py
```

První spuštění doinstaluje Python, další už jen spouští aplikaci.

## Použití (pro kolegy)

1. Spustit aplikaci, vlevo vložit seznam ID (každé na nový řádek).
2. "Načíst do editoru" → vpravo zkontrolovat typ (LOK = předpona `i`, FIDE = předpona `f`).
3. Otevřít Swiss-Manager s dialogem pro přidání hráče.
4. Kliknout START (nebo NEXT pro jeden krok) a do 5 sekund přepnout do okna Swiss-Manageru.
5. Nesahat na klávesnici/myš, dokud to běží; STOP zastaví po aktuální položce.
