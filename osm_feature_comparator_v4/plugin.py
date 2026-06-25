# -*- coding: utf-8 -*-
import os

from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from qgis.core import Qgis

from .map_tool              import OSMClickTool
from .overpass_client       import get_feature_display_name
from .feature_selector_dialog import FeatureSelectorDialog
from .comparison_dialog     import ComparisonDialog
from .history_dialog        import HistoryComparisonDialog
from .worker                import FetchWorker, HistoryFetchWorker


class OSMFeatureComparator:
    """Main plugin class for OSM Feature Comparator v4."""

    PLUGIN_NAME = "OSM Feature Comparator"

    def __init__(self, iface):
        self.iface  = iface
        self.canvas = iface.mapCanvas()
        self.map_tool = None
        self.action   = None

        self._features = []     # accumulated list of selected OSM feature dicts
        self._worker   = None   # active QThread reference
        self._loading  = False  # guard: block clicks while a request is in flight

    # ── QGIS lifecycle ───────────────────────────────────────────────────────

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.svg")
        self.action = QAction(
            QIcon(icon_path),
            self.PLUGIN_NAME,
            self.iface.mainWindow(),
        )
        self.action.setCheckable(True)
        self.action.setToolTip(
            "OSM Feature Comparator v4\n"
            "Click on the map to compare OpenStreetMap features.\n"
            "Select the same element again to view its version history."
        )
        self.action.triggered.connect(self._on_action_triggered)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToWebMenu(self.PLUGIN_NAME, self.action)

    def unload(self):
        self._abort_worker()
        self._deactivate_tool()
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginWebMenu(self.PLUGIN_NAME, self.action)

    # ── Tool lifecycle ───────────────────────────────────────────────────────

    def _on_action_triggered(self, checked):
        if checked:
            self._abort_worker()   # cancel any in-flight request
            self._features = []
            self._activate_tool()
        else:
            self._abort_worker()
            self._deactivate_tool()

    def _activate_tool(self):
        """Attach the click tool; keep _features intact (caller clears if needed)."""
        self._loading = False
        self.map_tool = OSMClickTool(self.canvas)
        self.map_tool.clicked.connect(self._on_canvas_clicked)
        self.map_tool.deactivated.connect(self._on_tool_deactivated)
        self.canvas.setMapTool(self.map_tool)

        next_num = len(self._features) + 1
        self._push_info(
            f"Click on the map to select <b>Feature {next_num}</b> from OpenStreetMap."
        )

    def _deactivate_tool(self):
        if self.map_tool is not None:
            try:
                self.map_tool.clicked.disconnect(self._on_canvas_clicked)
                self.map_tool.deactivated.disconnect(self._on_tool_deactivated)
            except Exception:
                pass
            self.canvas.unsetMapTool(self.map_tool)
            self.map_tool = None
        self._set_action_checked(False)

    def _on_tool_deactivated(self):
        """Called when QGIS switches away from this map tool."""
        self._set_action_checked(False)
        self.map_tool = None

    def _set_action_checked(self, state: bool):
        if self.action is not None:
            self.action.setChecked(state)

    def _abort_worker(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        self._worker  = None
        self._loading = False

    # ── Canvas click → Overpass fetch ────────────────────────────────────────

    def _on_canvas_clicked(self, lat, lon):
        if self._loading:
            self._push_info("Loading… please wait.")
            return

        click_number  = len(self._features) + 1
        self._loading = True
        self._push_info(
            f"Fetching OSM data for <b>Feature {click_number}</b> "
            f"({lat:.5f}, {lon:.5f})…"
        )

        self._worker = FetchWorker(lat, lon)
        self._worker.finished.connect(
            lambda features: self._on_features_loaded(features, click_number)
        )
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_features_loaded(self, features, click_number):
        self._loading = False

        if not features:
            self._push_warning(
                "No OSM features with tags found at this location (10 m buffer). "
                "Try clicking closer to the centre of a feature."
            )
            return

        selected = self._select_feature(features, click_number)
        if selected is None:
            return

        # ── Duplicate detection ───────────────────────────────────────────────
        duplicate = next(
            (
                f for f in self._features
                if f.get("type") == selected.get("type")
                and f.get("id")   == selected.get("id")
            ),
            None,
        )
        if duplicate is not None:
            self._deactivate_tool()
            self._fetch_history(selected)
            return

        # ── Normal: add feature, maybe open comparison ────────────────────────
        self._features.append(selected)
        name = get_feature_display_name(selected)

        if len(self._features) == 1:
            self._push_info(
                f"<b>Feature 1</b> selected: {name}. "
                "Now click on the map to select <b>Feature 2</b>."
            )
        else:
            self._deactivate_tool()
            self._show_comparison()

    def _on_fetch_error(self, message):
        self._loading = False
        self._push_error(f"OSM API error: {message}")

    def _select_feature(self, features, click_number):
        """Return the chosen feature — directly if unique, or via selection dialog."""
        if len(features) == 1:
            return features[0]
        dialog = FeatureSelectorDialog(
            features, click_number=click_number, parent=self.iface.mainWindow()
        )
        if dialog.exec_() == FeatureSelectorDialog.Accepted:
            return dialog.selected_feature
        return None

    # ── Comparison dialog ────────────────────────────────────────────────────

    def _show_comparison(self):
        dialog = ComparisonDialog(self._features, parent=self.iface.mainWindow())
        dialog.add_feature.connect(self._on_add_feature)
        dialog.compare_again.connect(self._on_compare_again)
        dialog.exec_()

    def _on_add_feature(self):
        """User pressed '➕ Add feature' — activate tool to pick one more feature."""
        self._set_action_checked(True)
        self._activate_tool()

    def _on_compare_again(self):
        """User pressed '🔄 New comparison' — reset and start fresh."""
        self._features = []
        self._set_action_checked(True)
        self._activate_tool()

    # ── Version history ──────────────────────────────────────────────────────

    def _fetch_history(self, feature):
        """Fetch OSM version history for a feature (same element was selected again)."""
        osm_type      = feature.get("type", "way")
        osm_id        = feature.get("id",   0)
        self._loading = True
        self._push_info(
            f"Fetching version history for "
            f"{osm_type.capitalize()} #{osm_id}…"
        )
        self._worker = HistoryFetchWorker(osm_type, osm_id)
        self._worker.finished.connect(self._on_history_loaded)
        self._worker.error.connect(self._on_history_fetch_error)
        self._worker.start()

    def _on_history_fetch_error(self, message):
        self._loading = False
        self._push_error(f"Could not load version history: {message}")
        self._resume_after_history()

    def _on_history_loaded(self, versions):
        self._loading = False

        # Need at least 2 versions to compare
        if len(versions) < 2:
            self._push_warning(
                "This element has only one version in OSM — no history to compare."
            )
            self._resume_after_history()
            return

        current_v  = versions[-1]
        previous_v = versions[-2]

        dialog = HistoryComparisonDialog(
            current_v, previous_v, parent=self.iface.mainWindow()
        )
        dialog.exec_()

        self._resume_after_history()

    def _resume_after_history(self):
        """After the history dialog closes, re-show comparison or shut down the tool."""
        if len(self._features) >= 2:
            # User was adding a feature and selected a duplicate → re-show comparison
            self._show_comparison()
        else:
            # User selected the same element twice (history view) → close completely
            self._features = []
            self._deactivate_tool()

    # ── Messages ─────────────────────────────────────────────────────────────

    def _push_info(self, msg):
        self.iface.messageBar().pushMessage(
            self.PLUGIN_NAME, msg, level=Qgis.Info, duration=6
        )

    def _push_warning(self, msg):
        self.iface.messageBar().pushMessage(
            self.PLUGIN_NAME, msg, level=Qgis.Warning, duration=8
        )

    def _push_error(self, msg):
        self.iface.messageBar().pushMessage(
            self.PLUGIN_NAME, msg, level=Qgis.Critical, duration=12
        )
