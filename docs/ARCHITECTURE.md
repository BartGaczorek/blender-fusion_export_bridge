# Protokół 2 — dwa kierunki

Oddzielne kanały v2/fusion oraz v2/blender izolują kolejki, statusy i blokady.
Odbiornik 0.1.0 nie może przypadkowo odebrać transferu do aktywnego dokumentu jako
nowego dokumentu. Manifest w obu kanałach zawiera jednostki mm, XYZ_Z_UP, SHA-256,
liczbę trójkątów, nazwę obiektu i bezpieczną względną nazwę pliku STL.

Ready -> processing -> finished. Publikacja następuje po zamknięciu wszystkich STL.
Awaria po przejęciu transferu nie powoduje replay. Nie gwarantujemy exactly-once
pomiędzy API aplikacji a systemem plików; status uncertain wymaga sprawdzenia ręcznego.

Fusion publikuje efemeryczny token aktywnego dokumentu. Blender dołącza token do
transferu ACTIVE. Odbiornik sprawdza aktualny dokument na wątku UI, zanim zacznie import.
Przełączenie dokumentu unieważnia token. Import ACTIVE nigdy nie zamyka dokumentu;
rollback obejmuje wyłącznie nowe ciała zwrócone przez meshBodies.add. W wariancie NEW
rollback zamyka tylko utworzony dokument. Import do root component, bez zmiany aktywacji.

Fusion MeshBody.displayMesh dostarcza istniejące trójkąty. BRepBody.meshManager używa
TriangleMeshCalculator z presetem NormalQualityTriangleMesh; obejmuje również otwarte
ciała powierzchniowe. Odczyt z nativeObject plus transform2 assemblyContext zapewnia
wspólne współrzędne świata bez podwójnego nakładania transformacji. STL zapisuje mm.

Fusion uruchamia API modelowania na CustomEvent na głównym wątku; wątek IO tylko
publikuje heartbeat i wywołuje fireCustomEvent. Przycisk wysyłania ma tylko pole wyboru
ciał i potwierdzenie, bez parametrów triangulacji. Handler destroy zwalnia referencje.

Blender używa persistent app timer na głównym wątku i API danych zamiast operatora
importu STL. Import jest w bieżącej scenie do nowej kolekcji, z rollback obiektów,
meshy i kolekcji. Tryb edycji i render odraczają import. Dwa programy nie współdzielą
interpreterów ani modułów. Dane nie trafiają do sieci.

Blender przechowuje ścieżkę programu; Fusion używa osobnych argumentów subprocess
(shell=False). Przed startem sprawdza blokadę odbiornika, proces blender.exe i krótki
znacznik uruchamiania. Zajęty odbiornik trzyma blokadę nawet przy nieaktualnym heartbeat.
Bootstrap zawiera ten sam dodatek co ZIP, bez nadpisywania preferencji i startup file.

Źródła API:
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshBody.htm
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TriangleMeshCalculator.htm
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_TriangleMesh_nodeCoordinates.htm
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_MeshBodies_add.htm
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/CustomEventSample_Sample.htm
- https://docs.blender.org/api/current/bpy.app.timers.html
