# -*- coding: utf-8 -*-
"""Klient Overpass API do wyszukiwania obiektów OSM w pobliżu punktu.

Overpass API używa odległości od GEOMETRII segmentów dróg (nie tylko węzłów),
dzięki czemu kliknięcie w środek segmentu drogi (między węzłami) poprawnie
zwraca dany way. OSM API /map zwraca tylko way'e których węzły są w bbox —
nie nadaje się do klikania w środek linii.

Dzięki FetchWorker (QThread) wywołanie jest asynchroniczne i nie blokuje UI.
"""
import json
import urllib.parse
import urllib.request

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_RADIUS_M = 10  # promień bufora w metrach


def query_features_at_point(lat, lon, radius=DEFAULT_RADIUS_M):
    """Pobierz obiekty OSM w promieniu `radius` metrów od punktu za pomocą Overpass API.

    Overpass `around` oblicza odległość od najbliższego punktu na SEGMENCIE way'a,
    co pozwala znaleźć drogi kliknięte w środku (nie tylko przy węzłach).
    Zwraca listę słowników {"type", "id", "tags"}. Obiekty bez tagów są odfiltrowane.
    """
    query = f"""[out:json][timeout:15];
(
  node(around:{radius},{lat},{lon});
  way(around:{radius},{lat},{lon});
  relation(around:{radius},{lat},{lon});
);
out tags;"""

    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "QGIS-OSMFeatureComparator/1.0"},
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))

    elements = result.get("elements", [])
    return [e for e in elements if e.get("tags")]


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
