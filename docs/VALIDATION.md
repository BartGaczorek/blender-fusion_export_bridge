# Walidacja 0.2.0 — 2026-11-05

- 39 testów: 38 zaliczonych na Linux/Python 3.12, 1 pominięty (blokada Windows).
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
