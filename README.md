# Blender ↔ Fusion Bridge

**0.2.2 — Windows.** Wersja 0.1.0 Blender → nowy dokument Fusion została sprawdzona
przez użytkownika. Nowe funkcje 0.2.2 mają testy automatyczne; wymagają jeszcze próby
w rzeczywistych aplikacjach na Windows.

## Poprawka Fusion 0.2.2

Naprawia „3 : invalid id”: identyfikator komendy zawiera teraz wyłącznie dozwolone
litery, cyfry i podkreślenia. Rejestracja sprząta pozostałości przycisku po błędzie,
a komunikaty startowe zawierają etap i traceback. Przycisk jest domyślnie przypięty
w Design → Utilities → Add-Ins. Zamknij Fusion, zastąp cały folder odbiornika i uruchom
Fusion ponownie, aby usunąć z pamięci starszą kopię commands.py.
Blender 0.2.1 jest zgodny i nie wymaga ponownej instalacji do tej poprawki.

## Poprawka instalacji Blendera (od 0.2.1)

Naprawia aktualizację dodatku w uruchomionym Blenderze: stare podmoduły Python
(w tym bridge_protocol z wersji 0.1.0) są przeładowywane w kolejności zależności.
Nieudana rejestracja usuwa timery, blokadę odbiornika, menu i zarejestrowane klasy.
Jeśli poprzednia instalacja już zakończyła się błędem, przed instalacją tej wersji
zapisz projekty i zamknij wszystkie procesy Blendera. Zainstaluj wewnętrzny ZIP 0.2.2.
Protokół nadal ma numer 2; odbiornik Fusion 0.2.0 jest zgodny. Aktualizacja całego
folderu Fusion jest zalecana, aby także uruchamianie zamkniętego Blendera używało poprawki.

## Co robi

- **Blender → Fusion:** zaznaczone obiekty po modyfikatorach, do nowego albo aktywnego
  dokumentu Fusion. Wybór celu w panelu **N → Fusion**. Jeden przycisk wysyłania.
- **Fusion → Blender:** zaznaczone ciała siatkowe zachowują istniejącą geometrię
  trójkątów (bez remeshu/redukcji). Bryły BRep i otwarte ciała powierzchniowe są
  triangulowane standardowym presetem **Normal** API Fusion, bez okna ustawień jakości.
  Modele trafiają jako osobne obiekty do nowej kolekcji w otwartej scenie Blendera.
- Jeśli Blender jest zamknięty, Fusion uruchamia go w nowym oknie i przekazuje modele.
  Istniejąca zawartość sceny/startup file nie jest kasowana (także domyślna kostka).
- Oba kierunki używają STL w mm, zachowują osie XYZ (Z w górę), położenie i skalę.
  Nie przenoszą materiałów, tekstur, hierarchii, pivotów ani historii CAD.

## Aktualizacja z 0.1.0 — instalacja ręczna

1. W Fusion zatrzymaj **BlenderFusionBridge** w **Scripts and Add-Ins**.
2. Zamknij Blender. Rozpakuj cały zestaw **Blender-Fusion-Bridge-0.2.2-Windows.zip**.
3. Skopiuj **cały folder `BlenderFusionBridge`** z nowej paczki do swojego miejsca
   instalacji, np. `C:\TOOLS\BlenderFusionBridge`, zastępując poprzednią wersję.
   Zachowaj podfolder `blender_fusion_bridge`: służy do startu zamkniętego Blendera.
4. W Fusion uruchom ponownie dodatek z tej samej lokalizacji. Jeśli zmieniasz lokalizację:
   **Utilities → Add-Ins → Scripts and Add-Ins → Add-Ins → +**; wskaż folder albo
   `BlenderFusionBridge.py`, zależnie od okna. Włącz **Run on Startup**.
5. W Blenderze wyłącz stary dodatek i zainstaluj wewnętrzny ZIP
   **blender_fusion_bridge-0.2.2.zip** przez **Preferences → Add-ons → Install from Disk**.
   Włącz dodatek. Przy problemie z odświeżeniem modułów uruchom Blender ponownie.
6. Zainstaluj **obie** strony 0.2.2. Wersja 0.1.0 nie odbiera protokołu 0.2.2.

Nowa instalacja: te same kroki, pomijając zatrzymywanie starej wersji. Użytkownicy
bez blokad PowerShell mogą opcjonalnie użyć Install-Fusion.cmd zamiast kopiowania.
Nie trzeba zmieniać polityki PowerShell. Jeśli skrypt nie jest podpisany i Windows
go odrzuca, wybierz powyższą instalację ręczną.

## Blender → Fusion

W Object Mode zaznacz modele, otwórz **N → Fusion**, ustaw **Cel**:

- **Nowy dokument:** każdy transfer tworzy osobny, niezapisany dokument Fusion.
- **Aktywny dokument Fusion:** dodaje siatki do root component aktualnego dokumentu.
  Dokument Fusion musi być otwarty, a odbiornik 0.2.2 uruchomiony. Po przełączeniu
  dokumentu poczekaj ok. 2 sekundy na odświeżenie statusu i dopiero wysyłaj.

Kliknij **Wyślij do Fusion**. Przy aktywnym poleceniu Fusion poczeka na jego zakończenie.
Jeżeli w czasie oczekiwania przełączysz dokument, import zostanie odrzucony zamiast
trafić do niewłaściwego projektu. Wybierz właściwy dokument i wyślij jeszcze raz.
Przy błędzie importu do otwartego dokumentu usuwane są tylko nowo dodane siatki;
istniejący dokument nie jest zamykany. Nie ma zastępowania poprzednich obiektów.

