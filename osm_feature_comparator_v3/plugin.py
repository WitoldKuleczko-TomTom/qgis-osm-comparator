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
    """Główna klasa pluginu OSM Feature Comparator."""

    PLUGIN_NAME = "OSM Feature Comparator"

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.map_tool = None
        self.action = None
        self._feature1 = None
        self._feature2 = None
        self._worker = None       # referencja do aktywnego wątku HTTP
        self._loading = False     # blokada przed podwójnym kliknięciem podczas ładowania

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
            "Kliknij dwukrotnie na mapę, aby porównać dwa obiekty OpenStreetMap."
        )
        self.action.triggered.connect(self._on_action_triggered)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToWebMenu(self.PLUGIN_NAME, self.action)

    def unload(self):
        self._abort_worker()
        self._deactivate_tool()
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginWebMenu(self.PLUGIN_NAME, self.action)

    # ── Obsługa narzędzia ────────────────────────────────────────────────────

    def _on_action_triggered(self, checked):
        if checked:
            self._activate_tool()
        else:
            self._deactivate_tool()

    def _activate_tool(self):
        """Uruchom narzędzie klikania i zresetuj stan wyboru."""
        self._feature1 = None
        self._feature2 = None
        self._loading = False

        self.map_tool = OSMClickTool(self.canvas)
        self.map_tool.clicked.connect(self._on_canvas_clicked)
        self.map_tool.deactivated.connect(self._on_tool_deactivated)
        self.canvas.setMapTool(self.map_tool)

        self._push_info("Kliknij na mapę, aby wybrać <b>Obiekt 1</b> z OpenStreetMap.")

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
        """Wywoływane gdy QGIS przełączy się na inne narzędzie mapy."""
        self._set_action_checked(False)
        self.map_tool = None

    def _set_action_checked(self, state: bool):
        if self.action is not None:
            self.action.setChecked(state)

    def _abort_worker(self):
        """Zatrzymaj aktywny wątek HTTP jeśli działa."""
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        self._worker = None
        self._loading = False

    # ── Logika kliknięć (asynchroniczna) ────────────────────────────────────

    def _on_canvas_clicked(self, lat, lon):
        if self._loading:
            self._push_info("Trwa pobieranie… poczekaj chwilę.")
            return

        click_number = 1 if self._feature1 is None else 2
        self._loading = True
        self._push_info(
            f"Pobieranie danych OSM dla <b>Obiektu {click_number}</b> "
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
                "Nie znaleziono obiektów OSM z tagami w tym miejscu (bufor 10 m). "
                "Spróbuj kliknąć bliżej centrum obiektu."
            )
            return

        selected = self._select_feature(features, click_number)
        if selected is None:
            return

        if click_number == 1:
            self._feature1 = selected
            name = get_feature_display_name(selected)
            self._push_info(
                f"<b>Obiekt 1</b> wybrany: {name}. "
                "Teraz kliknij na mapę, aby wybrać <b>Obiekt 2</b>."
            )
        else:
            self._feature2 = selected
            self._deactivate_tool()
            self._show_comparison()

    def _on_fetch_error(self, message):
        self._loading = False
        self._push_error(f"Błąd połączenia z OSM API: {message}")

    def _select_feature(self, features, click_number):
        """Zwraca wybrany feature – bezpośrednio lub przez dialog selekcji."""
        if len(features) == 1:
            return features[0]

        dialog = FeatureSelectorDialog(
            features, click_number=click_number, parent=self.iface.mainWindow()
        )
        if dialog.exec_() == FeatureSelectorDialog.Accepted:
            return dialog.selected_feature
        return None

    # ── Dialog porównania ────────────────────────────────────────────────────

    def _show_comparison(self):
        dialog = ComparisonDialog(
            self._feature1, self._feature2, parent=self.iface.mainWindow()
        )
        dialog.compare_again.connect(self._on_compare_again)
        dialog.exec_()

    def _on_compare_again(self):
        """Użytkownik kliknął 'Nowe porównanie' — aktywuj narzędzie ponownie."""
        self._set_action_checked(True)
        self._activate_tool()

    # ── Wiadomości ───────────────────────────────────────────────────────────

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
