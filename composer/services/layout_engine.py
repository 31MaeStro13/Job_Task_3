import math
import uuid
from typing import List, Dict, Any, Tuple


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

    # Масштабирование объектов для гармоничного соотношения размеров
    BASE_SCALES = {
        "l": {
            "book": 0.36,
            "folder": 0.38,
            "lamp": 0.33,
            "vase": 0.38,
            "phone": 0.45,
            "headphones": 0.40,
            "wallet": 0.48,
            "puzzle": 0.50,
            "coin": 0.58,
            "pen": 0.55,
        },
        "s": {
            "book": 0.65,
            "folder": 0.68,
            "lamp": 0.60,
            "vase": 0.68,
            "phone": 0.75,
            "headphones": 0.70,
            "wallet": 0.75,
            "puzzle": 0.80,
            "coin": 0.85,
            "pen": 0.80,
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
        # Объекты с подошвой ниже на экране естественным образом перекрывают задние
        for item in placed:
            ground_y = item["y"] + item["height"]
            base_z = int(ground_y)
            # Главные объекты имеют приоритет перед фоновыми на той же глубине
            if item["state"] == "main":
                base_z += 200
            item["z_index"] = base_z

        placed.sort(key=lambda o: o["z_index"])
        return placed

    def _get_scale(self, object_id: str, size: str) -> float:
        scales = self.BASE_SCALES.get(size, self.BASE_SCALES["l"])
        return scales.get(object_id, 0.45)

    def _layout_clustered(
        self, main_objs: List[Dict[str, Any]], bg_objs: List[Dict[str, Any]], cw: float, ch: float, size: str
    ) -> List[Dict[str, Any]]:
        """Центральный изометрический остров со слотовой иерархией."""
        result = []

        # Центр стола на холсте
        table_cx = cw * 0.50
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

        # Слоты изометрического стола
        # (ground_x, ground_y)
        slots: Dict[str, Tuple[float, float]] = {
            "hero": (table_cx, table_cy),
            "back_left": (table_cx - 210 * cos30, table_cy - 210 * sin30 - 30),
            "back_right": (table_cx + 200 * cos30, table_cy - 200 * sin30 - 20),
            "front_left": (table_cx - 190 * cos30, table_cy + 190 * sin30 - 10),
            "front_right": (table_cx + 190 * cos30, table_cy + 190 * sin30 - 5),
            "mid_left": (table_cx - 240 * cos30, table_cy - 20),
            "mid_right": (table_cx + 240 * cos30, table_cy - 10),
        }

        occupied_slots = []

        def place_at_slot(obj: Dict[str, Any], slot_name: str, state: str):
            gx, gy = slots[slot_name]
            scale = self._get_scale(obj["object_id"], size)
            if state == "bg":
                scale *= 0.88
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale

            # Выравнивание: X по центру, Y по подошве к ground_y
            pos_x = round(gx - (w / 2), 1)
            pos_y = round(gy - h, 1)

            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": state,
                "x": pos_x,
                "y": pos_y,
                "scale": scale,
                "rotation": 0.0,
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

        # 3. Средние объекты (Телефон, Наушники, Кошелек) ставим по флангам
        side_slot_names = ["front_left", "mid_right", "mid_left", "front_right", "back_right"]
        for med in medium_objs:
            for sname in side_slot_names:
                if sname not in occupied_slots:
                    place_at_slot(med, sname, "main")
                    break

        # 4. Малые объекты (Ручка, Монета, Пазл) ставим на передний план
        front_slot_names = ["front_right", "front_left", "mid_right", "mid_left"]
        for sm in small_objs:
            for sname in front_slot_names:
                if sname not in occupied_slots:
                    place_at_slot(sm, sname, "main")
                    break

        # 5. Фоновые монохромные силуэты формируют глубину сзади
        bg_slots = [
            (table_cx - 280 * cos30, table_cy - 260 * sin30 - 40),
            (table_cx + 280 * cos30, table_cy - 250 * sin30 - 35),
            (table_cx, table_cy - 180),
            (table_cx - 360 * cos30, table_cy - 120),
            (table_cx + 360 * cos30, table_cy - 110),
        ]
        for i, bg in enumerate(bg_objs):
            pos = bg_slots[i % len(bg_slots)]
            scale = self._get_scale(bg["object_id"], size) * 0.85
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
        """Правая зона холста (центр X = 68%), левая треть чистая под заголовок."""
        result = []
        table_cx = cw * 0.70
        table_cy = ch * 0.78
        cos30 = 0.866
        sin30 = 0.500

        # Распределение главных объектов
        all_main = list(main_objs)
        # Находим hero
        hero_idx = 0
        for i, o in enumerate(all_main):
            if self.OBJECT_TYPES.get(o["object_id"]) == "base":
                hero_idx = i
                break
        hero = all_main.pop(hero_idx) if all_main else None

        # Размещение Hero
        if hero:
            scale = self._get_scale(hero["object_id"], size)
            w = hero.get("width", 400) * scale
            h = hero.get("height", 400) * scale
            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": hero["object_id"],
                "name_ru": hero.get("name_ru", hero["object_id"]),
                "size": size,
                "state": "main",
                "x": round(table_cx - (w / 2), 1),
                "y": round(table_cy - h, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        # Остальные главные объекты
        offsets = [
            (-170 * cos30, -170 * sin30 - 30), # Back Left
            (160 * cos30, -160 * sin30 - 20),  # Back Right
            (-160 * cos30, 160 * sin30),       # Front Left
            (170 * cos30, 170 * sin30),        # Front Right
        ]
        for i, obj in enumerate(all_main):
            ox, oy = offsets[i % len(offsets)]
            scale = self._get_scale(obj["object_id"], size)
            w = obj.get("width", 400) * scale
            h = obj.get("height", 400) * scale
            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": obj["object_id"],
                "name_ru": obj.get("name_ru", obj["object_id"]),
                "size": size,
                "state": "main",
                "x": round(table_cx + ox - (w / 2), 1),
                "y": round(table_cy + oy - h, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        # Фоновые силуэты сзади
        bg_offsets = [
            (-230 * cos30, -220 * sin30 - 40),
            (230 * cos30, -210 * sin30 - 30),
            (0, -160),
            (250 * cos30, 80),
        ]
        for i, bg in enumerate(bg_objs):
            ox, oy = bg_offsets[i % len(bg_offsets)]
            scale = self._get_scale(bg["object_id"], size) * 0.85
            w = bg.get("width", 400) * scale
            h = bg.get("height", 400) * scale
            result.append({
                "id": str(uuid.uuid4())[:8],
                "object_id": bg["object_id"],
                "name_ru": bg.get("name_ru", bg["object_id"]),
                "size": size,
                "state": "bg",
                "x": round(table_cx + ox - (w / 2), 1),
                "y": round(table_cy + oy - h, 1),
                "scale": scale,
                "rotation": 0.0,
                "width": round(w, 1),
                "height": round(h, 1),
            })

        return result

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

            scale = self._get_scale(obj["object_id"], size) * (0.85 if is_bg else 1.0)
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
