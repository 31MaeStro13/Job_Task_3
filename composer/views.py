from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Composition, CustomPalette
from .serializers import (
    MetaphorComposeSerializer,
    ManualComposeSerializer,
    UpdateCompositionSerializer,
    RecolorSerializer,
    CompositionModelSerializer,
    CustomPaletteSerializer,
)
from .services.library_service import LibraryService
from .services.palette_service import PaletteService
from .services.layout_engine import LayoutEngine
from .services.svg_builder import SvgBuilder
from .services.nlp_agent import NlpMetaphorAgent

# Инициализация сервисов (синглтоны)
library_service = LibraryService()
palette_service = PaletteService()
layout_engine = LayoutEngine()
svg_builder = SvgBuilder(library_service, palette_service)
nlp_agent = NlpMetaphorAgent(library_service)


def index_view(request):
    """Главная страница интерактивного векторного конструктора."""
    components = library_service.list_components()
    palettes = palette_service.palettes
    formats = library_service.formats
    return render(request, "index.html", {
        "components": components,
        "palettes": palettes,
        "formats": formats,
    })


class ComponentsListView(APIView):
    """Каталог доступных SVG компонентов библиотеки."""

    def get(self, request):
        items = library_service.list_components()
        return Response({
            "success": True,
            "count": len(items),
            "components": items,
        })


class PalettesListView(APIView):
    """Список цветовых палитр (базовые + сохраненные кастомные)."""

    def get(self, request):
        palettes = dict(palette_service.palettes)
        for cp in CustomPalette.objects.all():
            palettes[f"custom_{cp.id}"] = {
                "id": f"custom_{cp.id}",
                "name": cp.name,
                "bg_light": cp.bg_light,
                "bg_mid": cp.bg_mid,
                "bg_dark": cp.bg_dark,
                "obj_accent_1": cp.obj_accent_1,
                "obj_accent_2": cp.obj_accent_2,
                "obj_accent_3": cp.obj_accent_3,
                "stroke": cp.stroke,
                "white": cp.white,
            }
        return Response({
            "success": True,
            "palettes": palettes,
        })

    def post(self, request):
        """Загрузка / создание пользовательской палитры с валидацией дизайнерских правил."""
        serializer = CustomPaletteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        try:
            palette_service.validate_palette_rules(data)
        except ValueError as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        palette_obj = serializer.save()
        palette_id = f"custom_{palette_obj.id}"
        palette_dict = {
            "id": palette_id,
            "name": palette_obj.name,
            "bg_light": palette_obj.bg_light,
            "bg_mid": palette_obj.bg_mid,
            "bg_dark": palette_obj.bg_dark,
            "obj_accent_1": palette_obj.obj_accent_1,
            "obj_accent_2": palette_obj.obj_accent_2,
            "obj_accent_3": palette_obj.obj_accent_3,
            "stroke": palette_obj.stroke,
            "white": palette_obj.white,
        }
        palette_service.palettes[palette_id] = palette_dict

        return Response({
            "success": True,
            "palette": palette_dict,
        }, status=status.HTTP_201_CREATED)


class ComposeMetaphorView(APIView):
    """Сценарий 1: Генерация композиции по метафоре или заголовку через ИИ."""

    def post(self, request):
        serializer = MetaphorComposeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        metaphor = data["metaphor"]
        canvas_format = data["format"]
        detail_size = data["size"]
        palette = data["palette"]
        use_bg_objects = data["use_bg_objects"]
        custom_palette = data.get("custom_palette")

        # 1. Семантический анализ ИИ
        nlp_res = nlp_agent.analyze(metaphor, use_bg_objects=use_bg_objects)
        selected_components = nlp_res["components"]
        layout_type = data.get("layout") or nlp_res["recommended_layout"]

        # 2. Обогащение геометрическими размерами объектов
        comp_with_sizes = []
        for c in selected_components:
            oid = c["object_id"]
            meta = library_service.get_object_meta(oid) or {}
            # Получаем размеры для выбранного размера (L/S)
            raw_w, raw_h = 500.0, 500.0
            variants = meta.get("variants", {})
            var_key = f"{detail_size}_{c['state']}"
            if var_key in variants:
                raw_w = variants[var_key]["width"]
                raw_h = variants[var_key]["height"]
            
            c_copy = dict(c)
            c_copy["width"] = raw_w
            c_copy["height"] = raw_h
            comp_with_sizes.append(c_copy)

        # 3. Расстановка объектов через LayoutEngine
        placed_objects = layout_engine.arrange(
            components=comp_with_sizes,
            canvas_format=canvas_format,
            detail_size=detail_size,
            layout_type=layout_type,
        )

        # 4. Сборка валидного SVG
        svg_content = svg_builder.build_svg(
            placed_objects=placed_objects,
            canvas_format=canvas_format,
            palette_id=palette,
            custom_palette=custom_palette,
        )

        return Response({
            "success": True,
            "metaphor": metaphor,
            "reasoning": nlp_res["reasoning"],
            "layout": layout_type,
            "format": canvas_format,
            "size": detail_size,
            "palette": palette,
            "objects": placed_objects,
            "svg_content": svg_content,
        })


