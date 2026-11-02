import math
import uuid
from typing import List, Dict, Any, Tuple


class LayoutEngine:
    """Математический движок изометрической компоновки композиций.
    
    Реализует 3 архитектурных лейаута из Figma:
    - under_headline: свободная зона слева под заголовок, фокусная группа справа.
    - offset: диагональная многоуровневая перспектива.
    - clustered: центрированная изометрическая композиция.
    """

    FORMAT_SPECS = {
        "1200x630": {"width": 1200, "height": 630, "aspect": 1200 / 630},
        "1000x1000": {"width": 1000, "height": 1000, "aspect": 1.0},
        "800x1200": {"width": 800, "height": 1200, "aspect": 800 / 1200},
    }

    # Базовые коэффициенты масштабирования исходных SVG элементов
    SCALE_FACTORS = {
        "l": {
            "book": 0.42,
            "phone": 0.52,
            "headphones": 0.50,
            "lamp": 0.40,
            "wallet": 0.55,
            "puzzle": 0.58,
            "coin": 0.65,
            "folder": 0.42,
            "pen": 0.60,
            "vase": 0.45,
        },
        "s": {
            "book": 0.70,
            "phone": 0.85,
            "headphones": 0.80,
            "lamp": 0.70,
            "wallet": 0.85,
            "puzzle": 0.90,
            "coin": 0.95,
            "folder": 0.75,
            "pen": 0.90,
            "vase": 0.75,
        }
    }

    def arrange(
        self,
        components: List[Dict[str, Any]],
        canvas_format: str = "1200x630",
        detail_size: str = "l",
        layout_type: str = "clustered",
    ) -> List[Dict[str, Any]]:
        spec = self.FORMAT_SPECS.get(canvas_format, self.FORMAT_SPECS["1200x630"])
        cw = spec["width"]
        ch = spec["height"]
        
        # Разделяем на главные и фоновые объекты
        main_objs = [c for c in components if c.get("state") == "main"]
        bg_objs = [c for c in components if c.get("state") == "bg"]

        # Если пользователь не передал состояния, первый делаем главным, остальные по умолчанию
        if not main_objs and components:
            components[0]["state"] = "main"
            main_objs = [components[0]]
            bg_objs = components[1:]

        placed: List[Dict[str, Any]] = []

        if layout_type == "under_headline":
            placed = self._layout_under_headline(main_objs, bg_objs, cw, ch, detail_size)
        elif layout_type == "offset":
            placed = self._layout_offset(main_objs, bg_objs, cw, ch, detail_size)
        else:  # clustered
            placed = self._layout_clustered(main_objs, bg_objs, cw, ch, detail_size)

        # Сортировка слоев: фоновые ниже главных, при равном типе сортировка по Y (изометрическая глубина)
        for idx, item in enumerate(placed):
            base_z = 10 if item["state"] == "bg" else 30
            # Смещение по Y (чем ниже объект на экране, тем он ближе к зрителю)
            y_depth = int(item["y"] / 20)
            item["z_index"] = base_z + y_depth

        placed.sort(key=lambda o: o["z_index"])
        return placed

    def _get_scale(self, object_id: str, size: str) -> float:
        size_scales = self.SCALE_FACTORS.get(size, self.SCALE_FACTORS["l"])
        return size_scales.get(object_id, 0.5)

    def _layout_under_headline(
        self, main_objs: List[Dict[str, Any]], bg_objs: List[Dict[str, Any]], cw: float, ch: float, size: str
    ) -> List[Dict[str, Any]]:
        """Правая зона холста (35%..95% по ширине), левая зона свободна для заголовка."""
        result = []
        center_x = cw * 0.68
        center_y = ch * 0.52

        # 1. Фоновые объекты (располагаются чуть сзади и выше)
        bg_offsets = [
            (-180, -120),
            (160, -110),
            (200, 80),
            (-220, 60),
        ]
        for i, obj in enumerate(bg_objs):
            ox, oy = bg_offsets[i % len(bg_offsets)]
            scale = self._get_scale(obj["object_id"], size) * 0.9
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale
            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": "bg",
                "x": round(center_x + ox - w / 2, 1),
                "y": round(center_y + oy - h / 2, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        # 2. Главные объекты (ядро композиции)
        main_offsets = [
            (0, 0),         # центральный доминант
            (140, 40),      # правый акцент
            (-130, 50),     # левый акцент
            (50, -90),      # верхний
            (-60, 90),      # нижний передний
        ]
        for i, obj in enumerate(main_objs):
            ox, oy = main_offsets[i % len(main_offsets)]
            scale = self._get_scale(obj["object_id"], size)
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale
            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": "main",
                "x": round(center_x + ox - w / 2, 1),
                "y": round(center_y + oy - h / 2, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        return result

    def _layout_offset(
        self, main_objs: List[Dict[str, Any]], bg_objs: List[Dict[str, Any]], cw: float, ch: float, size: str
    ) -> List[Dict[str, Any]]:
        """Диагональное смещение из левого верхнего в правый нижний угол."""
        result = []
        all_objs = main_objs + bg_objs
        total = len(all_objs)
        if total == 0:
            return result

        # Точки вдоль диагональной изометрической оси
        start_x = cw * 0.15
        start_y = ch * 0.18
        end_x = cw * 0.85
        end_y = ch * 0.78

        for i, obj in enumerate(all_objs):
            t = (i + 0.5) / total
            is_bg = obj.get("state") == "bg"
            
            # Легкое изометрическое колебание от прямой оси
            lateral_shift = 70 * math.sin(i * 1.8)
            x_pos = start_x + (end_x - start_x) * t + lateral_shift
            y_pos = start_y + (end_y - start_y) * t + ( -40 if is_bg else 20 )

            scale = self._get_scale(obj["object_id"], size) * (0.85 if is_bg else 1.0)
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale

            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": obj["state"],
                "x": round(x_pos - w / 2, 1),
                "y": round(y_pos - h / 2, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        return result

    def _layout_clustered(
        self, main_objs: List[Dict[str, Any]], bg_objs: List[Dict[str, Any]], cw: float, ch: float, size: str
    ) -> List[Dict[str, Any]]:
        """Центральный изометрический остров."""
        result = []
        center_x = cw * 0.50
        center_y = ch * 0.50

        # Фоновые силуэты формируют глубину сзади
        bg_positions = [
            (-160, -110),
            (170, -90),
            (-220, 30),
            (210, 40),
            (0, -140),
        ]
        for i, obj in enumerate(bg_objs):
            pos = bg_positions[i % len(bg_positions)]
            scale = self._get_scale(obj["object_id"], size) * 0.88
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale
            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": "bg",
                "x": round(center_x + pos[0] - w / 2, 1),
                "y": round(center_y + pos[1] - h / 2, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        # Главные цветные объекты формируют передний план
        main_positions = [
            (0, 30),         # центральный
            (-140, 60),      # передний левый
            (140, 50),       # передний правый
            (-80, -50),      # средний левый
            (90, -40),       # средний правый
        ]
        for i, obj in enumerate(main_objs):
            pos = main_positions[i % len(main_positions)]
            scale = self._get_scale(obj["object_id"], size)
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale
            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": "main",
                "x": round(center_x + pos[0] - w / 2, 1),
                "y": round(center_y + pos[1] - h / 2, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        return result
