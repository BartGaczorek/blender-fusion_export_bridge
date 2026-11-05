# Architektura v1

Blender i Fusion używają osobnych interpreterów. Transfer używa binarnego STL na
obiekt i manifestu JSON. Nie wymaga globalnego Pythona, serwera ani portu TCP.

1. Blender odczytuje `evaluated_get(...).to_mesh()` z modyfikatorami viewport.
2. Eksporter trianguluje kopię, zapisuje world-space w mm, odwraca winding przy
   ujemnym wyznaczniku macierzy. Nie zmienia modelu źródłowego.
3. Pliki mają nazwy ASCII `mesh_NNNN.stl`; oryginalne nazwy są w UTF-8 JSON.
4. Po zamknięciu STL atomowo publikowany jest `ready.json`.
5. Jeden odbiornik (`msvcrt.locking`) obserwuje kolejkę. Wątek IO używa tylko
   dozwolonego `Application.fireCustomEvent`; pozostałe API Fusion działa na wątku UI.
6. CustomEvent czeka na `SelectCommand`/brak polecenia, przejmuje znacznik jako
   `processing.json`, sprawdza manifest, ścieżki, rozmiary, liczbę trójkątów i SHA-256.
7. Nowy dokument Design otrzymuje siatki przez `meshBodies.add(path, MillimeterMeshUnit)`.
   Bez wyłączania historii poprzednich dokumentów, konwersji BRep i API preview.
8. Wynik `done`/`error` jest zapisany przed zmianą znacznika na `finished.json`.

Dokument jest zawsze nowy, więc zmiana aktywnego projektu w trakcie oczekiwania nie
kieruje importu do przypadkowego projektu. Błąd zamyka tylko ten nowy dokument.
Brak możliwości zamknięcia częściowego dokumentu jest jawnie zgłaszany.

Każdy eksport ma UUID. Niekompletne eksporty są niewidoczne dla odbiornika. Rozpoczęty
import po awarii staje się `uncertain` i nie jest ponawiany. Nie deklarujemy „exactly
once” pomiędzy Fusion a systemem plików: awaria po imporcie, przed zapisaniem statusu,
wymaga ręcznego sprawdzenia. Pliki transferów nie są automatycznie kasowane.

Metadane nie mogą zawierać dowolnych ścieżek ani kodu. Kolejka jest prywatna dla konta
Windows, ale nie stanowi granicy bezpieczeństwa przed innymi procesami tego samego
użytkownika. Nie należy umieszczać jej na dysku sieciowym.

## Sprawdzone źródła API

- [MeshBodies.add](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshBodies_add.htm)
- [MeshUnits](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshUnits.htm)
- [CustomEvent](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CustomEventSample_Sample.htm)
- [Documents.add](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/core_Documents_add.htm)
- [Manifest](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm)
- [Blender evaluated geometry](https://docs.blender.org/api/current/bpy.types.Depsgraph.html)

Documents.add nie może być wykonane wewnątrz transakcji Command.execute, dlatego
import wykonuje CustomEvent z kontrolą activeCommand, a nie toolbar command.
