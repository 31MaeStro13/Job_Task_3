import math
import uuid
from typing import List, Dict, Any, Tuple, Optional


class LayoutEngine:
    """Интеллектуальный слотовый движок изометрической композиции Figma (3 пространственные зоны).
    
    Основан на прямых координатных замерах эталонов Figma:
    - drop_clustered_l.svg (Собранно: трехзонный изометрический остров)
    - drop_headline_l.svg (Под заголовок: правая фокусировка, свободная левая зона)
    - drop_offset_l.svg (Со смещением: диагональный каскадный контрбаланс)
    
    Архитектурные принципы:
    1. Изометрическое зонирование:
       - Зона 1 (Левый остров / Базовое плато): Книга / Папка на столе, Телефон / Пазлы на поверхности.
       - Зона 2 (Центральный мост): Наушники / Кошелек, визуально связывающие левый и правый острова.
       - Зона 3 (Правый контрбаланс): Лампа / Ваза на заднем плане, Ручка / Монета на переднем плане.
    2. Единый масштаб 1:1 к Figma (FORMAT_SCALES) без искажения пропорций объектов.
    3. Z-Index строго по изометрической глубине (Ground Y) + приоритет поверхности (on_surface).
    4. Автоматическое математическое центрирование итогового bounding box сцены.
    """

    FORMAT_SPECS = {
        "1200x630": {"width": 1200, "height": 630, "ground_ratio_y": 0.82},
        "1000x1000": {"width": 1000, "height": 1000, "ground_ratio_y": 0.75},
        "800x1200": {"width": 800, "height": 1200, "ground_ratio_y": 0.70},
    }

    # Классификация объектов библиотеки по роли в изометрической композиции
    OBJECT_TYPES = {
        "book": "base",
        "folder": "base",
        "lamp": "tall",
        "vase": "tall",
        "phone": "medium",
        "headphones": "medium",
        "wallet": "medium",
        "puzzle": "small",
        "coin": "small",
        "pen": "small",
    }

    # Единый масштаб композиции 1:1 к исходным размерам в Figma
    FORMAT_SCALES = {
        "1200x630": {"l": 0.35, "s": 0.70},
        "1000x1000": {"l": 0.38, "s": 0.76},
        "800x1200": {"l": 0.32, "s": 0.64},
    }

    # Для обратной совместимости
    BASE_SCALES = FORMAT_SCALES

    # Композиционные слоты, выверенные по эталонам Figma
    SLOT_TEMPLATES = {
        "1200x630": {
            "clustered": {
                "main": [
                    ("zone1_base", 0.255, 0.818, False),
                    ("zone1_surface_1", 0.250, 0.583, True),
                    ("zone1_surface_2", 0.248, 0.497, True),
                    ("zone2_bridge", 0.603, 0.760, False),
                    ("zone3_tall", 0.840, 0.599, False),
                    ("zone3_front", 0.840, 0.862, False),
                    ("zone2_rear", 0.500, 0.580, False),
                    ("zone1_front", 0.180, 0.880, False),
                    ("zone3_mid", 0.720, 0.680, False),
                ],
                "bg": [(0.200, 0.440), (0.380, 0.420), (0.600, 0.420), (0.780, 0.440), (0.900, 0.460)],
            },
            "under_headline": {
                "main": [
                    ("zone1_base", 0.557, 0.683, False),
                    ("zone1_surface_1", 0.554, 0.548, True),
                    ("zone1_surface_2", 0.553, 0.498, True),
                    ("zone2_bridge", 0.757, 0.650, False),
                    ("zone3_tall", 0.894, 0.557, False),
                    ("zone3_front", 0.894, 0.708, False),
                    ("zone2_rear", 0.700, 0.500, False),
                    ("zone1_front", 0.520, 0.750, False),
                    ("zone3_mid", 0.820, 0.600, False),
                ],
                "bg": [(0.520, 0.420), (0.700, 0.400), (0.880, 0.420), (0.600, 0.380), (0.800, 0.380)],
            },
            "offset": {
                "main": [
                    ("zone_left_tall", 0.160, 0.599, False),
                    ("zone_left_front", 0.160, 0.862, False),
                    ("zone_mid_bridge", 0.397, 0.760, False),
                    ("zone_right_base", 0.745, 0.818, False),
                    ("zone_right_surface_1", 0.776, 0.595, True),
                    ("zone_right_surface_2", 0.793, 0.513, True),
                    ("zone_mid_rear", 0.480, 0.580, False),
                    ("zone_right_front", 0.820, 0.880, False),
                ],
                "bg": [(0.250, 0.420), (0.550, 0.400), (0.850, 0.420), (0.400, 0.380), (0.700, 0.380)],
            },
        },
        "1000x1000": {
            "clustered": {
                "main": [
                    ("zone1_base", 0.320, 0.780, False),
                    ("zone1_surface_1", 0.310, 0.580, True),
                    ("zone1_surface_2", 0.300, 0.500, True),
                    ("zone2_bridge", 0.620, 0.720, False),
                    ("zone3_tall", 0.780, 0.540, False),
                    ("zone3_front", 0.760, 0.840, False),
                    ("zone2_rear", 0.500, 0.520, False),
                    ("zone1_front", 0.220, 0.840, False),
                    ("zone3_mid", 0.700, 0.640, False),
                ],
                "bg": [(0.250, 0.400), (0.420, 0.380), (0.600, 0.380), (0.780, 0.400), (0.880, 0.420)],
            },
            "under_headline": {
                "main": [
                    ("zone1_base", 0.580, 0.720, False),
                    ("zone1_surface_1", 0.570, 0.560, True),
                    ("zone1_surface_2", 0.560, 0.500, True),
                    ("zone2_bridge", 0.780, 0.680, False),
                    ("zone3_tall", 0.860, 0.520, False),
                    ("zone3_front", 0.840, 0.800, False),
                    ("zone2_rear", 0.700, 0.480, False),
                    ("zone1_front", 0.520, 0.780, False),
                    ("zone3_mid", 0.820, 0.620, False),
                ],
                "bg": [(0.550, 0.400), (0.720, 0.380), (0.860, 0.400), (0.620, 0.360), (0.800, 0.360)],
            },
            "offset": {
                "main": [
                    ("zone_left_tall", 0.220, 0.540, False),
                    ("zone_left_front", 0.240, 0.820, False),
                    ("zone_mid_bridge", 0.450, 0.720, False),
                    ("zone_right_base", 0.720, 0.780, False),
                    ("zone_right_surface_1", 0.730, 0.580, True),
                    ("zone_right_surface_2", 0.740, 0.500, True),
                    ("zone_mid_rear", 0.500, 0.540, False),
                    ("zone_right_front", 0.780, 0.840, False),
                ],
                "bg": [(0.300, 0.380), (0.550, 0.360), (0.800, 0.380), (0.420, 0.350), (0.700, 0.350)],
            },
        },
        "800x1200": {
            "clustered": {
                "main": [
                    ("zone1_base", 0.350, 0.720, False),
                    ("zone1_surface_1", 0.340, 0.560, True),
                    ("zone1_surface_2", 0.330, 0.490, True),
                    ("zone2_bridge", 0.600, 0.650, False),
                    ("zone3_tall", 0.720, 0.480, False),
                    ("zone3_front", 0.680, 0.800, False),
                    ("zone2_rear", 0.500, 0.460, False),
                    ("zone1_front", 0.240, 0.780, False),
                    ("zone3_mid", 0.660, 0.580, False),
                ],
                "bg": [(0.280, 0.360), (0.450, 0.340), (0.600, 0.340), (0.750, 0.360), (0.850, 0.380)],
            },
            "under_headline": {
                "main": [
                    ("zone1_base", 0.600, 0.680, False),
                    ("zone1_surface_1", 0.590, 0.540, True),
                    ("zone1_surface_2", 0.580, 0.480, True),
                    ("zone2_bridge", 0.780, 0.640, False),
                    ("zone3_tall", 0.840, 0.460, False),
                    ("zone3_front", 0.800, 0.760, False),
                    ("zone2_rear", 0.700, 0.440, False),
                    ("zone1_front", 0.540, 0.720, False),
                    ("zone3_mid", 0.780, 0.560, False),
                ],
                "bg": [(0.560, 0.360), (0.720, 0.340), (0.850, 0.360), (0.620, 0.320), (0.780, 0.320)],
            },
            "offset": {
                "main": [
                    ("zone_left_tall", 0.260, 0.480, False),
                    ("zone_left_front", 0.280, 0.780, False),
                    ("zone_mid_bridge", 0.480, 0.650, False),
                    ("zone_right_base", 0.680, 0.720, False),
                    ("zone_right_surface_1", 0.690, 0.550, True),
                    ("zone_right_surface_2", 0.700, 0.480, True),
                    ("zone_mid_rear", 0.520, 0.500, False),
                    ("zone_right_front", 0.740, 0.800, False),
                ],
                "bg": [(0.320, 0.340), (0.520, 0.320), (0.750, 0.340), (0.420, 0.300), (0.680, 0.300)],
            },
        },
    }

    def arrange(
        self,
        components: List[Dict[str, Any]],
        canvas_format: str = "1200x630",
        detail_size: str = "l",
        layout_type: str = "clustered",
    ) -> List[Dict[str, Any]]:
        self._current_format = canvas_format
        spec = self.FORMAT_SPECS.get(canvas_format, self.FORMAT_SPECS["1200x630"])
        cw = spec["width"]
        ch = spec["height"]

        if not components:
            return []

        # 1. Разделение на главные и фоновые объекты
        main_objs = [dict(c) for c in components if c.get("state") == "main"]
        bg_objs = [dict(c) for c in components if c.get("state") == "bg"]

        if not main_objs and components:
            components[0]["state"] = "main"
            main_objs = [dict(components[0])]
            bg_objs = [dict(c) for c in components[1:]]

        # 2. Выбор стратегии компоновки
        if layout_type == "under_headline":
            placed = self._layout_under_headline(main_objs, bg_objs, cw, ch, detail_size)
        elif layout_type == "offset":
            placed = self._layout_offset(main_objs, bg_objs, cw, ch, detail_size)
        else:
            placed = self._layout_clustered(main_objs, bg_objs, cw, ch, detail_size)

        # 3. Расчет Z-Index по реальной экранной высоте подошвы (Ground Y) + приоритет поверхности
        for item in placed:
            ground_y = item["y"] + item["height"]
            base_z = int(ground_y)
            if item["state"] == "main":
                base_z += 500
            if item.get("on_surface"):
                base_z += 1000
            # Малые цветные аксессуары (ручка, монета) не должны перекрываться базовым плато
            if self.OBJECT_TYPES.get(item["object_id"]) == "small" and item["state"] == "main":
                base_z += 250
            item["z_index"] = base_z

        placed.sort(key=lambda o: o["z_index"])
        for idx, item in enumerate(placed):
            item["z_index"] = (idx + 1) * 100

        # 4. Проверка масштабирования под холст и математическое авто-центрирование
        if placed:
            min_x = min(item["x"] for item in placed)
            max_x = max(item["x"] + item["width"] for item in placed)
            min_y = min(item["y"] for item in placed)
            max_y = max(item["y"] + item["height"] for item in placed)

            scene_w = max_x - min_x
            scene_h = max_y - min_y

            max_allowed_w = cw - 80.0
            max_allowed_h = ch - 80.0

            if scene_w > max_allowed_w or scene_h > max_allowed_h:
                fit_scale = min(max_allowed_w / max(1.0, scene_w), max_allowed_h / max(1.0, scene_h))
                fit_scale = max(0.60, min(1.0, fit_scale))
                center_x = min_x + scene_w / 2.0
                center_y = min_y + scene_h / 2.0

                for item in placed:
                    item["scale"] = round(item["scale"] * fit_scale, 3)
                    item["width"] = round(item["width"] * fit_scale, 1)
                    item["height"] = round(item["height"] * fit_scale, 1)
                    item["x"] = round(center_x + (item["x"] - center_x) * fit_scale, 1)
                    item["y"] = round(center_y + (item["y"] - center_y) * fit_scale, 1)

                min_x = min(item["x"] for item in placed)
                max_x = max(item["x"] + item["width"] for item in placed)
                min_y = min(item["y"] for item in placed)
                max_y = max(item["y"] + item["height"] for item in placed)
                scene_w = max_x - min_x
                scene_h = max_y - min_y

            if layout_type == "under_headline":
                # Композиция центрируется в правой зоне холста (65%)
                target_cx = min(cw - scene_w / 2.0 - 40.0, max(cw * 0.55, cw * 0.65))
            else:
                # Строго по центру холста
                target_cx = cw / 2.0

            target_cy = ch * 0.52

            current_cx = min_x + scene_w / 2.0
            current_cy = min_y + scene_h / 2.0

            shift_x = target_cx - current_cx
            shift_y = target_cy - current_cy

            for item in placed:
                item["x"] = round(item["x"] + shift_x, 1)
                item["y"] = round(item["y"] + shift_y, 1)

        return placed

    def _get_scale(self, object_id: str = "", size: str = "l", canvas_format: Optional[str] = None) -> float:
        fmt = canvas_format or getattr(self, "_current_format", "1200x630")
        fmt_scales = self.FORMAT_SCALES.get(fmt, self.FORMAT_SCALES["1200x630"])
        return fmt_scales.get(size, 0.35)

    def _allocate_slots(
        self, main_objs: List[Dict[str, Any]], layout_type: str, canvas_format: str
    ) -> Tuple[Dict[str, Tuple[Dict[str, Any], bool, float, float]], List[Tuple[float, float]]]:
        """Распределение объектов по пространственным слотам изометрической композиции."""
        fmt_data = self.SLOT_TEMPLATES.get(canvas_format, self.SLOT_TEMPLATES["1200x630"])
        layout_data = fmt_data.get(layout_type, fmt_data["clustered"])
        slots = layout_data["main"]
        slot_map = {s[0]: s for s in slots}

        bases = [o for o in main_objs if self.OBJECT_TYPES.get(o["object_id"]) == "base"]
        talls = [o for o in main_objs if self.OBJECT_TYPES.get(o["object_id"]) == "tall"]
        smalls = [o for o in main_objs if self.OBJECT_TYPES.get(o["object_id"]) == "small"]
        mediums = [o for o in main_objs if self.OBJECT_TYPES.get(o["object_id"], "medium") == "medium"]

        assigned: Dict[str, Tuple[Dict[str, Any], bool, float, float]] = {}

        if layout_type == "offset":
            # Левый верхний фланг: высокий вертикальный акцент
            if talls:
                s = slot_map["zone_left_tall"]
                assigned["zone_left_tall"] = (talls.pop(0), False, s[1], s[2])
            elif mediums:
                s = slot_map["zone_left_tall"]
                assigned["zone_left_tall"] = (mediums.pop(0), False, s[1], s[2])

            # Правый фланг: базовое плато с поверхностью
            if bases:
                s = slot_map["zone_right_base"]
                assigned["zone_right_base"] = (bases.pop(0), False, s[1], s[2])
                surf_cand = [m for m in mediums if m["object_id"] == "phone"]
                if surf_cand:
                    mediums.remove(surf_cand[0])
                    s1 = slot_map["zone_right_surface_1"]
                    assigned["zone_right_surface_1"] = (surf_cand[0], True, s1[1], s1[2])
                elif smalls:
                    s1 = slot_map["zone_right_surface_1"]
                    assigned["zone_right_surface_1"] = (smalls.pop(0), True, s1[1], s1[2])
                if smalls:
                    s2 = slot_map["zone_right_surface_2"]
                    assigned["zone_right_surface_2"] = (smalls.pop(0), True, s2[1], s2[2])
            elif mediums:
                s = slot_map["zone_right_base"]
                assigned["zone_right_base"] = (mediums.pop(0), False, s[1], s[2])
                if smalls:
                    s1 = slot_map["zone_right_surface_1"]
                    assigned["zone_right_surface_1"] = (smalls.pop(0), True, s1[1], s1[2])

            # Центральный диагональный мост
            if mediums:
                s = slot_map["zone_mid_bridge"]
                assigned["zone_mid_bridge"] = (mediums.pop(0), False, s[1], s[2])
            elif bases:
                s = slot_map["zone_mid_bridge"]
                assigned["zone_mid_bridge"] = (bases.pop(0), False, s[1], s[2])

            # Левый передний план
            if smalls:
                s = slot_map["zone_left_front"]
                assigned["zone_left_front"] = (smalls.pop(0), False, s[1], s[2])
            elif mediums:
                s = slot_map["zone_left_front"]
                assigned["zone_left_front"] = (mediums.pop(0), False, s[1], s[2])

        else:
            # clustered и under_headline: классическая 3-зонная модель Figma

            # Зона 1: Базовое плато на левом фланге (книга/папка) + предметы на поверхности
            if bases:
                s = slot_map["zone1_base"]
                assigned["zone1_base"] = (bases.pop(0), False, s[1], s[2])
                surf_cand = [m for m in mediums if m["object_id"] == "phone"]
                if surf_cand:
                    mediums.remove(surf_cand[0])
                    s1 = slot_map["zone1_surface_1"]
                    assigned["zone1_surface_1"] = (surf_cand[0], True, s1[1], s1[2])
                elif smalls:
                    s1 = slot_map["zone1_surface_1"]
                    assigned["zone1_surface_1"] = (smalls.pop(0), True, s1[1], s1[2])
                if smalls:
                    s2 = slot_map["zone1_surface_2"]
                    assigned["zone1_surface_2"] = (smalls.pop(0), True, s2[1], s2[2])
            elif mediums:
                s = slot_map["zone1_base"]
                assigned["zone1_base"] = (mediums.pop(0), False, s[1], s[2])
                if smalls:
                    s1 = slot_map["zone1_surface_1"]
                    assigned["zone1_surface_1"] = (smalls.pop(0), True, s1[1], s1[2])

            # Зона 3: Правый контрбаланс заднего плана (лампа/ваза)
            if talls:
                s = slot_map["zone3_tall"]
                assigned["zone3_tall"] = (talls.pop(0), False, s[1], s[2])

            # Зона 2: Центральный связующий мост (наушники/кошелек)
            if mediums:
                s = slot_map["zone2_bridge"]
                assigned["zone2_bridge"] = (mediums.pop(0), False, s[1], s[2])
            elif bases:
                s = slot_map["zone2_bridge"]
                assigned["zone2_bridge"] = (bases.pop(0), False, s[1], s[2])

            # Зона 3 (передний план): малый или средний аксессуар (ручка/монета)
            if smalls:
                s = slot_map["zone3_front"]
                assigned["zone3_front"] = (smalls.pop(0), False, s[1], s[2])
            elif mediums:
                s = slot_map["zone3_front"]
                assigned["zone3_front"] = (mediums.pop(0), False, s[1], s[2])

        # Распределение оставшихся объектов по резервным слотам
        remaining = bases + talls + mediums + smalls
        for sname, rx, ry, surf in slots:
            if sname not in assigned and remaining:
                assigned[sname] = (remaining.pop(0), surf, rx, ry)

        return assigned, layout_data["bg"]

    def _layout_by_slots(
        self,
        main_objs: List[Dict[str, Any]],
        bg_objs: List[Dict[str, Any]],
        cw: float,
        ch: float,
        size: str,
        layout_type: str,
    ) -> List[Dict[str, Any]]:
        """Размещение объектов по 3-зонным слотам изометрической композиции Figma."""
        canvas_format = getattr(self, "_current_format", "1200x630")
        assigned_main, bg_slots = self._allocate_slots(main_objs, layout_type, canvas_format)
        placed: List[Dict[str, Any]] = []

        for sname, (obj, on_surface, rx, ry) in assigned_main.items():
            scale = self._get_scale(obj["object_id"], size, canvas_format)
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale
            gx = rx * cw
            gy = ry * ch
            pos_x = round(gx - (w / 2.0), 1)
            pos_y = round(gy - h, 1)

            placed.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": "main",
                "x": pos_x,
                "y": pos_y,
                "scale": scale,
                "rotation": 0.0,
                "on_surface": on_surface,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        for i, bg in enumerate(bg_objs):
            pos = bg_slots[i % len(bg_slots)]
            scale = self._get_scale(bg["object_id"], size, canvas_format)
            w = bg.get("width", 400) * scale
            h = bg.get("height", 400) * scale
            gx = pos[0] * cw
            gy = pos[1] * ch
            pos_x = round(gx - (w / 2.0), 1)
            pos_y = round(gy - h, 1)

            placed.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": bg["object_id"],
                "name_ru": bg.get("name_ru", bg["object_id"]),
                "size": size,
                "state": "bg",
                "x": pos_x,
                "y": pos_y,
                "scale": scale,
                "rotation": 0.0,
                "on_surface": False,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        return placed

    def _layout_clustered(
        self,
        main_objs: List[Dict[str, Any]],
        bg_objs: List[Dict[str, Any]],
        cw: float,
        ch: float,
        size: str,
        table_cx: Optional[float] = None,
        table_cy: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Центральный изометрический остров со слотовой иерархией Figma."""
        return self._layout_by_slots(main_objs, bg_objs, cw, ch, size, "clustered")

    def _layout_under_headline(
        self, main_objs: List[Dict[str, Any]], bg_objs: List[Dict[str, Any]], cw: float, ch: float, size: str
    ) -> List[Dict[str, Any]]:
        """Правая зона холста со слотовой изометрической иерархией Figma, свободная зона слева под заголовок."""
        return self._layout_by_slots(main_objs, bg_objs, cw, ch, size, "under_headline")

    def _layout_offset(
        self, main_objs: List[Dict[str, Any]], bg_objs: List[Dict[str, Any]], cw: float, ch: float, size: str
    ) -> List[Dict[str, Any]]:
        """Динамический изометрический каскад (контрбаланс) по канону Figma."""
        return self._layout_by_slots(main_objs, bg_objs, cw, ch, size, "offset")
