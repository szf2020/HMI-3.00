from __future__ import annotations

from typing import Any
from uuid import uuid4

from debug_utils import get_logger

logger = get_logger(__name__)
SCHEMA_VERSION = 1


def validate_serialized_object(obj: dict[str, Any]) -> bool:
    required = {
        "object_id": str,
        "object_type": str,
        "geometry": dict,
        "styling": dict,
        "data_links": dict,
    }
    for k, t in required.items():
        if k not in obj or not isinstance(obj[k], t):
            logger.error("Invalid serialized object: missing/invalid key '%s'", k)
            return False

    geom = obj["geometry"]
    for gk in ["x", "y", "width", "height", "rotation"]:
        if gk not in geom or not isinstance(geom[gk], (int, float)):
            logger.error("Invalid serialized object geometry key '%s'", gk)
            return False

    links = obj["data_links"]
    if not isinstance(links.get("tags", []), list) or not isinstance(links.get("comments", []), list):
        logger.error("Invalid serialized object data_links payload")
        return False

    return True


def build_screen_document(name, bg_color, width, height, objects):
    valid_objects = []
    for obj in objects:
        if validate_serialized_object(obj):
            valid_objects.append(obj)
        else:
            logger.error("Rejecting invalid object write for screen '%s'", name)

    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": {
            "screen_id": str(uuid4()),
            "name": name,
            "background_color": bg_color,
            "dimensions": {"width": width, "height": height},
        },
        "objects": valid_objects,
    }
