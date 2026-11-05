# Blender → Fusion Export Bridge

**0.1.0 — Windows, pierwsza wersja do testów w aplikacjach.**

Zaznacz model w Blenderze → **Wyślij do Fusion** → odbiornik tworzy nowy dokument
Autodesk Fusion i importuje osobne, nazwane siatki. Po jednorazowej instalacji transfer
wymaga jednego kliknięcia w otwartym panelu. Fusion powinien działać z aktywnym
odbiornikiem; opcjonalnie Blender może uruchamiać wskazany skrót Fusion.

**Modele trafiają jako siatki (mesh bodies), nie bryły parametryczne BRep/STEP.**
Nie jest odtwarzana historia modelowania, materiały ani tekstury. Kierunek Fusion →
Blender nie jest częścią tej wersji.

## Instalacja na Windows

Paczka: `Blender-Fusion-Bridge-0.1.0-Windows.zip`. W repozytorium zbudujesz ją przez
`python tools/build.py`; wynik trafia do `dist/`. Workflow GitHub Actions też buduje
paczkę po uruchomieniu testów.

1. Rozpakuj **całą paczkę Windows**.
2. Uruchom **Install-Fusion.cmd**. Instaluje odbiornik w stałym folderze bieżącego
   użytkownika i otwiera ten folder. Nie wymaga administratora, niczego nie pobiera
   i nie zmienia globalnej polityki PowerShell.
3. W Fusion: **Utilities → Add-Ins → Scripts and Add-Ins → Add-Ins → +**. Wskaż
   folder `BlenderFusionBridge` otwarty przez instalator (lub `BlenderFusionBridge.py`,
   jeśli okno wymaga pliku). Wybierz **Run**, włącz **Run on Startup**. Nazwy sekcji
   mogą różnić się zależnie od wersji i języka Fusion.
4. W Blenderze: **Edit → Preferences → Add-ons → Install from Disk…** (w starszych
   wersjach **Install…**). Wybierz wewnętrzny plik **blender_fusion_bridge-0.1.0.zip**,
   pozostawiając go spakowanym. Włącz **Blender → Fusion Bridge**. Nie instaluj całej
   paczki Windows jako dodatku Blendera.

Folder odbiornika: `%LOCALAPPDATA%\BlenderFusionBridge\AddIns\BlenderFusionBridge`.
Bez instalatora można skopiować folder `BlenderFusionBridge` w stałe miejsce i wskazać
je w Fusion. Przeniesienie go później wymaga ponownej rejestracji.

## Codzienna praca

1. Zaznacz obiekt lub kilka obiektów w **Object Mode**.
2. W widoku 3D otwórz panel klawiszem **N**, kartę **Fusion** i kliknij **Wyślij do Fusion**.

Alternatywy: **F3 → Wyślij do Fusion**, **File → Export → Wyślij do Fusion** lub
Quick Favorites po dodaniu przycisku prawym przyciskiem myszy.
Panel pokazuje **W kolejce → Importowanie → Zaimportowano** lub opis błędu.
Dokument Fusion pozostaje niezapisany — zapisujesz go w wybranym projekcie samodzielnie.
Każdy następny eksport tworzy nowy dokument, nie aktualizuje poprzedniego.

Podczas aktywnego polecenia w Fusion odbiornik czeka na jego zakończenie. Po instalacji
zamknij okno Scripts and Add-Ins. Gdy odbiornik jest wyłączony, model czeka w lokalnej
kolejce do uruchomienia dodatku. Kolejka jest zachowana także po restarcie programów.

**Opcjonalny autostart Fusion:** w preferencjach dodatku Blendera wskaż istniejący
skrót `.lnk` lub plik `.exe` Fusion. Skrót jest wygodniejszy, ponieważ aktualizacje
Fusion mogą zmieniać lokalizację programu. Nadal wymagane są odbiornik i Run on Startup.
Logowanie lub aktualizacja Fusion mogą wymagać interakcji użytkownika.

## Wymiary i orientacja

Domyślnie **1 jednostka Blendera = Unit Scale × 1000 mm**. Dotyczy to również
`Unit System = None`: domyślna jednostka oznacza wtedy 1 m. Sama zmiana `Length`
na milimetry zmienia sposób wyświetlania, nie skalę geometrii. Panel pokazuje przelicznik.

| Przypadek | Ustawienie dodatku | Wynik |
|---|---|---|
| Rzeczywisty wymiar w Blenderze 20 mm | Ze sceny | 20 mm w Fusion |
| Wpisujesz 20 jednostek, traktując je jako 20 mm | 1 BU = 1 mm | 20 mm w Fusion |
| Kostka 2 BU, Unit Scale = 1 | Ze sceny | 2000 mm w Fusion |
| Kostka 2 BU, Unit Scale = 0.001 | Ze sceny | 2 mm w Fusion |

