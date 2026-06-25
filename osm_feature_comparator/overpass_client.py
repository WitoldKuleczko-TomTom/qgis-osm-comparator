# -*- coding: utf-8 -*-
"""Klient OSM API używający endpointu /api/0.6/map (szybszy niż Overpass dla małych bbox).

Endpoint zwraca XML ze wszystkimi obiektami w prostokącie bez etapu
przetwarzania zapytania — znacznie szybsza odpowiedź dla małego promienia.
Dzięki FetchWorker (QThread) wywołanie jest asynchroniczne i nie blokuje UI.
"""
import math
import urllib.request
import xml.etree.ElementTree as ET

OSM_API_URL = "https://api.openstreetmap.org/api/0.6/map"
DEFAULT_RADIUS_M = 10  # promień bufora w metrach


def _bbox_from_point(lat, lon, radius_m):
    """Oblicza bbox (left, bottom, right, top) w stopniach dla okrągłego bufora."""
    delta_lat = radius_m / 111_320.0
    delta_lon = radius_m / (111_320.0 * math.cos(math.radians(lat)))
    return (lon - delta_lon, lat - delta_lat, lon + delta_lon, lat + delta_lat)


def query_features_at_point(lat, lon, radius=DEFAULT_RADIUS_M):
    """Pobierz obiekty OSM (node/way/relation) w promieniu `radius` metrów od punktu.

    Używa oficjalnego OSM API /map – szybszy od Overpass dla małych obszarów.
    Zwraca listę słowników {"type", "id", "tags"}.
    Obiekty bez tagów są odfiltrowane.
    """
    left, bottom, right, top = _bbox_from_point(lat, lon, radius)
    url = f"{OSM_API_URL}?bbox={left:.7f},{bottom:.7f},{right:.7f},{top:.7f}"

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "QGIS-OSMFeatureComparator/1.0"},
    )

    with urllib.request.urlopen(req, timeout=15) as response:
        xml_data = response.read().decode("utf-8")

    root = ET.fromstring(xml_data)
    elements = []
    for elem in root:
        if elem.tag not in ("node", "way", "relation"):
            continue
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in elem if tag.tag == "tag"}
        if tags:
            elements.append(
                {
                    "type": elem.tag,
                    "id": int(elem.attrib.get("id", 0)),
                    "tags": tags,
                }
            )

    return elements


def get_feature_display_name(feature):
    """Zwraca czytelną nazwę obiektu OSM do wyświetlenia na liście."""
    tags = feature.get("tags", {})
    ftype = feature.get("type", "?")
    fid = feature.get("id", "?")

    name_keys = [
        "name", "name:pl", "ref", "highway", "amenity", "building",
        "landuse", "natural", "leisure", "shop", "tourism", "historic",
        "waterway", "railway", "aeroway",
    ]
    label = next((tags[k] for k in name_keys if k in tags), None)

    type_labels = {"node": "Węzeł", "way": "Linia", "relation": "Relacja"}
    type_str = type_labels.get(ftype, ftype.capitalize())

    if label:
        return f"{type_str} #{fid} — {label}"
    return f"{type_str} #{fid}"