Skróty: **F3 → Wyślij do Fusion**, **File → Export → Wyślij do Fusion**, Quick Favorites.
Obsługiwane typy Blender: Mesh, Curve, Surface, Text. Geometry Nodes z instancjami
wymaga **Realize Instances**. Eksport używa modyfikatorów viewport w bieżącej klatce,
bez ich Apply ani zmiany oryginalnych obiektów.

## Fusion → Blender

1. Zaznacz całe ciała Mesh, bryły BRep lub ciała powierzchniowe w drzewie Fusion.
2. W Design / Utilities / Add-Ins kliknij **Wyślij do Blendera** i potwierdź **OK**.
   Pole wyboru ciał przejmuje zgodne zaznaczenie; można je też uzupełnić w tym oknie.
   Nie ma ustawień triangulacji. Same ściany, krawędzie i komponenty nie są eksportowane.

Otwarty Blender z włączonym dodatkiem odbiera automatycznie, bez okna wyboru pliku.
W Edit Mode lub podczas renderowania import poczeka. W scenie powstaje kolekcja
**Fusion - nazwa dokumentu**; wcześniejsze obiekty i zaznaczenie pozostają bez zmian.

Przy pierwszym uruchomieniu dodatku Blender zapisuje ścieżkę swojego programu.
Jeżeli Fusion nie zna tej ścieżki, jednorazowo poprosi o wskazanie **blender.exe**.
Zamknięty Blender jest uruchamiany z odbiornikiem z paczki, również bez wcześniejszego
zapisania dodatku w preferencjach. Nie zmienia to startup file ani preferencji.
Jeśli Blender już działa, ale dodatek jest wyłączony, transfer pozostaje w kolejce:
włącz dodatek 0.2.2 w tym oknie. Most nie otwiera wtedy drugiego procesu.

Przy wielu procesach Blendera odbiera **pierwszy uruchomiony odbiornik 0.2.2**.
Wyłącz dodatek w nim i włącz go w docelowym procesie, jeśli chcesz zmienić odbiorcę.
Wielookienkowy Blender korzysta ze sceny bieżącego kontekstu aplikacji.

Status odbioru jest widoczny w panelu Fusion w Blenderze. Fusion zapisuje wynik
wysyłania w **Text Commands**, a błędy odbioru pokazuje komunikatem.

## Jednostki

Opcja **Ze sceny** oznacza **1 BU = Unit Scale × 1000 mm**, również dla Unit System=None.
Sama zmiana Length na milimetry zmienia wyświetlanie, nie skalę współrzędnych.
Przelicznik w panelu dotyczy **obu kierunków**, co umożliwia round-trip przy umownych mm.

| Ustawienie | Znaczenie |
|---|---|
| Ze sceny, Unit Scale = 1 | 1 BU = 1000 mm |
| Ze sceny, Unit Scale = 0.001 | 1 BU = 1 mm |
| 1 BU = 1 mm | Niezależnie od jednostek sceny |
| 1 BU = 1 cm / 1 m / 1 cal | 10 / 1000 / 25.4 mm |

Fusion używa wewnętrznie cm; współrzędne odczytane z jego siatek są przeliczane na mm.
Transformacje wystąpień komponentów są nakładane raz, przed zapisem STL. Mesh nie
jest upraszczany; quady/polygony są reprezentowane trójkątami wymaganymi przez STL.
Limit: 500 obiektów / 5 mln trójkątów na transfer. Duże modele mogą blokować UI podczas
przeliczania/odczytu; brak gwarancji płynnego importu tak dużych siatek w Fusion.

## Pliki i diagnostyka

Lokalne kolejki: `%LOCALAPPDATA%\BlenderFusionBridge\v2\fusion` i `...\v2\blender`.
W każdym kanale `jobs/<id>` zawiera STL, manifest i status. Zamknięcie programu nie
kasuje kolejki. Po awarii rozpoczęty import jest oznaczany jako przerwany i nie jest
automatycznie powtarzany. Sprawdź scenę przed ponownym wysłaniem.

Transfery pozostają na dysku. Usuwaj zakończone zadania przy zatrzymanych odbiornikach.
Nie usuwaj receiver.lock podczas pracy programów. Stara kolejka 0.1.0 (`jobs` bez `v2`)
nie jest odtwarzana w nowym odbiorniku. Nie usuwaj folderu AddIns z zainstalowanym kodem.
Most nie uruchamia serwera ani nie wysyła modeli przez internet; zapis/synchronizacja
projektów Fusion odbywa się zgodnie z ustawieniami samej aplikacji.

## Budowanie i testowanie

```powershell
python -m unittest discover -s tests -v
python tools/build.py
```

Paczka powstaje w `dist/`. Workflow GitHub Actions testuje Linux/Windows i buduje ZIP.
Źródła są w `blender/`, `fusion/`, `common/`; wspólne moduły i odbiornik startowy kopiuje
skrypt budujący. Nie instaluj niekompletnych folderów źródłowych.

Test rzeczywistego Blendera (własna ścieżka do programu):

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --factory-startup --python tools/blender_smoke.py
```

Test tworzy osobną scenę testową w procesie background. Nie otwiera projektów użytkownika.
Zgodność docelowa: Blender 3.6+ i bieżący Fusion na Windows 10/11.
[Próby stanowiskowe](docs/TESTING.md) · [Walidacja](docs/VALIDATION.md) · [Architektura](docs/ARCHITECTURE.md).
