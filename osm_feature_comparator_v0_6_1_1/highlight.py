# -*- coding: utf-8 -*-
"""Shared rubber-band highlighting helpers.

Used by both plugin.py (persistent highlights after selection) and
feature_selector_dialog.py (live preview while browsing the feature list).
"""
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
    QgsWkbTypes,
)
from qgis.gui import QgsRubberBand
from PyQt5.QtGui import QColor


def make_rubber_bands(canvas, feature, color):
    """Return a list of QgsRubberBand objects for *feature* drawn on *canvas*.

    *color* must be a QColor.  The caller owns the returned objects and is
    responsible for removing them from the canvas scene when done.
    """
    osm_type = feature.get("type")

    crs_wgs84  = QgsCoordinateReferenceSystem("EPSG:4326")
    crs_canvas = canvas.mapSettings().destinationCrs()
    transform  = (
        QgsCoordinateTransform(crs_wgs84, crs_canvas, QgsProject.instance())
        if crs_wgs84 != crs_canvas else None
    )

    def to_canvas(lon, lat):
        pt = QgsPointXY(lon, lat)
        return transform.transform(pt) if transform else pt

    rbs = []

    if osm_type == "node":
        lat = feature.get("lat")
        lon = feature.get("lon")
        if lat is None or lon is None:
            return rbs
        rb = QgsRubberBand(canvas, QgsWkbTypes.PointGeometry)
        rb.setColor(color)
        rb.setWidth(4)
        rb.setIconSize(14)
        rb.setIcon(QgsRubberBand.ICON_CIRCLE)
        rb.addPoint(to_canvas(lon, lat))
        rbs.append(rb)

    elif osm_type == "way":
        geom_pts = feature.get("geometry", [])
        if not geom_pts:
            return rbs
        pts = [to_canvas(p["lon"], p["lat"]) for p in geom_pts]
        is_closed = (
            len(pts) >= 4
            and abs(pts[0].x() - pts[-1].x()) < 1e-7
            and abs(pts[0].y() - pts[-1].y()) < 1e-7
        )
        if is_closed:
            rb = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
            fill = QColor(color)
            fill.setAlpha(50)
            rb.setFillColor(fill)
            rb.setStrokeColor(color)
            rb.setWidth(3)
        else:
            rb = QgsRubberBand(canvas, QgsWkbTypes.LineGeometry)
            rb.setColor(color)
            rb.setWidth(3)
        for pt in pts:
            rb.addPoint(pt)
        rbs.append(rb)

    elif osm_type == "relation":
        for member in feature.get("members", []):
            if member.get("type") != "way":
                continue
            geom_pts = member.get("geometry", [])
            if not geom_pts:
                continue
            rb = QgsRubberBand(canvas, QgsWkbTypes.LineGeometry)
            rb.setColor(color)
            rb.setWidth(3)
            for p in geom_pts:
                rb.addPoint(to_canvas(p["lon"], p["lat"]))
            rbs.append(rb)

    return rbs


def clear_rubber_bands(canvas, rbs):
    """Remove *rbs* from *canvas* scene and empty the list in-place."""
    for rb in rbs:
        rb.reset()
        canvas.scene().removeItem(rb)
    rbs.clear()
