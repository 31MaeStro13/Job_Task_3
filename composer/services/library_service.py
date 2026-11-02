import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from django.conf import settings


class LibraryService:
    """Управление векторной библиотекой элементов из Figma."""

    def __init__(self, assets_dir: Optional[Path] = None):
        self.assets_dir = assets_dir or settings.ASSETS_DIR
        self.library_file = self.assets_dir / "library.json"
        self.elements_dir = self.assets_dir / "elements"
        self.backgrounds_dir = self.assets_dir / "backgrounds"
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        if self.library_file.exists():
            with open(self.library_file, "r", encoding="utf-8") as f:
                self._data = json.load(f)

    @property
    def objects(self) -> Dict[str, Any]:
        return self._data.get("objects", {})

    @property
    def formats(self) -> Dict[str, Any]:
        return self._data.get("formats", {
            "1200x630": {"width": 1200, "height": 630, "name": "Горизонтальный (1200×630)"},
            "1000x1000": {"width": 1000, "height": 1000, "name": "Квадрат (1000×1000)"},
            "800x1200": {"width": 800, "height": 1200, "name": "Вертикальный (800×1200)"},
        })

    def get_object_meta(self, object_id: str) -> Optional[Dict[str, Any]]:
        return self.objects.get(object_id)

    def get_element_path(self, object_id: str, size: str, state: str) -> Path:
        size = size.lower()
        state = state.lower()
        fname = f"{object_id}_{size}_{state}.svg"
        fpath = self.elements_dir / fname
        if not fpath.exists():
            # Fallback size
            fallback_size = "l" if size == "s" else "s"
            fpath = self.elements_dir / f"{object_id}_{fallback_size}_{state}.svg"
            if not fpath.exists():
                raise FileNotFoundError(f"SVG элемент не найден: {object_id}_{size}_{state}.svg")
        return fpath

    def get_element_raw_svg(self, object_id: str, size: str = "l", state: str = "main") -> str:
        fpath = self.get_element_path(object_id, size, state)
        with open(fpath, "r", encoding="utf-8") as f:
            return f.read()

    def get_element_inner_svg(self, object_id: str, size: str = "l", state: str = "main") -> Tuple[str, float, float, str, str]:
        """Извлекает внутренние теги SVG, ширину, высоту, viewBox и дефы/клипы."""
        raw_svg = self.get_element_raw_svg(object_id, size, state)
        root = ET.fromstring(raw_svg)
        
        w = float(root.get("width", 500))
        h = float(root.get("height", 500))
        vb = root.get("viewBox", f"0 0 {w} {h}")

        defs_content = []
        inner_content = []

        for child in root:
            tag = child.tag.split("}")[-1]
            if tag == "defs":
                for def_child in child:
                    defs_content.append(ET.tostring(def_child, encoding="unicode"))
            else:
                inner_content.append(ET.tostring(child, encoding="unicode"))

        return "".join(inner_content), w, h, vb, "".join(defs_content)

    def list_components(self) -> List[Dict[str, Any]]:
        """Возвращает список компонентов для каталога UI с превью."""
        result = []
        for obj_id, meta in self.objects.items():
            try:
                preview = self.get_element_raw_svg(obj_id, "s", "main")
            except Exception:
                preview = self.get_element_raw_svg(obj_id, "l", "main")

            result.append({
                "id": obj_id,
                "name_ru": meta.get("name_ru", obj_id),
                "name_en": meta.get("name_en", obj_id),
                "category": meta.get("category", "general"),
                "keywords": meta.get("keywords", []),
                "default_role": meta.get("default_role", "main"),
                "preview_svg": preview,
            })
        return result
