import math
import uuid
from typing import List, Dict, Any, Tuple, Optional


class LayoutEngine:
    """Интеллектуальный слотовый движок изометрической компоновки.
    
    Решает ключевые проблемы компоновки:
    1. Привязка объектов по нижней точке касания стола (Bottom-Center Ground Plane)
       вместо левого верхнего угла bounding box.
    2. Типология объектов: базовые плато (Книга, Папка) в центре, вертикальные
       акценты (Лампа, Ваза) сзади, малые спутники (Ручка, Монета, Пазл) вокруг.
    3. Z-Index строго по изометрической глубине (Ground Y): чем ближе подошва
       к зрителю, тем выше слой.
    """

    FORMAT_SPECS = {
        "1200x630": {"width": 1200, "height": 630, "ground_ratio_y": 0.82},
        "1000x1000": {"width": 1000, "height": 1000, "ground_ratio_y": 0.75},
        "800x1200": {"width": 800, "height": 1200, "ground_ratio_y": 0.70},
    }

    # Классификация объектов библиотеки
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
    # Сохраняет строгие пропорции между всеми объектами ТЗ
    FORMAT_SCALES = {
        "1200x630": {"l": 0.35, "s": 0.70},
        "1000x1000": {"l": 0.38, "s": 0.76},
        "800x1200": {"l": 0.32, "s": 0.64},
    }

    # Для обратной совместимости
    BASE_SCALES = FORMAT_SCALES

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

        # 1. Сортировка объектов по смысловой роли для распределения по слотам
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

        # 3. Расчет Z-Index по реальной экранной высоте подошвы (Ground Y)
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
        """Центральный изометрический остров со слотовой иерархией."""
        result = []

        # Центр стола на холсте
        if table_cx is None:
            table_cx = cw * 0.50
        if table_cy is None:
            table_cy = ch * 0.76

        # Изометрические коэффициенты смещения (угол 30 градусов)
        cos30 = 0.866
        sin30 = 0.500

        # Разделяем главные объекты по типам: база, вертикали, средние, малые
        hero_obj = None
        tall_objs = []
        medium_objs = []
        small_objs = []

        for obj in main_objs:
            obj_type = self.OBJECT_TYPES.get(obj["object_id"], "medium")
            if obj_type == "base" and not hero_obj:
                hero_obj = obj
            elif obj_type == "tall":
                tall_objs.append(obj)
            elif obj_type == "small":
                small_objs.append(obj)
            else:
                medium_objs.append(obj)

        # Если нет базового плато, берем первый крупный объект как Hero
        if not hero_obj:
            if medium_objs:
                hero_obj = medium_objs.pop(0)
            elif tall_objs:
                hero_obj = tall_objs.pop(0)
            elif small_objs:
                hero_obj = small_objs.pop(0)

        # Расчет безопасных динамических отступов от габаритов центрального Hero
        hero_scale = self._get_scale(hero_obj["object_id"], size) if hero_obj else 0.45
        hero_w = (hero_obj.get("width", 500) if hero_obj else 500) * hero_scale
        hero_h = (hero_obj.get("height", 500) if hero_obj else 500) * hero_scale
        hero_hw = hero_w / 2.0
        hero_hh = hero_h / 2.0

        def get_slot_coords(obj: Dict[str, Any], slot_name: str, state: str) -> Tuple[float, float]:
            scale = self._get_scale(obj["object_id"], size)
            if state == "bg":
                scale *= 0.88
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale
            hw = w / 2.0
            hh = h / 2.0

            if slot_name == "hero":
                return (table_cx, table_cy)

            # Безопасный зазор для исключения наложения теней (shadow clipping)
            clearance = 55.0

            if slot_name == "mid_left":
                dx = hero_hw + hw + clearance
                dy = 20.0
                return (table_cx - dx, table_cy - dy)

            elif slot_name == "mid_right":
                dx = hero_hw + hw + clearance
                dy = 15.0
                return (table_cx + dx, table_cy - dy)

            elif slot_name == "back_left":
                dx = (hero_hw * 0.75) + (hw * 0.85) + clearance
                dy = (hero_hh * 0.70) + (hh * 0.40) + 40.0
                return (table_cx - dx * cos30, table_cy - dy)

            elif slot_name == "back_right":
                dx = (hero_hw * 0.75) + (hw * 0.85) + clearance
                dy = (hero_hh * 0.70) + (hh * 0.40) + 35.0
                return (table_cx + dx * cos30, table_cy - dy + 10)

            elif slot_name == "front_left":
                if obj["object_id"] == "pen":
                    dx = hero_hw * 0.65 + 30.0
                    dy = hero_hh * 0.40 + 30.0
                    return (table_cx - dx, table_cy + dy)
                else:
                    dx = (hero_hw * 0.75) + (hw * 0.85) + clearance
                    dy = (hero_hh * 0.50) + (hh * 0.50) + 40.0
                    return (table_cx - dx * cos30, table_cy + dy * sin30)

            elif slot_name == "front_right":
                if obj["object_id"] == "pen":
                    dx = hero_hw * 0.65 + 30.0
                    dy = hero_hh * 0.40 + 30.0
                    return (table_cx + dx, table_cy + dy)
                else:
                    dx = (hero_hw * 0.75) + (hw * 0.85) + clearance
                    dy = (hero_hh * 0.50) + (hh * 0.50) + 40.0
                    return (table_cx + dx * cos30, table_cy + dy * sin30)

            return (table_cx, table_cy)

        occupied_slots = []

        def place_at_slot(obj: Dict[str, Any], slot_name: str, state: str):
            gx, gy = get_slot_coords(obj, slot_name, state)
            scale = self._get_scale(obj["object_id"], size)
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale

            # Выравнивание: X по центру, Y по подошве к ground_y
            pos_x = round(gx - (w / 2), 1)
            pos_y = round(gy - h, 1)

            rotation = 0.0
            on_surface = False
            if obj["object_id"] == "pen":
                on_surface = True

            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": state,
                "x": pos_x,
                "y": pos_y,
                "scale": scale,
                "rotation": rotation,
                "on_surface": on_surface,
                "width": round(w, 1),
                "height": round(h, 1),
            })
            occupied_slots.append(slot_name)

        # 1. Ставим Hero в центр основания
        if hero_obj:
            place_at_slot(hero_obj, "hero", "main")

        # 2. Высокие вертикальные акценты (Лампа, Ваза) ставим СЗАДИ базы
        back_slot_names = ["back_left", "back_right"]
        for tall in tall_objs:
            for sname in back_slot_names:
                if sname not in occupied_slots:
                    place_at_slot(tall, sname, "main")
                    break

        # 3. Средние объекты (Телефон, Наушники, Кошелек) ставим по флангам и передней диагонали
        side_slot_names = ["mid_left", "front_right", "mid_right", "front_left", "back_right"]
        for med in medium_objs:
            for sname in side_slot_names:
                if sname not in occupied_slots:
                    place_at_slot(med, sname, "main")
                    break

        # 4. Малые объекты (Ручка, Монета, Пазл) ставим на передний план или фланги
        front_slot_names = ["front_left", "front_right", "mid_left", "mid_right"]
        for sm in small_objs:
            for sname in front_slot_names:
                if sname not in occupied_slots:
                    place_at_slot(sm, sname, "main")
                    break

        # 5. Фоновые монохромные силуэты формируют глубину сзади
        bg_dx = hero_hw + 160.0
        bg_dy = hero_hh + 80.0
        bg_slots = [
            (table_cx - bg_dx * cos30, table_cy - bg_dy - 50),
            (table_cx + bg_dx * cos30, table_cy - bg_dy - 40),
            (table_cx, table_cy - bg_dy - 90),
            (table_cx - bg_dx - 60, table_cy - 40),
            (table_cx + bg_dx + 60, table_cy - 30),
        ]
        for i, bg in enumerate(bg_objs):
            pos = bg_slots[i % len(bg_slots)]
            scale = self._get_scale(bg["object_id"], size)
            w = bg.get("width", 400) * scale
            h = bg.get("height", 400) * scale
            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": bg["object_id"],
                "name_ru": bg.get("name_ru", bg["object_id"]),
                "size": size,
                "state": "bg",
                "x": round(pos[0] - (w / 2), 1),
                "y": round(pos[1] - h, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        return result

    def _layout_under_headline(
        self, main_objs: List[Dict[str, Any]], bg_objs: List[Dict[str, Any]], cw: float, ch: float, size: str
    ) -> List[Dict[str, Any]]:
        """Правая зона холста со слотовой изометрической иерархией, свободная зона слева под заголовок."""
        return self._layout_clustered(
            main_objs=main_objs,
            bg_objs=bg_objs,
            cw=cw,
            ch=ch,
            size=size,
            table_cx=cw * 0.65,
            table_cy=ch * 0.76,
        )

    def _layout_offset(
        self, main_objs: List[Dict[str, Any]], bg_objs: List[Dict[str, Any]], cw: float, ch: float, size: str
    ) -> List[Dict[str, Any]]:
        """Диагональный каскад из верхнего левого в нижний правый угол."""
        result = []
        all_objs = main_objs + bg_objs
        total = len(all_objs)
        if total == 0:
            return result

        # Линия диагонального стола
        start_x, start_y = cw * 0.22, ch * 0.40
        end_x, end_y = cw * 0.80, ch * 0.85

        for i, obj in enumerate(all_objs):
            t = (i + 0.5) / total
            is_bg = obj.get("state") == "bg"

            # Изометрическое колебание
            lateral_offset = 60 * math.sin(i * 2.1)
            gx = start_x + (end_x - start_x) * t + lateral_offset
            gy = start_y + (end_y - start_y) * t + (-30 if is_bg else 15)

            scale = self._get_scale(obj["object_id"], size)
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale

            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": obj["state"],
                "x": round(gx - (w / 2), 1),
                "y": round(gy - h, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        return result
