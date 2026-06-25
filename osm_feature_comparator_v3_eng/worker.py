# -*- coding: utf-8 -*-
"""Background QThread that runs the OSM API request without blocking the UI."""
from PyQt5.QtCore import QThread, pyqtSignal

from .overpass_client import query_features_at_point, DEFAULT_RADIUS_M


class FetchWorker(QThread):
    """Worker thread that fetches OSM features and emits results via Qt signals."""

    finished = pyqtSignal(list)  # list of features on success
    error = pyqtSignal(str)      # error message on failure

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
