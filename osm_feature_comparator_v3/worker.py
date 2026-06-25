# -*- coding: utf-8 -*-
"""Worker QThread wykonujący zapytanie do OSM API w tle.

Dzięki temu interfejs QGIS pozostaje responsywny podczas oczekiwania
na odpowiedź serwera.
"""
from PyQt5.QtCore import QThread, pyqtSignal

from .overpass_client import query_features_at_point, DEFAULT_RADIUS_M


class FetchWorker(QThread):
    """Wątek pobierający obiekty OSM; emituje wyniki sygnałami Qt."""

    finished = pyqtSignal(list)   # lista features po sukcesie
    error = pyqtSignal(str)        # komunikat błędu

    def __init__(self, lat, lon, radius=DEFAULT_RADIUS_M, parent=None):
        super().__init__(parent)
        self.lat = lat
        self.lon = lon
        self.radius = radius

    def run(self):
        try:
            features = query_features_at_point(self.lat, self.lon, self.radius)
            self.finished.emit(features)
        except Exception as exc:
            self.error.emit(str(exc))
