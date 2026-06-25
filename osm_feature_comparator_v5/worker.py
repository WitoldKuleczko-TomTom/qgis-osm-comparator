# -*- coding: utf-8 -*-
"""Background QThreads that run OSM API requests without blocking the UI."""
from PyQt5.QtCore import QThread, pyqtSignal

from .overpass_client    import query_features_at_point, DEFAULT_RADIUS_M
from .osm_history_client import query_feature_history


class FetchWorker(QThread):
    """Worker thread — fetches OSM features via Overpass API."""

    finished = pyqtSignal(list)   # list of feature dicts on success
    error    = pyqtSignal(str)    # error message on failure

    def __init__(self, lat, lon, radius=DEFAULT_RADIUS_M, parent=None):
        super().__init__(parent)
        self.lat    = lat
        self.lon    = lon
        self.radius = radius

    def run(self):
        try:
            features = query_features_at_point(self.lat, self.lon, self.radius)
            self.finished.emit(features)
        except Exception as exc:
            self.error.emit(str(exc))


class HistoryFetchWorker(QThread):
    """Worker thread — fetches all versions of an OSM element from the OSM REST API."""

    finished = pyqtSignal(list)   # list of version dicts sorted by version asc
    error    = pyqtSignal(str)

    def __init__(self, osm_type, osm_id, parent=None):
        super().__init__(parent)
        self.osm_type = osm_type
        self.osm_id   = osm_id

    def run(self):
        try:
            versions = query_feature_history(self.osm_type, self.osm_id)
            self.finished.emit(versions)
        except Exception as exc:
            self.error.emit(str(exc))
