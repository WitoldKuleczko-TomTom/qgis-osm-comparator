# OSM Feature Comparator — QGIS Plugin

A QGIS 3.x plugin for comparing OpenStreetMap feature attributes by clicking directly on the map canvas.

---

## Features

### 🗺️ Click-to-select OSM features
Click anywhere on the canvas to query OpenStreetMap data at that location. The plugin uses the **Overpass API** with two complementary strategies:
- `around:10` — finds nearby roads, nodes and relations by measuring distance from geometry segments (not just nodes), so clicking in the middle of a road segment always works
- `is_in` + `pivot` — finds enclosing areas such as buildings, parks, forests, landuse zones and administrative boundaries

If multiple features are found at a click location, a selection dialog lets you pick the right one.

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

## What's new in v5

**Fix: closing the history dialog now fully deactivates the plugin.**

In v4, after viewing the version history of an element (by selecting the same feature twice), pressing **Close** left the plugin active and waiting for another canvas click. In v5, closing the history dialog completely deactivates the map tool and resets the plugin state — consistent with the user's intent to finish the comparison.

---

## Installation

1. Download `osm_feature_comparator_v5.zip`
2. In QGIS: **Plugins → Manage and Install Plugins → Install from ZIP**
3. Select the downloaded `.zip` file
4. The plugin appears in the **Web** menu and toolbar

---

## How to use

1. Click the **OSM Feature Comparator** toolbar button to activate
2. Click on the map → select a feature from the dialog (if multiple results)
3. Click on another location → select a second feature → comparison table opens
4. Use **➕ Add feature** to add more columns to the comparison
5. Use **🔄 New comparison** to reset and start over
6. Click the **same element again** to view its version history
7. Press **Close** on any dialog to fully deactivate the plugin

---

## Version history

| Version | API | is_in | Language | Notes |
|---|---|---|---|---|
| v1 | OSM API /map | ❌ | PL | Does not detect roads clicked mid-segment |
| v2 | Overpass around | ❌ | PL | Correct road detection |
| v3 | Overpass around + is_in | ✅ | PL | Matches OSM.org Query Features behaviour |
| v3_eng | Overpass around + is_in | ✅ | EN | English version of v3 |
| v4 | Overpass + OSM REST history | ✅ | EN | Multi-feature comparison + version history |
| **v5** | Overpass + OSM REST history | ✅ | EN | **Fix: Close on history dialog fully deactivates plugin** |

---

## Technical notes

- **Overpass radius:** 10 m (`DEFAULT_RADIUS_M` in `overpass_client.py`)
- **Qt sorting bug:** `QTableWidget.setSortingEnabled(True)` must be called *after* all rows are populated — enabling it during `setItem()` causes Qt to shift rows and leave empty cells
- **Async guard:** `_loading = True` blocks double-clicks while a request is in flight
- **History API:** `GET https://api.openstreetmap.org/api/0.6/{type}/{id}/history.json`

---

## Requirements

- QGIS 3.0 or newer
- Internet access (Overpass API + OSM REST API)
