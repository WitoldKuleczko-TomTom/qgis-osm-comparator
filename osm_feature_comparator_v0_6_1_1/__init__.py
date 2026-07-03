# -*- coding: utf-8 -*-
def classFactory(iface):
    from .plugin import OSMFeatureComparator
    return OSMFeatureComparator(iface)
