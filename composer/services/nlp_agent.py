import os
import json
import re
from typing import Dict, List, Any, Optional
import requests
from .library_service import LibraryService


class NlpMetaphorAgent:
    """ИИ-агент семантического анализа метафор и заголовков.
    
    Поддерживает гибридный режим:
    1. Если в окружении есть GEMINI_API_KEY или OPENAI_API_KEY — вызывает современную LLM
       со структурированным JSON-выводом и семантическим обоснованием.
    2. В оффлайн-режиме (или при сбое сети) — мгновенно переключается на встроенный
       детерминированный семантический анализатор по онтологии тегов и ключевых слов.
    """

    def __init__(self, library_service: LibraryService):
        self.library = library_service

    def analyze(self, metaphor: str, use_bg_objects: bool = True) -> Dict[str, Any]:
        # 1. Попытка вызова внешней LLM
        llm_res = self._try_llm_analyze(metaphor, use_bg_objects)
        if llm_res:
            return llm_res

        # 2. Детерминированный локальный эвристический анализ
        return self._local_heuristic_analyze(metaphor, use_bg_objects)

    def _local_heuristic_analyze(self, metaphor: str, use_bg_objects: bool = True) -> Dict[str, Any]:
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
        # clustered — строгий дефолт для центрированной гармоничной композиции
        is_headline_pattern = any(w in text_clean for w in ["под заголовок", "заголовок слева", "баннер", "обложка с текстом", "место под текст"])
        is_dynamic_pattern = any(w in text_clean for w in ["динамика", "каскад", "диагональ"])

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

    def _try_llm_analyze(self, metaphor: str, use_bg_objects: bool) -> Optional[Dict[str, Any]]:
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if not gemini_key and not openai_key:
            return None

        system_prompt = (
            "Ты — ИИ арт-директор и композитор векторных иллюстраций.\n"
            "По заданной метафоре или заголовку выбери от 3 до 5 подходящих объектов из библиотеки "
            "и назначь им роли: 'main' (цветной доминант переднего плана) или 'bg' (монохромный силуэт глубины).\n\n"
            "Доступно ровно 10 объектов библиотеки (другие запрещены!):\n"
            "- book (Книга)\n- phone (Смартфон)\n- headphones (Наушники)\n- lamp (Лампа)\n"
            "- wallet (Кошелек)\n- puzzle (Пазлы)\n- coin (Монета)\n- folder (Папка)\n"
            "- pen (Ручка)\n- vase (Ваза с цветами)\n\n"
            "Схемы компоновки (layout):\n"
            "- clustered (ОСНОВНОЙ ВЫБОР ПО УМОЛЧАНИЮ: цельная центрированная композиция в центре холста)\n"
            "- under_headline (ИСКЛЮЧИТЕЛЬНО если прямо требуется баннер или заголовок с местом слева)\n"
            "- offset (динамичный диагональный каскад)\n\n"
            "Верни ответ СТРОГО в JSON:\n"
            "{\n"
            '  "components": [{"object_id": "book", "state": "main"}, {"object_id": "lamp", "state": "bg"}],\n'
            '  "layout": "clustered",\n'
            '  "reasoning": "Краткое арт-обоснование метафоры на русском (1-2 предложения)"\n'
            "}"
        )

        if gemini_key:
            try:
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
                headers = {
                    "x-goog-api-key": gemini_key,
                    "Content-Type": "application/json",
                }
                payload = {
                    "contents": [{"parts": [{"text": f"{system_prompt}\n\nМетафора: \"{metaphor}\""}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(text)
                    return self._format_llm_response(parsed, metaphor, use_bg_objects, engine="Gemini Flash AI")
            except Exception:
                pass

        elif openai_key:
            try:
                url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/chat/completions"
                payload = {
                    "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f'Метафора: "{metaphor}"'}
                    ],
                    "response_format": {"type": "json_object"}
                }
                resp = requests.post(url, json=payload, headers={"Authorization": f"Bearer {openai_key}"}, timeout=6)
                if resp.status_code == 200:
                    data = resp.json()
                    parsed = json.loads(data["choices"][0]["message"]["content"])
                    return self._format_llm_response(parsed, metaphor, use_bg_objects, engine="OpenAI AI")
            except Exception:
                pass

        return None

    def _format_llm_response(
        self,
        parsed: Dict[str, Any],
        metaphor: str,
        use_bg_objects: bool,
        engine: str = "LLM AI",
    ) -> Optional[Dict[str, Any]]:
        raw_comps = parsed.get("components", [])
        valid_comps = []
        seen = set()

        for c in raw_comps:
            oid = str(c.get("object_id", "")).lower()
            if oid in self.library.objects and oid not in seen:
                seen.add(oid)
                meta = self.library.get_object_meta(oid) or {}
                state = c.get("state", "main")
                if not use_bg_objects:
                    state = "main"
                elif state not in ["main", "bg"]:
                    state = "main"

                valid_comps.append({
                    "object_id": oid,
                    "name_ru": meta.get("name_ru", oid),
                    "state": state,
                    "score": 10.0,
                })

        if len(valid_comps) < 2:
            return None

        layout = parsed.get("layout", "clustered")
        if layout not in ["under_headline", "offset", "clustered"]:
            layout = "clustered"

        reasoning = parsed.get("reasoning", "Семантический подбор композиции.")

        return {
            "metaphor": metaphor,
            "components": valid_comps,
            "recommended_layout": layout,
            "reasoning": f"[{engine}] {reasoning}",
        }
