# OSM Feature Comparator — QGIS Plugin — Notatki projektowe

## Lokalizacja plików
```
D:\COPA\QGIS_plugin\
├── osm_feature_comparator\          ← v1 (OSM API /map, async)
├── osm_feature_comparator_v2\       ← v2 (Overpass around, async)
├── osm_feature_comparator_v3\       ← v3 PL (Overpass around + is_in)
├── osm_feature_comparator_v3_eng\   ← v3 ENG (Overpass around + is_in)
├── osm_feature_comparator_v4\       ← v4 ENG (multi-feature + historia wersji)
├── osm_feature_comparator_v5\       ← v5 ENG (fix: Close historii = pełne wyłączenie pluginu) ← AKTUALNA
├── osm_feature_comparator_v1.zip
├── osm_feature_comparator_v2.zip
├── osm_feature_comparator_v3.zip
├── osm_feature_comparator_v3_eng.zip
└── osm_feature_comparator_v5.zip   ← do instalacji w QGIS
```

## Instalacja w QGIS
**Plugins → Manage and Install Plugins → Install from ZIP**  
Wskaż odpowiedni plik `.zip`.

---

## Opis pluginu

Plugin do QGIS 3.40.4 umożliwiający porównanie atrybutów (tagów) dwóch obiektów OpenStreetMap przez kliknięcie na canvie.

### Przepływ działania
1. Użytkownik aktywuje plugin z toolbara / menu Web
2. **Klik 1** → async zapytanie Overpass → wybór Feature 1 (dialog jeśli kilka wyników)
3. **Klik 2** → async zapytanie Overpass → wybór Feature 2 → otwarcie okna porównania
4. Okno porównania wyświetla tabelę tagów z kolorowaniem
5. Przycisk "New comparison / Nowe porównanie" → reset i ponowny wybór

---

## Struktura plików pluginu

| Plik | Rola |
|---|---|
| `__init__.py` | Entry point QGIS (`classFactory`) |
| `metadata.txt` | Metadane pluginu (name, version, description) |
| `plugin.py` | Główna klasa `OSMFeatureComparator` — lifecycle, toolbar, logika |
| `map_tool.py` | `OSMClickTool(QgsMapTool)` — kliknięcia z transformacją CRS→WGS84 |
| `overpass_client.py` | Zapytania do Overpass API + `get_feature_display_name()` |
| `worker.py` | `FetchWorker(QThread)` + `HistoryFetchWorker(QThread)` — async HTTP |
| `feature_selector_dialog.py` | Dialog wyboru gdy kilka obiektów w pobliżu |
| `comparison_dialog.py` | Tabela porównania N featureów z kolorowaniem i statystykami |
| `history_dialog.py` | *(v4 NEW)* `HistoryComparisonDialog` — porównanie dwóch wersji elementu |
| `osm_history_client.py` | *(v4 NEW)* Klient OSM REST API — `query_feature_history()` |
| `resources/icon.svg` | Ikona toolbara |

---

## Kluczowe decyzje techniczne

### 1. Overpass API zamiast OSM API /map
- **OSM API `/api/0.6/map?bbox=...`** — szybki, ale zwraca tylko way'e których **węzły** są w bbox.  
  Problem: kliknięcie w środek segmentu drogi (między węzłami oddalonymi >10m) nic nie zwraca.
- **Overpass API `around:R`** — oblicza odległość od **geometrii segmentów** (nie tylko węzłów).  
  Zawsze znajdzie drogę klikniętą gdziekolwiek wzdłuż linii. ✅

### 2. Zapytanie Overpass (v3) — wzorowane na OSM.org Query Features
```overpass
[out:json][timeout:25];
is_in(LAT,LON)->.enclosing;
(
  node(around:10,LAT,LON);
  way(around:10,LAT,LON);
  relation(around:10,LAT,LON);
  way(pivot.enclosing);
  relation(pivot.enclosing);
);
out tags;
```

**Dlaczego dwa typy zapytań:**
- `around:10` — obiekty w pobliżu krawędzi (drogi, węzły, relacje)
- `is_in` + `pivot` — obszary **okalające** punkt (budynki, parki, lasy, landuse, granice admin.)  
  Kliknięcie wewnątrz dużego poligonu — `around` go nie znajdzie, `is_in` zawsze tak.

### 3. Async HTTP — QThread
Zapytanie HTTP uruchamiane w `FetchWorker(QThread)` — QGIS nie freezuje podczas oczekiwania.  
Guard `self._loading = True` blokuje podwójne kliknięcia podczas ładowania.

### 4. Bug sortowania Qt
`QTableWidget.setSortingEnabled(True)` musi być wywołane **PO** zapełnieniu wszystkich wierszy.  
Jeśli sorting jest aktywny podczas `setItem()`, Qt przesuwa wiersze → puste komórki.

### 5. Promień bufora
`DEFAULT_RADIUS_M = 10` w `overpass_client.py`

---

## Historia wersji

