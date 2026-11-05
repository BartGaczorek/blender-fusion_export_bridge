# Walidacja i test stanowiskowy

Środowisko przygotowania: Python na Linux, bez Blendera, Fusion ani Windows.
Testy jednostkowe nie potwierdzają pełnej zgodności z instalacją użytkownika.
To wersja 0.2.0 do testu stanowiskowego, nie zweryfikowane wydanie produkcyjne.

## Automatycznie

`python -m unittest discover -s tests -v` — format STL, jednostki, world-space,
ujemna skala, nazwy, wiele obiektów, błędy eksportu, integralność danych, kolejka,
przerwany import, odraczanie aktywnych poleceń, rollback nowego dokumentu.
Test rzeczywistej blokady Windows jest pomijany na innych systemach.

`python tools/build.py` buduje zestaw Windows, ZIP Blender i odbiornik Fusion.
`tools/blender_smoke.py` sprawdza rzeczywiste API Blendera: rejestrację dodatku,
eksport kostki z przesunięciem, ujemną skalą, rotacją i modyfikatorem bevel.
Wymaga zainstalowanego Blendera; uruchomienie opisano w README.

## Pierwsza próba na Windows

| Próba | Oczekiwany wynik |
|---|---|
| Instalacja dodatków, restart Fusion | Odbiornik startuje automatycznie; panel pokazuje „Fusion: gotowy”. |
| Kostka 20 × 30 × 40 mm, „Ze sceny” | Nowy dokument; pomiar 20 × 30 × 40 mm. |
| Przesunięcie i obrót 90° wokół Z | Zgodne położenie i orientacja; bez zamiany Y/Z. |
| Dwa obiekty z polskimi nazwami | Dwie osobne siatki z nazwami i zachowanym odstępem. |
| Bevel/Subdivision, Scale X = -1 | Wynik jak w viewport; modyfikatory nadal w Blenderze. |
| Inny niezapisany projekt w Fusion | Pozostaje niezmieniony; import tworzy nowy dokument. |
| Aktywne Extrude w Fusion | Import czeka na koniec/anulowanie polecenia. |
| Wyłączony odbiornik, dwa eksporty, uruchomienie | Dwa dokumenty, po jednym imporcie każdego eksportu. |
| Restart po zakończonym transferze | Brak powtórnego importu. |
| Edit Mode, kamera, pusta siatka | Przycisk niedostępny lub błąd; brak częściowego transferu. |
| Opcjonalny skrót przy zamkniętym Fusion | Start aplikacji i import po uruchomieniu odbiornika. |

Zapisz wersje Blender/Fusion oraz wyniki pomiarów. Przy błędzie zachowaj status.json
i receiver.log. W miarę możliwości odtwórz błąd kostką zamiast udostępniać właściwy model.
Testy awarii wykonuj na dokumentach testowych; nie zamykaj na siłę Fusion z otwartymi,
niezapisanymi projektami produkcyjnymi.

## Nowe próby 0.2.0

1. Blender → ACTIVE: otwórz Fusion z istniejącymi ciałami, wyślij kostkę. Dokument
   i stare ciała pozostają, nowa siatka ma właściwy wymiar i położenie.
2. Otwórz polecenie Extrude, wyślij ACTIVE, przełącz dokument zanim kolejka ruszy:
   odmowa zamiast importu do niewłaściwego dokumentu. Wyślij ponownie do właściwego.
3. Fusion → Blender: mesh z przesuniętego/obróconego wystąpienia komponentu;
   ta sama liczba trójkątów i właściwe położenie w Blenderze.
4. Wyślij BRep kuli oraz otwartą powierzchnię. Bez ustawień siatkowania, dwie osobne
   siatki, zgodne wymiary; powierzchnia nie jest sztucznie domykana.
5. Otwarty Blender: import do bieżącej sceny, istniejące obiekty bez zmian.
6. Blender w Edit Mode / podczas renderu: poczekaj, nie uruchamiaj drugiego procesu.
7. Zamknij Blender, wyślij z Fusion: nowe okno, import, bez utraty startup file.
8. Blender działa z wyłączonym dodatkiem: brak drugiego okna; kolejka odbierana po włączeniu 0.2.0.
9. Dwa eksporty podczas startu Blendera: jeden proces, dwa importy.
10. W obu kierunkach round-trip kostki 20 × 30 × 40 mm w trybach Ze sceny oraz 1 BU=1 mm.
