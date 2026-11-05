# Wyniki weryfikacji — 2026-11-05

Wersja 0.1.0. Środowisko: Linux, Python 3.12.14.

- 25 testów jednostkowych: **24 zakończone powodzeniem**, **1 pominięty**
  (rzeczywista blokada msvcrt dostępna tylko na Windows).
- Kompilacja Python: poprawna.
- Pakiet ZIP: poprawna integralność, składnia plików Python, struktura wewnętrznego
  ZIP Blendera, manifest Windows Fusion, zgodność obu kopii protokołu.
- Nie przeprowadzono testu instalacji w Windows ani importu w rzeczywistym Fusion.
- Nie uruchomiono testu rzeczywistego API Blender; skrypt do tej próby jest dołączony.
- Testy adapterów aplikacji używają atrap API. Nie potwierdzają integracji end-to-end.


Pełne źródła, instrukcja instalacji i workflow testów znajdują się w repozytorium.
Paczka Windows jest budowana poleceniem `python tools/build.py` lub przez GitHub
Actions. Test stanowiskowy opisano w [TESTING.md](TESTING.md).
