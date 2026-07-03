# -*- coding: utf-8 -*-
"""OSM REST API client for fetching element version history.

Endpoint: GET https://api.openstreetmap.org/api/0.6/{type}/{id}/history.json

Each version dict contains: type, id, version, timestamp, changeset, user, uid,
visible, tags (and nodes/members for ways/relations — ignored here).
"""
import json
import urllib.request

OSM_API_URL = "https://api.openstreetmap.org/api/0.6"


def query_feature_history(osm_type, osm_id):
    """Return all versions of an OSM element, sorted ascending by version number.

    Versions that were deleted (visible=False) are included — the caller decides
    how to handle them. Versions with no 'tags' key get an empty dict assigned.
    """
    url = f"{OSM_API_URL}/{osm_type}/{osm_id}/history.json"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "QGIS-OSMFeatureComparator/4.0"},
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    elements = result.get("elements", [])

    # Ensure tags key is always present
    for e in elements:
        if "tags" not in e:
            e["tags"] = {}

    # Sort ascending by version (API usually returns in order, but be safe)
    elements.sort(key=lambda e: e.get("version", 0))
    return elements
