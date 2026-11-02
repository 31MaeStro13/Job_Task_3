import json
import re
from pathlib import Path
from typing import Dict, Optional, Any
from django.conf import settings


class PaletteService:
    """Управление цветовыми палитрами и точечная перекраска SVG."""

    DEFAULT_PALETTES = {
        "purple": {
            "id": "purple",
            "name": "Фиолетовая (Базовая)",
            "description": "Фиолетовый фон с кораллово-желтыми акцентами",
            "bg_light": "#D7CDF5",
            "bg_mid": "#AA9BF0",
            "bg_dark": "#7864D7",
            "obj_accent_1": "#F9ECB0",
            "obj_accent_2": "#F9A3AA",
            "obj_accent_3": "#FFE3E1",
            "stroke": "#181817",
            "white": "#FFFFFF",
        },
        "peach": {
            "id": "peach",
            "name": "Персиковая / Оранжевая",
            "description": "Теплый персиковый фон с бирюзовыми акцентами",
            "bg_light": "#FDD7B9",
            "bg_mid": "#FAC896",
            "bg_dark": "#D27532",
            "obj_accent_1": "#F9ECB0",
            "obj_accent_2": "#80DADA",
            "obj_accent_3": "#BEEBEB",
            "stroke": "#181817",
            "white": "#FFFFFF",
        },
        "mint": {
            "id": "mint",
            "name": "Мятная / Голубая",
            "description": "Свежий мятный фон с синими и розовыми акцентами",
            "bg_light": "#BEEBEB",
            "bg_mid": "#80DADA",
            "bg_dark": "#5ABEBE",
            "obj_accent_1": "#FFD4F2",
            "obj_accent_2": "#6D7BFC",
            "obj_accent_3": "#B6C6FE",
            "stroke": "#181817",
            "white": "#FFFFFF",
        },
    }

    def __init__(self, palettes_file: Optional[Path] = None):
        self.palettes_file = palettes_file or (settings.ASSETS_DIR / "palettes.json")
        self.palettes: Dict[str, Dict[str, Any]] = dict(self.DEFAULT_PALETTES)
        self.load()

    def load(self) -> None:
        if self.palettes_file.exists():
            with open(self.palettes_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.palettes.update(data)

    def get_palette(self, palette_id: str, custom_palette: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if custom_palette:
            self.validate_palette_rules(custom_palette)
            return custom_palette
        return self.palettes.get(palette_id, self.palettes["purple"])

    def validate_palette_rules(self, p: Dict[str, Any]) -> None:
        """Проверка дизайн-правила:
        'Цвета фонов могут использоваться в объектах. Цвета для объектов не могут использоваться в фонах.'
        """
        bg_colors = {
            p.get("bg_light", "").lower(),
            p.get("bg_mid", "").lower(),
            p.get("bg_dark", "").lower(),
        }
        obj_colors = {
            p.get("obj_accent_1", "").lower(),
            p.get("obj_accent_2", "").lower(),
            p.get("obj_accent_3", "").lower(),
        }
        intersection = bg_colors.intersection(obj_colors)
        if intersection:
            raise ValueError(
                f"Нарушение правила дизайна: акцентные цвета объектов {intersection} не могут быть использованы в качестве цветов фона!"
            )

    def build_color_map(
        self,
        from_palette_id: str = "purple",
        to_palette_id: str = "purple",
        custom_to_palette: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        from_p = self.get_palette(from_palette_id)
        to_p = self.get_palette(to_palette_id, custom_to_palette)

        color_map: Dict[str, str] = {}

        # 1. Фоновые тона
        color_map[from_p["bg_light"].lower()] = to_p["bg_light"]
        color_map[from_p["bg_mid"].lower()] = to_p["bg_mid"]
        color_map[from_p["bg_dark"].lower()] = to_p["bg_dark"]

        # 2. Акценты объектов
        color_map[from_p["obj_accent_1"].lower()] = to_p["obj_accent_1"]
        color_map[from_p["obj_accent_2"].lower()] = to_p["obj_accent_2"]
        color_map[from_p["obj_accent_3"].lower()] = to_p["obj_accent_3"]

        # 3. Вариации оттенков исходных SVG из Figma
        color_map["#f5efc9"] = to_p["obj_accent_1"]
        color_map["#fac896"] = to_p["bg_mid"] if to_palette_id == "peach" else to_p["obj_accent_1"]
        color_map["#d27532"] = to_p["bg_dark"] if to_palette_id == "peach" else to_p["obj_accent_2"]
        color_map["#ffd4f2"] = to_p["obj_accent_1"] if to_palette_id == "mint" else to_p["obj_accent_2"]
        color_map["#6d7bfc"] = to_p["obj_accent_2"] if to_palette_id == "mint" else to_p["bg_dark"]
        color_map["#b6c6fe"] = to_p["obj_accent_3"] if to_palette_id == "mint" else to_p["bg_light"]
        color_map["#80dada"] = to_p["bg_mid"] if to_palette_id == "mint" else (to_p["obj_accent_2"] if to_palette_id == "peach" else to_p["bg_mid"])
        color_map["#beebeb"] = to_p["bg_light"] if to_palette_id == "mint" else (to_p["obj_accent_3"] if to_palette_id == "peach" else to_p["bg_light"])
        color_map["#5abebe"] = to_p["bg_dark"] if to_palette_id == "mint" else to_p["bg_dark"]

        return color_map

    def recolor_svg(
        self,
        svg_xml: str,
        from_palette_id: str = "purple",
        to_palette_id: str = "purple",
        custom_to_palette: Optional[Dict[str, Any]] = None,
        is_bg_object: bool = False,
    ) -> str:
        if from_palette_id == to_palette_id and not custom_to_palette and not is_bg_object:
            return svg_xml

        to_p = self.get_palette(to_palette_id, custom_to_palette)
        from_p = self.get_palette(from_palette_id)
        color_map = self.build_color_map(from_palette_id, to_palette_id, custom_to_palette)

        def replace_color(match: re.Match) -> str:
            attr = match.group(1)
            color = match.group(2)
            suffix = match.group(3)
            
            c_low = color.lower()
            if is_bg_object:
                if c_low in ["#181817", "black", "#000", "#000000"]:
                    new_color = to_p.get("stroke", "#181817")
                elif c_low in ["white", "#fff", "#ffffff"]:
                    new_color = to_p["bg_light"]
                elif c_low == from_p["bg_dark"].lower():
                    new_color = to_p["bg_dark"]
                else:
                    new_color = to_p["bg_light"]
                return f'{attr}"{new_color}"{suffix}'

            if c_low in color_map:
                new_color = color_map[c_low]
                return f'{attr}"{new_color}"{suffix}'
            
            return match.group(0)

        pattern = re.compile(r'(fill=|stroke=|stop-color=)["\'](#[0-9a-fA-F]{3,8}|white|black)["\'](\s|>|/)')
        return pattern.sub(replace_color, svg_xml)
