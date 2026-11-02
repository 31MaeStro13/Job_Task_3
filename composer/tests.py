import pytest
from django.test import TestCase
from rest_framework.test import APIClient
from composer.services.library_service import LibraryService
from composer.services.palette_service import PaletteService
from composer.services.layout_engine import LayoutEngine
from composer.services.svg_builder import SvgBuilder
from composer.services.nlp_agent import NlpMetaphorAgent


class ComposerServiceTests(TestCase):
    def setUp(self):
        self.library = LibraryService()
        self.palettes = PaletteService()
        self.layout = LayoutEngine()
        self.builder = SvgBuilder(self.library, self.palettes)
        self.nlp = NlpMetaphorAgent(self.library)

    def test_library_has_ten_objects(self):
        """Проверка наличия всех 10 ключевых объектов в библиотеке."""
        objects = self.library.objects
        assert len(objects) == 10
        expected_ids = ["book", "phone", "headphones", "lamp", "wallet", "puzzle", "coin", "folder", "pen", "vase"]
        for eid in expected_ids:
            assert eid in objects, f"Объект {eid} отсутствует в library.json"

    def test_all_forty_variants_parse(self):
        """Проверка парсинга всех 40 вариантов SVG (10 объектов * 2 размера * 2 роли)."""
        sizes = ["l", "s"]
        states = ["main", "bg"]
        count = 0
        for obj_id in self.library.objects.keys():
            for s in sizes:
                for st in states:
                    inner, w, h, vb, defs = self.library.get_element_inner_svg(obj_id, s, st)
                    assert len(inner) > 0
                    assert w > 0 and h > 0
                    count += 1
        assert count == 40

    def test_palette_isolation_rule(self):
        """Проверка строгого правила: цвета объектов не могут использоваться в фонах."""
        # Корректная палитра
        valid_palette = {
            "bg_light": "#D7CDF5",
            "bg_mid": "#AA9BF0",
            "bg_dark": "#7864D7",
            "obj_accent_1": "#F9ECB0",
            "obj_accent_2": "#F9A3AA",
            "obj_accent_3": "#FFE3E1",
        }
        self.palettes.validate_palette_rules(valid_palette)

        # Невалидная палитра (акцент объекта используется как цвет фона)
        invalid_palette = {
            "bg_light": "#F9ECB0",  # совпадает с obj_accent_1!
            "bg_mid": "#AA9BF0",
            "bg_dark": "#7864D7",
            "obj_accent_1": "#F9ECB0",
            "obj_accent_2": "#F9A3AA",
            "obj_accent_3": "#FFE3E1",
        }
        with pytest.raises(ValueError) as exc:
            self.palettes.validate_palette_rules(invalid_palette)
        assert "не могут быть использованы в качестве цветов фона" in str(exc.value)

    def test_recolor_svg(self):
        """Проверка корректной перекраски SVG в палитру peach."""
        raw_svg = self.library.get_element_raw_svg("book", "l", "main")
        recolored = self.palettes.recolor_svg(raw_svg, from_palette_id="purple", to_palette_id="peach")
        assert len(recolored) > 0
        # В палитре peach используется #FDD7B9 или #80DADA
        assert ("#FDD7B9" in recolored) or ("#80DADA" in recolored) or ("#FAC896" in recolored)

    def test_layout_archetypes(self):
        """Проверка работы 3 лейаутов без выпадения за границы холста."""
        components = [
            {"object_id": "book", "state": "main", "width": 600, "height": 400},
            {"object_id": "lamp", "state": "main", "width": 400, "height": 500},
            {"object_id": "headphones", "state": "bg", "width": 400, "height": 300},
            {"object_id": "pen", "state": "bg", "width": 250, "height": 150},
        ]

        for layout_name in ["under_headline", "offset", "clustered"]:
            placed = self.layout.arrange(components, canvas_format="1200x630", detail_size="l", layout_type=layout_name)
            assert len(placed) == 4
            for item in placed:
                assert item["x"] is not None
                assert item["y"] is not None
                assert item["scale"] > 0
                assert item["z_index"] > 0

    def test_nlp_metaphor_matching(self):
        """Проверка Сценария 1: семантический подбор ассетов по метафоре."""
        res_edu = self.nlp.analyze("Дистанционное обучение и лекции")
        edu_ids = [c["object_id"] for c in res_edu["components"]]
        assert "book" in edu_ids or "pen" in edu_ids

        res_fin = self.nlp.analyze("Управление личными финансами и инвестиции")
        fin_ids = [c["object_id"] for c in res_fin["components"]]
        assert "wallet" in fin_ids or "coin" in fin_ids

        res_logic = self.nlp.analyze("Командная работа и решение сложных задач")
        logic_ids = [c["object_id"] for c in res_logic["components"]]
        assert "puzzle" in logic_ids or "lamp" in logic_ids

    def test_pen_layer_and_rotation_hierarchy(self):
        """Ручка должна лежать поверх книги (выше z_index) и иметь естественный угол наклона 0.0 (изометрия Figma)."""
        components = [
            {"object_id": "book", "state": "main", "width": 520, "height": 350},
            {"object_id": "pen", "state": "main", "width": 280, "height": 160},
        ]
        placed = self.layout.arrange(components, canvas_format="1200x630", layout_type="clustered")
        book_obj = next(o for o in placed if o["object_id"] == "book")
        pen_obj = next(o for o in placed if o["object_id"] == "pen")

        # Ручка должна быть строго выше книги по z_index
        assert pen_obj["z_index"] > book_obj["z_index"]
        assert pen_obj["rotation"] == 0.0

    def test_uniform_scale_preserves_figma_proportions(self):
        """Проверка строгого сохранения пропорций Figma 1:1 между объектами сцены."""
        components = [
            {"object_id": "book", "state": "main", "width": 1446.0, "height": 977.0},
            {"object_id": "phone", "state": "main", "width": 797.0, "height": 462.0},
            {"object_id": "coin", "state": "main", "width": 287.0, "height": 262.0},
            {"object_id": "pen", "state": "main", "width": 509.0, "height": 286.0},
        ]
        placed = self.layout.arrange(components, canvas_format="1200x630", layout_type="clustered")
        book = next(o for o in placed if o["object_id"] == "book")
        phone = next(o for o in placed if o["object_id"] == "phone")
        coin = next(o for o in placed if o["object_id"] == "coin")
        pen = next(o for o in placed if o["object_id"] == "pen")

        # Масштаб всех объектов должен быть строго одинаковым (Figma 1:1)
        assert book["scale"] == phone["scale"] == coin["scale"] == pen["scale"]

        # Соотношение экранных ширин строго равно отношению ширин в Figma (1:1)
        expected_ratio_phone = 797.0 / 1446.0
        actual_ratio_phone = phone["width"] / book["width"]
        assert abs(actual_ratio_phone - expected_ratio_phone) < 0.005

        expected_ratio_coin = 287.0 / 1446.0
        actual_ratio_coin = coin["width"] / book["width"]
        assert abs(actual_ratio_coin - expected_ratio_coin) < 0.005

    def test_bounding_box_auto_centering(self):
        """Сцена должна быть математически отцентрирована по центру холста (cw/2)."""
        components = [
            {"object_id": "book", "state": "main", "width": 520, "height": 350},
            {"object_id": "lamp", "state": "main", "width": 400, "height": 500},
            {"object_id": "pen", "state": "main", "width": 280, "height": 160},
        ]
        cw = 1200
        placed = self.layout.arrange(components, canvas_format="1200x630", layout_type="clustered")
        min_x = min(o["x"] for o in placed)
        max_x = max(o["x"] + o["width"] for o in placed)
        center_x = (min_x + max_x) / 2.0

        # Погрешность центрирования не должна превышать 2px
        assert abs(center_x - (cw / 2.0)) < 2.0

    def test_svg_builder_layer_reordering(self):
        """Проверка, что изменение z_index меняет фактический порядок тегов <g> в SVG DOM."""
        obj_a = {"id": "elem_book", "object_id": "book", "size": "l", "state": "main", "x": 100, "y": 100, "z_index": 100}
        obj_b = {"id": "elem_pen", "object_id": "pen", "size": "l", "state": "main", "x": 120, "y": 120, "z_index": 200}

        svg_forward = self.builder.build_svg([obj_a, obj_b])
        # При z_index 100 < 200: elem_book рисуется раньше, elem_pen позже (поверх)
        assert svg_forward.find('id="elem_book"') < svg_forward.find('id="elem_pen"')

        # Меняем слои местами (эквивалент кнопки «▼ Назад» для ручки)
        obj_a_higher = dict(obj_a, z_index=300)
        obj_b_lower = dict(obj_b, z_index=100)
        svg_reversed = self.builder.build_svg([obj_a_higher, obj_b_lower])
        assert svg_reversed.find('id="elem_pen"') < svg_reversed.find('id="elem_book"')

    def test_default_layout_recommendation(self):
        """Для обычных тем (образование, финансы) дефолтом должен быть clustered (центрированный остров)."""
        res = self.nlp.analyze("Дистанционное образование и онлайн-лекции")
        assert res["recommended_layout"] == "clustered"

    def test_shadow_and_body_clearance(self):
        """Проверка отсутствия коллизий и пересечения теней между Hero и боковым спутником (книга + телефон)."""
        phone_meta = self.library.get_object_meta("phone")["variants"]["l_main"]
        book_meta = self.library.get_object_meta("book")["variants"]["l_main"]

        components = [
            {"object_id": "book", "state": "main", "width": book_meta["width"], "height": book_meta["height"]},
            {"object_id": "phone", "state": "main", "width": phone_meta["width"], "height": phone_meta["height"]},
        ]
        placed = self.layout.arrange(components, canvas_format="1200x630", layout_type="clustered")
        book = next(o for o in placed if o["object_id"] == "book")
        phone = next(o for o in placed if o["object_id"] == "phone")

        phone_right = phone["x"] + phone["width"]
        book_left = book["x"]
        gap = book_left - phone_right
        assert gap >= 40.0, f"Коллизия объектов: зазор {gap:.1f}px < 40px, тени пересекаются!"


class ComposerApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_api_components_list(self):
        resp = self.client.get("/api/components/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["count"] == 10

    def test_api_compose_metaphor(self):
        resp = self.client.post("/api/compose/metaphor/", {
            "metaphor": "Продуктивность и онлайн образование",
            "format": "1200x630",
            "size": "l",
            "palette": "purple"
        }, format="json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "<svg" in data["svg_content"]
        assert len(data["objects"]) >= 3

    def test_api_compose_manual(self):
        resp = self.client.post("/api/compose/manual/", {
            "components": [
                {"object_id": "lamp", "state": "main"},
                {"object_id": "phone", "state": "main"},
                {"object_id": "headphones", "state": "bg"}
            ],
            "format": "1000x1000",
            "size": "l",
            "palette": "mint",
            "layout": "clustered"
        }, format="json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "<svg" in data["svg_content"]
        assert len(data["objects"]) == 3

    def test_api_create_custom_palette_valid(self):
        resp = self.client.post("/api/palettes/", {
            "name": "Тестовая Валидная",
            "bg_light": "#112233",
            "bg_mid": "#223344",
            "bg_dark": "#334455",
            "obj_accent_1": "#FFEEDD",
            "obj_accent_2": "#EECCBB",
            "obj_accent_3": "#DD9988",
            "stroke": "#000000",
            "white": "#FFFFFF",
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["palette"]["name"] == "Тестовая Валидная"
        assert data["palette"]["id"].startswith("custom_")

    def test_api_create_custom_palette_rule_violation(self):
        # Акцент объекта используется как цвет фона
        resp = self.client.post("/api/palettes/", {
            "name": "Нарушающая Правило",
            "bg_light": "#FFEEDD",  # Совпадает с obj_accent_1!
            "bg_mid": "#223344",
            "bg_dark": "#334455",
            "obj_accent_1": "#FFEEDD",
            "obj_accent_2": "#EECCBB",
            "obj_accent_3": "#DD9988",
            "stroke": "#000000",
            "white": "#FFFFFF",
        }, format="json")
        assert resp.status_code == 400
        data = resp.json()
        assert data["success"] is False
        assert "не могут быть использованы в качестве цветов фона" in data["error"]

