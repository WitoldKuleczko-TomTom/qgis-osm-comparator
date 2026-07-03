# OSM Feature Comparator — QGIS Plugin

A QGIS 3.x plugin for comparing OpenStreetMap feature attributes by clicking directly on the map canvas.

---

## Features

### 🗺️ Click-to-select OSM features
Click anywhere on the canvas to query OpenStreetMap data at that location. The plugin uses the **Overpass API** with two complementary strategies:
- `around:10` — finds nearby roads, nodes and relations by measuring distance from geometry segments (not just nodes), so clicking in the middle of a road segment always works
- `is_in` + `pivot` — finds enclosing areas such as buildings, parks, forests, landuse zones and administrative boundaries

If multiple features are found at a click location, a **non-blocking selection dialog** opens — the canvas stays fully interactive (pan, zoom) while you browse the list.

### 🔦 Canvas highlighting
Every feature is highlighted on the canvas with a colour-coded rubber band as soon as it is selected. The colour matches the corresponding column header in the comparison table. While browsing the selection dialog, each list item is **previewed live** on the canvas so you can visually identify it before confirming.

| Feature type | Highlight style |
|---|---|
| Node | Circle icon |
| Way (open) | 3 px coloured line |
| Way (closed / polygon) | Semi-transparent fill + coloured border |
| Relation | Each member way drawn individually; bounding box as fallback |

Highlights are cleared when starting a new comparison or deactivating the plugin.

### 📊 Multi-feature comparison table
Compare **N features side-by-side** in a colour-coded tag table:

| Colour | Meaning |
|---|---|
| 🟢 Green | Identical value across all compared features |
| 🟡 Yellow | Key present in multiple features but values differ |
| Feature colour | Key unique to one feature |
| ⬜ Light grey | Key absent in this feature |

Use the **➕ Add feature** button to keep adding columns without resetting the comparison.

### 🕓 Version history comparison
Select the **same OSM element twice** to trigger a version history comparison. The plugin fetches the full edit history from the OSM REST API and displays the two most recent versions side-by-side:

| Colour | Meaning |
|---|---|
| 🟢 Green | Tag unchanged between versions |
| 🟡 Yellow | Tag value changed |
| 🔴 Pink | Tag added in the current version |
| 🔵 Blue | Tag removed in the current version |

Each column header shows: `v{N} · YYYY-MM-DD · by {user} · cs#{changeset}`

### ⚡ Non-blocking async requests
All HTTP requests run in a background `QThread` — QGIS never freezes while waiting for Overpass or OSM API responses.

---

## What's new in v0.6.1.1

**Live canvas preview in the feature selection dialog.**

When multiple OSM features are found at a click location, the selection dialog now highlights each list item on the canvas as you move through it — so you can see exactly which road, building or boundary you are about to select before pressing OK.

**What's new in v0.6.1** (base for this release):
- All selected features are highlighted on the canvas with `QgsRubberBand` after confirmation.
- Overpass query changed from `out tags` to `out geom tags` to retrieve geometry.
- Rubber-band colours match the comparison table column headers.

**What's new in v0.5.0:**
- Versioning scheme changed to SemVer (`0.5.0`).
- Author set to Witold Kuleczko.
- Fix: closing the history dialog now fully deactivates the plugin (v5 behaviour preserved).

---

## Installation

1. Download `osm_feature_comparator_v0_6_1_1.zip`
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**
3. Select the downloaded `.zip` file
4. The plugin appears in the **Web** menu and toolbar

---

## How to use

1. Click the **OSM Feature Comparator** toolbar button to activate
2. Click on the map → if multiple features found, a dialog opens:
   - Browse the list — each item is highlighted live on the canvas
   - Confirm with **OK** or double-click
3. Click on another location → select a second feature → comparison table opens
4. Use **➕ Add feature** to add more columns to the comparison
5. Use **🔄 New comparison** to reset and start over
6. Click the **same element again** to view its version history
7. Press **Close** on any dialog to fully deactivate the plugin

---

## Version history

| Version | Highlights | Notes |
|---|---|---|
| v1 | — | OSM API /map; does not detect roads clicked mid-segment |
| v2 | — | Overpass `around`; correct road detection |
| v3 | — | + `is_in`; matches OSM.org Query Features (PL) |
| v3_eng | — | English version of v3 |
| v4 | — | Multi-feature comparison + version history |
| v0.5.0 | — | SemVer; fix: Close on history dialog fully deactivates plugin |
| v0.6.1 | 🔦 Canvas highlights | `QgsRubberBand` after feature confirmation; `out geom tags` |
| **v0.6.1.1** | 🔦 Live preview | **Current** — preview in selector dialog; `highlight.py` shared module |

---

## Technical notes

- **Overpass query:** `out geom tags` — returns geometry (coordinates) alongside tags
- **Overpass radius:** 10 m (`DEFAULT_RADIUS_M` in `overpass_client.py`)
- **Rubber-band ownership:** all `QgsRubberBand` objects are owned by the plugin, never by dialogs — prevents orphaned canvas items on dialog garbage-collection
- **Non-blocking selector:** `QDialog.show()` + signals instead of `exec_()` keeps the canvas interactive during feature selection
- **Qt sorting bug:** `QTableWidget.setSortingEnabled(True)` must be called *after* all rows are populated
- **History API:** `GET https://api.openstreetmap.org/api/0.6/{type}/{id}/history.json`

---

## Requirements

- QGIS 3.0 or newer
- Internet access (Overpass API + OSM REST API)