class ComposeManualView(APIView):
    """Сценарий 2: Сборка композиции из вручную выбранных компонентов."""

    def post(self, request):
        serializer = ManualComposeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        components = data["components"]
        canvas_format = data["format"]
        detail_size = data["size"]
        palette = data["palette"]
        layout_type = data["layout"]
        custom_palette = data.get("custom_palette")

        comp_with_sizes = []
        for c in components:
            oid = c["object_id"]
            meta = library_service.get_object_meta(oid) or {}
            variants = meta.get("variants", {})
            var_key = f"{detail_size}_{c['state']}"
            raw_w = variants.get(var_key, {}).get("width", 500.0)
            raw_h = variants.get(var_key, {}).get("height", 500.0)

            c_copy = dict(c)
            c_copy["name_ru"] = meta.get("name_ru", oid)
            c_copy["width"] = raw_w
            c_copy["height"] = raw_h
            comp_with_sizes.append(c_copy)

        placed_objects = layout_engine.arrange(
            components=comp_with_sizes,
            canvas_format=canvas_format,
            detail_size=detail_size,
            layout_type=layout_type,
        )

        svg_content = svg_builder.build_svg(
            placed_objects=placed_objects,
            canvas_format=canvas_format,
            palette_id=palette,
            custom_palette=custom_palette,
        )

        return Response({
            "success": True,
            "layout": layout_type,
            "format": canvas_format,
            "size": detail_size,
            "palette": palette,
            "objects": placed_objects,
            "svg_content": svg_content,
        })


class UpdateCompositionView(APIView):
    """Пересборка SVG после интерактивного перемещения, поворота или удаления пользователем."""

    def post(self, request):
        serializer = UpdateCompositionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        objects = data["objects"]
        canvas_format = data["format"]
        palette = data["palette"]
        custom_palette = data.get("custom_palette")

        svg_content = svg_builder.build_svg(
            placed_objects=objects,
            canvas_format=canvas_format,
            palette_id=palette,
            custom_palette=custom_palette,
        )

        return Response({
            "success": True,
            "svg_content": svg_content,
            "objects": objects,
        })


class RecolorView(APIView):
    """Мгновенная перекраска композиции в новую палитру с соблюдением правил."""

    def post(self, request):
        serializer = RecolorSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        objects = data["objects"]
        to_palette = data["to_palette"]
        canvas_format = data["format"]
        custom_palette = data.get("custom_palette")

        try:
            svg_content = svg_builder.build_svg(
                placed_objects=objects,
                canvas_format=canvas_format,
                palette_id=to_palette,
                custom_palette=custom_palette,
            )
            return Response({
                "success": True,
                "palette": to_palette,
                "svg_content": svg_content,
            })
        except ValueError as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExportSvgView(APIView):
    """Скачивание финальной векторной композиции в виде SVG файла."""

    def post(self, request):
        svg_content = request.data.get("svg_content", "")
        filename = request.data.get("filename", "illustration.svg")
        if not filename.endswith(".svg"):
            filename += ".svg"

        if not svg_content:
            return Response({"error": "Пустой SVG контент"}, status=status.HTTP_400_BAD_REQUEST)

        response = HttpResponse(svg_content, content_type="image/svg+xml; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SaveCompositionView(APIView):
    """Сохранение композиции в базу данных."""

    def post(self, request):
        serializer = CompositionModelSerializer(data=request.data)
        if serializer.is_valid():
            comp = serializer.save()
            return Response({"success": True, "id": str(comp.id)})
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ListSavedCompositionsView(APIView):
    """Получение сохраненных композиций из БД."""

    def get(self, request):
        qs = Composition.objects.all()[:20]
        data = CompositionModelSerializer(qs, many=True).data
        return Response({"success": True, "compositions": data})
