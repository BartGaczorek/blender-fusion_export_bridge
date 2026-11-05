# Walidacja 0.2.2 — 2026-11-05

- 45 testów: 44 zaliczonych na Linux/Python 3.12, 1 pominięty (blokada Windows).
- Nowe testy: aktywny dokument i zmiana celu; rollback tylko nowych ciał; istniejąca
  scena Blender; rollback częściowego importu Blender; mesh bez przeliczania;
  BRep/powierzchnie z normalną jakością; transformacja wystąpienia, jednostki i
  round-trip; zajęty odbiornik; otwarty Blender bez dodatku; start bez shell i duplikatów.
- Kompilacja Python i budowa obu dodatków oraz pakietu Windows: poprawne.
- Testy API aplikacji korzystają z atrap. Nie wykonano rzeczywistego testu 0.2.0
  w Fusion/Blender ani instalacji/startu procesów na Windows w środowisku wykonawczym.
- Użytkownik potwierdził działanie wersji 0.1.0 na swoim stanowisku. To nie stanowi
  potwierdzenia nowych funkcji 0.2.0.
- tools/blender_smoke.py rozszerzono o rzeczywisty import do istniejącej sceny i rollback;
  wymaga uruchomienia w zainstalowanym Blenderze.

Lista prób przed wdrożeniem: [TESTING.md](TESTING.md).

Poprawka 0.2.1: test odtworzenia starego modułu bez channel_root, przeładowania
zależności oraz powtarzalnego sprzątania po częściowej rejestracji.

Poprawka 0.2.2: zgodność ID komendy z kontraktem Autodesk, przypięcie przycisku,
sprzątanie nieudanej rejestracji i ponowna rejestracja po błędzie.
