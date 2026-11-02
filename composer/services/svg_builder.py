from typing import List, Dict, Any, Optional
from .library_service import LibraryService
from .palette_service import PaletteService


class SvgBuilder:
    """Генератор и сборщик валидного монолитного SVG документа."""

    FORMAT_SPECS = {
        "1200x630": {"width": 1200, "height": 630},
        "1000x1000": {"width": 1000, "height": 1000},
        "800x1200": {"width": 800, "height": 1200},
    }

    def __init__(self, library_service: LibraryService, palette_service: PaletteService):
        self.library = library_service
        self.palettes = palette_service

    def build_svg(
        self,
        placed_objects: List[Dict[str, Any]],
        canvas_format: str = "1200x630",
        palette_id: str = "purple",
        custom_palette: Optional[Dict[str, Any]] = None,
    ) -> str:
        spec = self.FORMAT_SPECS.get(canvas_format, self.FORMAT_SPECS["1200x630"])
        cw = spec["width"]
        ch = spec["height"]

        palette = self.palettes.get_palette(palette_id, custom_palette)

        all_defs = []
        body_groups = []

        # 1. Генерация фонового слоя с изометрической сеткой
        bg_markup = self._render_background(cw, ch, palette)

        # 2. Сортировка объектов по z_index
        sorted_objects = sorted(placed_objects, key=lambda o: o.get("z_index", 0))

        # 3. Встраивание каждого объекта
        for idx, obj in enumerate(sorted_objects):
            obj_id = obj["object_id"]
            size = obj.get("size", "l")
            state = obj.get("state", "main")
            x = obj.get("x", 0)
            y = obj.get("y", 0)
            scale = obj.get("scale", 1.0)
            rotation = obj.get("rotation", 0.0)
            item_id = obj.get("id", f"obj_{idx}")

            try:
                inner_svg, orig_w, orig_h, vb, defs = self.library.get_element_inner_svg(obj_id, size, state)
            except Exception as e:
                continue

            # Уникализация id внутри defs и clip-path, чтобы разные копии одного объекта не конфликтовали
            unique_prefix = f"o{idx}_"
            defs_unique = defs.replace('id="', f'id="{unique_prefix}').replace('url(#', f'url(#{unique_prefix}')
            inner_unique = inner_svg.replace('id="', f'id="{unique_prefix}').replace('url(#', f'url(#{unique_prefix}')

            # Перекраска объекта под целевую палитру
            is_bg_obj = (state == "bg")
            recolored_inner = self.palettes.recolor_svg(
                inner_unique,
                from_palette_id="purple",
                to_palette_id=palette_id,
                custom_to_palette=custom_palette,
                is_bg_object=is_bg_obj,
            )
            recolored_defs = self.palettes.recolor_svg(
                defs_unique,
                from_palette_id="purple",
                to_palette_id=palette_id,
                custom_to_palette=custom_palette,
                is_bg_object=is_bg_obj,
            )

            if recolored_defs:
                all_defs.append(recolored_defs)

            # Формирование группы с трансформацией
            transform_parts = [f"translate({x}, {y})"]
            if rotation:
                transform_parts.append(f"rotate({rotation})")
            if scale != 1.0:
                transform_parts.append(f"scale({scale})")

            transform_attr = " ".join(transform_parts)

            group_xml = (
                f'  <g id="{item_id}" class="scene-object" data-object-id="{obj_id}" '
                f'data-size="{size}" data-state="{state}" transform="{transform_attr}">\n'
                f"    {recolored_inner}\n"
                f"  </g>"
            )
            body_groups.append(group_xml)

        defs_block = ""
        if all_defs:
            defs_block = "  <defs>\n    " + "\n    ".join(all_defs) + "\n  </defs>\n"

        full_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{cw}" height="{ch}" '
            f'viewBox="0 0 {cw} {ch}" fill="none">\n'
            f"{defs_block}"
            f"{bg_markup}\n"
            + "\n".join(body_groups)
            + "\n</svg>"
        )

        return full_svg

    def _render_background(self, cw: float, ch: float, p: Dict[str, Any]) -> str:
        """Рендерит базовый фон и аутентичные изометрические акцентные линии из Figma."""
        bg_light = p["bg_light"]
        bg_mid = p["bg_mid"]
        bg_dark = p["bg_dark"]

        # Изометрические диагональные линии (угол ~30 градусов / наклон 0.577)
        return f"""  <!-- Background Layer -->
  <rect width="{cw}" height="{ch}" fill="{bg_light}"/>
  <g class="bg-grid-decor" opacity="0.4">
    <!-- Isometric guideline accents -->
    <path d="M0 {ch * 0.4} L{cw * 0.6} {ch * 0.1}" stroke="{bg_mid}" stroke-width="2" stroke-dasharray="6 6"/>
    <path d="M{cw * 0.2} {ch * 0.8} L{cw * 0.8} {ch * 0.5}" stroke="{bg_mid}" stroke-width="2"/>
    <path d="M{cw * 0.5} {ch * 0.9} L{cw} {ch * 0.6}" stroke="{bg_dark}" stroke-width="1.5" stroke-dasharray="4 4"/>
    <!-- Decorative isometric rings -->
    <ellipse cx="{cw * 0.15}" cy="{ch * 0.85}" rx="35" ry="18" fill="{bg_mid}" opacity="0.6"/>
    <ellipse cx="{cw * 0.88}" cy="{ch * 0.18}" rx="28" ry="14" fill="white" opacity="0.7"/>
  </g>"""
