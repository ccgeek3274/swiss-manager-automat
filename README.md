# Swiss-Manager Automat

Pomocná aplikace pro hromadné zadávání hráčů do [Swiss-Manageru](https://swiss-manager.at/).
Místo ručního opisování desítek ID se vloží seznam, zkontroluje se v tabulce
a aplikace pak ID postupně naklikne do dialogu pro přidání hráče.

![Python 3](https://img.shields.io/badge/python-3.x-blue) ![Windows | macOS](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)

## Co umí

- **Seznam ID na vstupu** — každé ID na vlastní řádek, typ LOK (šachy.cz) nebo FIDE.
- **Kontrola před vložením** — ke každému ID se z [api.chess.cz](https://api.chess.cz)
  načte jméno a oddíl. Nejčastější oddíl v seznamu se bere jako domácí a zobrazí
  se černě, hráči z jiných oddílů červeně s příznakem `(Host)`, nenalezená ID
  jako `⚠ nenalezeno`. Překlep v ID je tak vidět dřív, než se začne vkládat.
- **Automatické vkládání** — START projede celý seznam, NEXT vloží jednoho hráče,
  STOP zastaví po aktuální položce. Stav se průběžně ukazuje u každého řádku.
- **Aktivace okna Swiss-Manageru** — volitelně si aplikace okno najde a přepne
  se do něj sama; jinak je na přepnutí 5 sekund odpočtu.

Do vyhledávacího pole se vkládá ID s předponou `i` pro LOK a `f` pro FIDE.

## Požadavky

Python 3 se standardní knihovnou — **žádné pip balíčky**. GUI je v Tkinteru,
schránka a stisky kláves se řeší systémovými nástroji:

| Platforma | Použité nástroje |
|---|---|
| Windows | PowerShell — `Set-Clipboard`, `WScript.Shell` (SendKeys); přepnutí okna přes Win32 API (`ctypes`) |
| macOS | `pbcopy`, `osascript` (System Events) |

Na macOS je potřeba dát Terminálu (nebo výsledné aplikaci) oprávnění
**Zpřístupnění pro počítač** v Nastavení → Soukromí a zabezpečení, jinak
System Events klávesy neodešle.

## Spuštění

```bash
python3 naklikej_hrace.py
```

Na macOS jde místo toho dvojkliknout na **`naklikej_hrace.command`** ve Finderu —
otevře Terminál a spustí aplikaci. Musí ležet ve stejné složce jako
`naklikej_hrace.py`. Oprávnění „Zpřístupnění pro počítač“ se v tomto případě
uděluje Terminálu.

## Hotové sestavené soubory

Poslední vydání je v [Releases](../../releases):

| Soubor | Platforma | Poznámka |
|---|---|---|
| `SwissManagerAutomat.exe` | Windows | Jeden soubor, Python uvnitř, nic se neinstaluje |
| `SwissManagerAutomat-macos.zip` | macOS | Samostatný `.command` — vyžaduje na stroji Python 3 |

Obojí staví GitHub Actions ([`.github/workflows/build.yml`](.github/workflows/build.yml))
na tag `v*`. Sestavení `.exe` ručně na vlastním Windows stroji popisuje
[BUILD_WINDOWS.md](BUILD_WINDOWS.md).

Ani jeden soubor není digitálně podepsaný:

- **Windows** — SmartScreen při prvním spuštění varuje („neznámý vydavatel“),
  je potřeba kliknout na *Další informace* → *Přesto spustit*.
- **macOS** — stažený soubor má karanténní příznak, takže Gatekeeper dvojklik
  odmítne. Pomůže pravé tlačítko → *Otevřít*, nebo
  `xattr -dr com.apple.quarantine SwissManagerAutomat.command`.

## Postup práce

1. Ve Swiss-Manageru otevřít turnaj a dialog pro zadávání hráčů tak, aby byl
   kurzor v poli pro vyhledání podle ID.
2. V aplikaci vlevo vložit seznam ID a kliknout na **Načíst do editoru**.
3. V tabulce zkontrolovat typ ID (LOK/FIDE) a načtená jména.
4. Kliknout na **START** — okno Swiss-Manageru se aktivuje samo, nebo se do něj
   přepnout během 5s odpočtu.
5. Po dokončení zkontrolovat ve Swiss-Manageru počet a jména vložených hráčů.

## Když se nepřepne na Swiss-Manager

Tlačítko **🔍 Diagnostika** vypíše všechna otevřená okna i s názvem jejich
`.exe` a šipkou označí to, které aplikace považuje za Swiss-Manager.
Tlačítkem **Zkusit přepnout** se aktivace vyzkouší samostatně, bez spouštění
celé automatizace. Když se přepnutí nepovede, vypíše se, na jaké okno se
mířilo a co zůstalo v popředí.

Okno se hledá podle názvu `.exe`, ne podle titulku — titulek obsahuje „swiss“
i u téhle aplikace a u prohlížeče s otevřeným tímhle repozitářem.

## ⚠️ Upozornění

Aplikace pouze **emuluje stisky kláves** (Alt+Q, Ctrl+V, Enter) v aktivním okně.
Během vkládání nesahejte na klávesnici ani myš — každý zásah může poslat ID
do jiného okna.

Aplikace nedokáže rozpoznat chyby. Když se dialog Swiss-Manageru zachová jinak,
než se čeká — typicky u hráče, který není na nahrané Elo listině — půjdou další
stisky kláves do nesprávných polí. Průběh proto sledujte a při nesrovnalosti
dejte STOP.

## Soubory

| Soubor | Popis |
|---|---|
| `naklikej_hrace.py` | Celá aplikace |
| `naklikej_hrace.command` | Spouštěč pro macOS — dvojklik ve Finderu |
| `smoke_test_windows.py` | Test volání Win32 API, běží ve workflow na Windows runneru |
| `gen_icon.py` | Jednorázový generátor `icon.png` / `icon.ico` — `python3 gen_icon.py <ikona-SM.png>`, zapisuje vedle skriptu (vyžaduje Pillow) |
| `icon.png`, `icon.ico` | Ikona okna a exe |
| `BUILD_WINDOWS.md` | Build `.exe` pro Windows |
