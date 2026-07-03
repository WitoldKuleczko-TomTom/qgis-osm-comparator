# -*- coding: utf-8 -*-
from qgis.gui import QgsMapTool
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QCursor


class OSMClickTool(QgsMapTool):
    """Map tool that emits WGS-84 coordinates on canvas click."""

    clicked = pyqtSignal(float, float)  # lat, lon

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.setCursor(QCursor(Qt.CrossCursor))

    def canvasReleaseEvent(self, event):
        point = self.toMapCoordinates(event.pos())

        crs_src   = QgsProject.instance().crs()
        crs_wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")

        if crs_src != crs_wgs84:
            transform = QgsCoordinateTransform(crs_src, crs_wgs84, QgsProject.instance())
            point = transform.transform(point)

        self.clicked.emit(point.y(), point.x())  # lat, lon
