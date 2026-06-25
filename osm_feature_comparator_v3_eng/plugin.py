# -*- coding: utf-8 -*-
import os

from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from qgis.core import Qgis

from .map_tool import OSMClickTool
from .overpass_client import get_feature_display_name
from .feature_selector_dialog import FeatureSelectorDialog
from .comparison_dialog import ComparisonDialog
from .worker import FetchWorker


class OSMFeatureComparator:
    """Main plugin class for OSM Feature Comparator."""

    PLUGIN_NAME = "OSM Feature Comparator"

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.map_tool = None
        self.action = None
        self._feature1 = None
        self._feature2 = None
        self._worker = None    # reference to the active HTTP thread
        self._loading = False  # guard against double-clicks while loading

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
            "OSM Feature Comparator\n"
            "Click twice on the map to compare two OpenStreetMap features."
        )
        self.action.triggered.connect(self._on_action_triggered)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToWebMenu(self.PLUGIN_NAME, self.action)

    def unload(self):
        self._abort_worker()
        self._deactivate_tool()
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginWebMenu(self.PLUGIN_NAME, self.action)

    # ── Tool handling ────────────────────────────────────────────────────────

    def _on_action_triggered(self, checked):
        if checked:
            self._activate_tool()
        else:
            self._deactivate_tool()

    def _activate_tool(self):
        """Start the click tool and reset selection state."""
        self._feature1 = None
        self._feature2 = None
        self._loading = False

        self.map_tool = OSMClickTool(self.canvas)
        self.map_tool.clicked.connect(self._on_canvas_clicked)
        self.map_tool.deactivated.connect(self._on_tool_deactivated)
        self.canvas.setMapTool(self.map_tool)

        self._push_info("Click on the map to select <b>Feature 1</b> from OpenStreetMap.")

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
        """Called when QGIS switches to another map tool."""
        self._set_action_checked(False)
        self.map_tool = None

    def _set_action_checked(self, state: bool):
        if self.action is not None:
            self.action.setChecked(state)

    def _abort_worker(self):
        """Stop the active HTTP thread if running."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        self._worker = None
        self._loading = False

    # ── Click logic (asynchronous) ───────────────────────────────────────────

    def _on_canvas_clicked(self, lat, lon):
        if self._loading:
            self._push_info("Loading… please wait.")
            return

        click_number = 1 if self._feature1 is None else 2
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

        if click_number == 1:
            self._feature1 = selected
            name = get_feature_display_name(selected)
            self._push_info(
                f"<b>Feature 1</b> selected: {name}. "
                "Now click on the map to select <b>Feature 2</b>."
            )
        else:
            self._feature2 = selected
            self._deactivate_tool()
            self._show_comparison()

    def _on_fetch_error(self, message):
        self._loading = False
        self._push_error(f"OSM API connection error: {message}")

    def _select_feature(self, features, click_number):
        """Return the selected feature — directly if only one, or via dialog."""
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
        dialog = ComparisonDialog(
            self._feature1, self._feature2, parent=self.iface.mainWindow()
        )
        dialog.compare_again.connect(self._on_compare_again)
        dialog.exec_()

    def _on_compare_again(self):
        """User clicked 'New comparison' — reactivate the tool."""
        self._set_action_checked(True)
        self._activate_tool()

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