| Wersja | API | Async | is_in | Język | Uwagi |
|---|---|---|---|---|---|
| v1 | OSM API /map | ✅ QThread | ❌ | PL | Nie wykrywa dróg klikanych w środku segmentu |
| v2 | Overpass around | ✅ QThread | ❌ | PL | Poprawne wykrywanie dróg |
| v3 | Overpass around + is_in | ✅ QThread | ✅ | PL | Jak OSM.org Query Features |
| v3_eng | Overpass around + is_in | ✅ QThread | ✅ | EN | Wersja angielska v3 |
| v4 | Overpass around + is_in + OSM REST history | ✅ QThread | ✅ | EN | multi-feature + historia |
| v5 | Overpass around + is_in + OSM REST history | ✅ QThread | ✅ | EN | **Aktualna wersja** — fix: Close historii = pełne wyłączenie pluginu |

---

## Kolorowanie w oknie porównania

### v1–v3: Dwa featureу

| Kolor | Hex | Znaczenie |
|---|---|---|
| 🟢 Zielony | `#A8D5A2` | Identyczna wartość w obu obiektach |
| 🟡 Żółty | `#FFE082` | Klucz w obu, ale wartości różne |
| 🔴 Różowy | `#FFCDD2` | Klucz tylko w Feature 1 |
| 🔵 Niebieski | `#BBDEFB` | Klucz tylko w Feature 2 |

### v4: N featureów (ComparisonDialog)

| Kolor | Hex | Znaczenie |
|---|---|---|
| 🟢 Zielony | `#A8D5A2` | Identyczna wartość we wszystkich featureach |
| 🟡 Żółty | `#FFE082` | Klucz w ≥2 featureach, wartości różne |
| Kolor feature | `FEATURE_HEADER_COLORS[i]` | Klucz tylko w jednym feature (unikalny) |
| ⬜ Szary | `#F0F0F0` | Klucz nieobecny w tym feature |

### v4: Historia wersji (HistoryComparisonDialog)

| Kolor | Hex | Znaczenie |
|---|---|---|
| 🟢 Zielony | `#A8D5A2` | Tag niezmieniony między wersjami |
| 🟡 Żółty | `#FFE082` | Wartość tagu zmieniona |
| 🔴 Różowy | `#FFCDD2` | Tag dodany w bieżącej wersji |
| 🔵 Niebieski | `#BBDEFB` | Tag usunięty w bieżącej wersji |

---

## Nowe funkcje v4

### 1. Porównanie wielu featureów (N kolumn)

Przycisk **➕ Add feature** w oknie porównania:
1. Zamyka dialog (sygnał `add_feature`) → `plugin._on_add_feature()` → aktywuje map tool
2. Użytkownik klika kolejny element → Overpass → wybór → dodanie do `_features[]`
3. Nowy `ComparisonDialog` ze wszystkimi featurami otwiera się ponownie
4. Tabela dynamicznie ma `N+1` kolumn (Key + Feature 1..N)

Paleta kolorów nagłówków (cyklicznie):
```python
FEATURE_HEADER_COLORS = [
    "#FFCDD2",  # F1 – różowy
    "#BBDEFB",  # F2 – niebieski
    "#C8E6C9",  # F3 – zielony
    "#FFF9C4",  # F4 – żółty
    "#E1BEE7",  # F5 – lawendowy
    "#FFE0B2",  # F6 – pomarańczowy
]
```

### 2. Historia wersji (duplikat elementu)

Gdy użytkownik wybierze element już obecny w porównaniu (ten sam `type` + `id`):
1. `plugin._on_features_loaded()` wykrywa duplikat (porównanie `type+id`)
2. Deaktywuje tool, wywołuje `_fetch_history(selected)`
3. `HistoryFetchWorker(QThread)` pobiera: `GET https://api.openstreetmap.org/api/0.6/{type}/{id}/history.json`
4. `_on_history_loaded()` → `HistoryComparisonDialog` z ostatnimi 2 wersjami (`versions[-1]` vs `versions[-2]`)
5. Nagłówek zawiera: `v{N} · YYYY-MM-DD · by {user} · cs#{changeset}`
6. Po zamknięciu: `_resume_after_history()` — wraca do porównania (≥2 featureów) lub reaktywuje tool (1 feature)

### 3. Poprawki robustności (v4 vs v3_eng)

| Problem | Rozwiązanie |
|---|---|
| Przerwanie w trakcie pobierania | `_abort_worker()` wywoływany przy zmianie stanu toolbara |
| Błąd pobierania historii bez powrotu do UI | Dedykowany `_on_history_fetch_error()` → `_resume_after_history()` |
| Martwe wyniki po anulowaniu | `_abort_worker()` przed każdym nowym sessionem |

---

## Znane problemy / TODO

- [ ] Overpass API może być wolny przy pierwszym użyciu (cold start serwera)
- [ ] Brak obsługi offline / brak połączenia z internetem (tylko komunikat błędu)
- [ ] Brak możliwości zmiany promienia bufora z poziomu UI
- [ ] Typ obiektu: `node→Node`, `way→Way`, `relation→Relation`
- [ ] Priorytet nazw: `name`, `name:en`, `ref`, `highway`, `amenity`, ...
- [ ] OSM history API może zwrócić duże odpowiedzi dla popularnych elementów (setki wersji)
- [ ] Brak podglądu geometrii zmian między wersjami (tylko tagi)

---

## Testowane koordynaty

| Koordynaty | OSM ID | Typ | Uwaga |
|---|---|---|---|
| 51.96685933, 20.12996516 | way/1415213595 | way | Wymagało is_in lub around na segmencie |
| 51.96900898, 20.13627291 | way/1305885201 | way | j.w. |
| 51.968173, 20.137749 | — | — | Porównanie z OSM.org Query Features |
