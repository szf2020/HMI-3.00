from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import uuid4
from typing import Any, Dict

from PySide6.QtCore import Qt


class SerializableGraphicMixin(ABC):
    """Mixin that provides a canonical JSON shape for scene graphic objects."""

    DEFAULT_DATA_LINKS = {"tags": [], "comments": []}

    def ensure_object_id(self) -> str:
        """Ensure the item has a persistent UUID in Qt.UserRole payload."""
        data = self.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            data = {}

        object_id = data.get("object_id")
        if not isinstance(object_id, str) or not object_id.strip():
            object_id = str(uuid4())
            data["object_id"] = object_id
            self.setData(Qt.ItemDataRole.UserRole, data)

        return object_id

    @staticmethod
    def canonical_document(
        *,
        object_id: str,
        object_type: str,
        geometry: Dict[str, Any],
        styling: Dict[str, Any],
        data_links: Dict[str, Any] | None = None,
        z_index: float | None = None,
        locked: bool | None = None,
        visible: bool | None = None,
        custom_props: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        doc = {
            "object_id": object_id,
            "object_type": object_type,
            "geometry": geometry,
            "styling": styling,
            "data_links": data_links or {"tags": [], "comments": []},
        }
        if z_index is not None:
            doc["z_index"] = z_index
        if locked is not None:
            doc["locked"] = locked
        if visible is not None:
            doc["visible"] = visible
        if custom_props is not None:
            doc["custom_props"] = custom_props
        return doc

    @abstractmethod
    def to_json_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def apply_json_dict(self, data: Dict[str, Any]) -> None:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def from_json_dict(cls, data: Dict[str, Any], scene_context) -> "SerializableGraphicMixin":
        raise NotImplementedError
