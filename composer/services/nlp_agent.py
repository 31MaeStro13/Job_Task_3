import re
from typing import Dict, List, Any, Optional
from .library_service import LibraryService


class NlpMetaphorAgent:
    """ИИ-агент семантического анализа метафор и заголовков.
    
    Отвечает строго за семантику (Сценарий 1):
    1. Анализирует тему, контекст и эмоциональный тон метафоры.
    2. Выбирает наиболее подходящие 3–5 объектов из векторной библиотеки.
    3. Разделяет их на Главные (Main, цветные доминанты) и Фоновые (Bg, монохромная глубина).
    4. Подбирает рекомендуемый композиционный архетип (under_headline, offset, clustered).
    """

    def __init__(self, library_service: LibraryService):
        self.library = library_service

    def analyze(self, metaphor: str, use_bg_objects: bool = True) -> Dict[str, Any]:
        text_clean = metaphor.lower().strip()
        words = re.findall(r"\b[a-zA-Zа-яА-ЯёЁ0-9]{3,}\b", text_clean)

        scores: Dict[str, float] = {}
        matched_keywords: Dict[str, List[str]] = {}

        # 1. Расчет семантического сходства по базе ключевых слов объектов
        for obj_id, meta in self.library.objects.items():
            score = 0.0
            matched = []
            keywords = meta.get("keywords", [])
            name_ru = meta.get("name_ru", "").lower()

            for w in words:
                # Прямое совпадение с именем
                if w in name_ru or name_ru in w:
                    score += 5.0
                    matched.append(w)
                # Совпадение с ключевыми словами
                for kw in keywords:
                    if w in kw or kw in w:
                        score += 3.0
                        matched.append(kw)
                        break

            # Базовый вес категории
            base_weight = meta.get("weight", 0.7)
            scores[obj_id] = score * base_weight
            matched_keywords[obj_id] = matched

        # Сортировка по убыванию релевантности
        sorted_objs = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

        # Если явных совпадений нет — берем гармоничную универсальную тройку
        if sorted_objs[0][1] <= 0.0:
            selected_ids = ["lamp", "phone", "book", "headphones"]
            reason = "Прямых совпадений не обнаружено. Выбран сбалансированный универсальный сет рабочего пространства."
        else:
            # Отбираем объекты с положительным скором (от 3 до 5 объектов)
            positive = [obj_id for obj_id, s in sorted_objs if s > 0]
            if len(positive) < 3:
                # Дополняем логически совместимыми объектами
                for obj_id, _ in sorted_objs:
                    if obj_id not in positive:
                        positive.append(obj_id)
                    if len(positive) >= 3:
                        break
            selected_ids = positive[:5]
            matched_terms = []
            for oid in selected_ids:
                if matched_keywords.get(oid):
                    matched_terms.extend(matched_keywords[oid][:2])
            reason = f"Объекты подобраны по ключевым смыслам: {', '.join(set(matched_terms)) or 'контекстный анализ'}."

        # 2. Назначение ролей (Главные и Фоновые)
        components = []
        # Первые 1-2 объекта — главные цветные
        num_main = 2 if len(selected_ids) >= 3 else 1
        for i, obj_id in enumerate(selected_ids):
            meta = self.library.get_object_meta(obj_id) or {}
            if i < num_main or not use_bg_objects:
                state = "main"
            else:
                state = "bg"

            components.append({
                "object_id": obj_id,
                "name_ru": meta.get("name_ru", obj_id),
                "state": state,
                "score": scores.get(obj_id, 0.0),
            })

        # 3. Выбор рекомендуемого лейаута
        # Если текст похож на заголовок статьи/поста или содержит слова "как", "почему", "курс", "отчет"
        is_headline_pattern = any(w in text_clean for w in ["как", "заголовок", "курс", "статья", "пост", "отчет", "руководство", "гайды"])
        is_dynamic_pattern = any(w in text_clean for w in ["рост", "интеграция", "движение", "развитие", "путь", "процесс", "шаг"])

        if is_headline_pattern:
            layout = "under_headline"
            layout_reason = "Стиль 'Под заголовок': композиция смещена вправо, оставляя левую треть под текст заголовка."
        elif is_dynamic_pattern:
            layout = "offset"
            layout_reason = "Стиль 'Со смещением': диагональная динамическая композиция, подчеркивающая развитие темы."
        else:
            layout = "clustered"
            layout_reason = "Стиль 'Собранно': цельная изометрическая композиция в центре холста."

        return {
            "metaphor": metaphor,
            "components": components,
            "recommended_layout": layout,
            "reasoning": f"{reason} {layout_reason}",
        }
