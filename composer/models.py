from django.db import models
import uuid


class Composition(models.Model):
    FORMAT_CHOICES = [
        ("1200x630", "1200x630 (Horizontal)"),
        ("1000x1000", "1000x1000 (Square)"),
        ("800x1200", "800x1200 (Portrait)"),
    ]

    SIZE_CHOICES = [
        ("l", "Large (High Detail)"),
        ("s", "Small (Simplified)"),
    ]

    LAYOUT_CHOICES = [
        ("under_headline", "Под заголовок (Свободно слева)"),
        ("offset", "Со смещением (Динамичный диагональный)"),
        ("clustered", "Собранно (Центральный изометрический)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, default="Новая композиция")
    metaphor = models.CharField(max_length=500, blank=True, default="")
    scenario = models.CharField(max_length=50, default="manual")  # metaphor | manual
    canvas_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default="1200x630")
    detail_size = models.CharField(max_length=5, choices=SIZE_CHOICES, default="l")
    palette = models.CharField(max_length=50, default="purple")
    layout_type = models.CharField(max_length=50, choices=LAYOUT_CHOICES, default="clustered")
    
    # JSON-описание расставленных элементов на холсте
    objects_data = models.JSONField(default=list, blank=True)
    
    # Финальный векторный SVG код
    svg_content = models.TextField(blank=True, default="")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Композиция"
        verbose_name_plural = "Композиции"

    def __str__(self):
        return f"{self.title} ({self.canvas_format}, {self.palette})"


class CustomPalette(models.Model):
    name = models.CharField(max_length=100)
    bg_light = models.CharField(max_length=20)
    bg_mid = models.CharField(max_length=20)
    bg_dark = models.CharField(max_length=20)
    obj_accent_1 = models.CharField(max_length=20)
    obj_accent_2 = models.CharField(max_length=20)
    obj_accent_3 = models.CharField(max_length=20)
    stroke = models.CharField(max_length=20, default="#181817")
    white = models.CharField(max_length=20, default="#FFFFFF")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
