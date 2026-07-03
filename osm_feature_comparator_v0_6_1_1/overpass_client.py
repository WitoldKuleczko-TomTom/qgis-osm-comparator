# -*- coding: utf-8 -*-
"""Overpass API client — query modelled after the OSM.org Query Features button.

OSM.org combines two query types:
  1. around:R  — features (node/way/relation) whose geometry intersects a buffer
                 of R metres around the clicked point.
  2. is_in     — closed polygons (way + relation) that ENCLOSE the clicked point,
                 e.g. buildings, parks, forests, admin boundaries, landuse.
                 Works even when clicking deep inside a large area, far from its
                 edge — which 'around' alone would miss.

Both sets are merged by Overpass into a single deduplicated result.
FetchWorker (QThread) runs the request asynchronously so the UI stays responsive.
"""
import json
import urllib.parse
import urllib.request

OVERPASS_URL    = "https://overpass-api.de/api/interpreter"
DEFAULT_RADIUS_M = 10  # buffer radius in metres


def query_features_at_point(lat, lon, radius=DEFAULT_RADIUS_M):
    """Fetch OSM features near/enclosing a point — identical to OSM Query Features.

    Returns a list of dicts {"type", "id", "tags"}. Features without tags are filtered out.
    """
    query = f"""[out:json][timeout:25];
is_in({lat},{lon})->.enclosing;
(
  node(around:{radius},{lat},{lon});
  way(around:{radius},{lat},{lon});
  relation(around:{radius},{lat},{lon});
  way(pivot.enclosing);
  relation(pivot.enclosing);
);
out geom tags;"""

    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req  = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "QGIS-OSMFeatureComparator/0.6.1"},
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    elements = result.get("elements", [])
    return [e for e in elements if e.get("tags")]


def get_feature_display_name(feature):
    """Return a human-readable label for an OSM feature."""
    tags  = feature.get("tags", {})
    ftype = feature.get("type", "?")
    fid   = feature.get("id",   "?")

    name_keys = [
        "name", "name:en", "ref", "highway", "amenity", "building",
        "landuse", "natural", "leisure", "shop", "tourism", "historic",
        "waterway", "railway", "aeroway",
    ]
    label = next((tags[k] for k in name_keys if k in tags), None)

    type_labels = {"node": "Node", "way": "Way", "relation": "Relation"}
    type_str = type_labels.get(ftype, ftype.capitalize())

    if label:
        return f"{type_str} #{fid} — {label}"
    return f"{type_str} #{fid}"