Zachowywane są **osie XYZ, Z w górę**, położenie w świecie, rotacja, skala,
transformacje rodziców i odbicia. Transformacje są zapisane we współrzędnych siatki;
hierarchia, pivoty i constraints nie są przenoszone. Nie ma zamiany Y/Z. Ustawienie
widoku „Up” w Fusion może wpływać na odbiór orientacji na ekranie, ale nie współrzędne.

Eksport obejmuje wynik modyfikatorów widoczny w viewport w bieżącej klatce, bez Apply
ani zmiany `.blend`. Obsługiwane typy: **Mesh, Curve, Surface, Text**.
Geometry Nodes: użyj **Realize Instances**, jeśli wynik zawiera instancje.
Instancje kolekcji, metakule, rig i animacja nie są przenoszone w tej wersji.
Samodzielne wierzchołki i krawędzie nie tworzą powierzchni STL.

Limit jednego transferu: **500 obiektów / 5 mln trójkątów**. To limit transportu,
nie gwarancja płynności Fusion. Duże modele mogą długo się przetwarzać; eksport w
Blenderze i import w Fusion wykonują się synchronicznie w wątkach UI.

## Aktualizacja i usunięcie

Przed aktualizacją zatrzymaj odbiornik w Fusion, wyłącz dodatek Blendera i zamknij
oba programy. Zainstaluj nową paczkę w tych samych miejscach. Instalator odrzuca
nadpisanie uruchomionego odbiornika. Nie uruchamiaj kilku wersji odbiornika.

Usuwanie: wyłącz i usuń dodatek Blendera; zatrzymaj i usuń wpis odbiornika w Fusion,
a następnie jego folder instalacyjny. Dane transferów są osobno w podfolderze `jobs`.

## Transfery i diagnostyka

Most działa na jednym komputerze i tym samym koncie Windows, bez portów TCP, serwera
ani dodatkowych bibliotek. Sam nie wysyła plików do internetu; zapis i synchronizacja
projektu przez Fusion odbywają się zgodnie z ustawieniami Fusion.

`%LOCALAPPDATA%\BlenderFusionBridge` zawiera:

- `jobs/<id>/`: STL, manifest i status transferu;
- `receiver.json`: aktualny status odbiornika;
- `receiver.log`: rotowany dziennik problemów odbiornika;
- `AddIns/`: zainstalowany kod odbiornika.

Kliknij **Otwórz folder transferów**, aby znaleźć diagnostykę. Transfery pozostają
na dysku do ręcznego usunięcia. Usuwaj zakończone transfery przy zatrzymanym odbiorniku;
usunięcie całego `jobs` kasuje też oczekujące eksporty. Nie wpływa na modele już
otwarte/zapisane w Fusion. Nie usuwaj `receiver.lock`, gdy Fusion działa.

| Objaw | Działanie |
|---|---|
| „Odbiornik wyłączony” | Uruchom BlenderFusionBridge w Fusion i włącz Run on Startup. |
| „Zakończ aktywne polecenie” | Zakończ/anuluj polecenie w Fusion; odbiornik go nie anuluje. |
| „Import przerwany” | Sprawdź dokumenty Fusion; w razie potrzeby wyślij model ponownie. |
| Model 1000 razy za duży | Sprawdź Unit Scale oraz „Ze sceny” / „1 BU = 1 mm”. |
| Błąd importu | Przeczytaj opis w panelu i status.json. Spróbuj prostszej siatki. |
| Niepełny wynik Geometry Nodes | Zrealizuj instancje. |
| Brak dodatku Blendera | Instaluj wewnętrzny ZIP dodatku, nie cały zestaw. |

Nieudany import zamyka wyłącznie nowo utworzony dokument, bez zapisywania. Jeśli
Fusion odmówi jego zamknięcia, komunikat wskazuje możliwość pozostawienia częściowego
dokumentu. Po awarii procesu nie ma automatycznego ponowienia importu, aby uniknąć duplikatów.

## Kod i testy

Kod celuje w **Blender 3.6+ i bieżący Autodesk Fusion na Windows 10/11**.
Zgodność z konkretną instalacją wymaga próby w obu aplikacjach.

```powershell
python -m unittest discover -s tests -v
python -m compileall -q blender fusion common tools
python tools/build.py
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --factory-startup --python tools/blender_smoke.py
```

Ścieżka Blendera jest przykładem; wskaż własną instalację. Test headless tworzy
scenę w osobnym procesie, nie otwiera ani nie zapisuje Twoich projektów.
Testy API jednostkowych używają atrap, więc nie zastępują testu w aplikacjach.
Lista prób: [docs/TESTING.md](docs/TESTING.md).

Źródła: `blender/`, `fusion/`, `common/`. Skrypt budowania kopiuje wspólne moduły
do obu paczek. Instaluj zbudowane paczki, nie niekompletne foldery źródłowe.
Opis protokołu: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
