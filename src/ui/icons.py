from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import qtawesome as qta
from PySide6.QtGui import QColor, QIcon


@dataclass(frozen=True)
class IconSpec:
    name: str
    color: str = "#f2f2f2"


class IconProvider:
    """Central icon provider.

    Uses an icon font through qtawesome.
    """

    def __init__(self) -> None:
        self._cache: Dict[tuple[str, str], QIcon] = {}

    def icon(self, spec: IconSpec) -> QIcon:
        key = (spec.name, spec.color)
        if key in self._cache:
            return self._cache[key]
        ic = qta.icon(spec.name, color=QColor(spec.color))
        self._cache[key] = ic
        return ic


ICONS = IconProvider()
