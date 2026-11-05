# Walidacja i test stanowiskowy

Środowisko przygotowania: Python na Linux, bez Blendera, Fusion ani Windows.
Testy jednostkowe nie potwierdzają pełnej zgodności z instalacją użytkownika.
To wersja 0.1.0 do testu stanowiskowego, nie zweryfikowane wydanie produkcyjne.

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
