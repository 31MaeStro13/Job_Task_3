from rest_framework import serializers
from .models import Composition, CustomPalette


class CustomPaletteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomPalette
        fields = [
            "name",
            "bg_light",
            "bg_mid",
            "bg_dark",
            "obj_accent_1",
            "obj_accent_2",
            "obj_accent_3",
            "stroke",
            "white",
        ]


class ComponentItemSerializer(serializers.Serializer):
    object_id = serializers.CharField()
    state = serializers.ChoiceField(choices=["main", "bg"], default="main")
    size = serializers.ChoiceField(choices=["l", "s"], required=False, allow_null=True)


class PlacedObjectSerializer(serializers.Serializer):
    id = serializers.CharField()
    object_id = serializers.CharField()
    name_ru = serializers.CharField(required=False)
    size = serializers.ChoiceField(choices=["l", "s"], default="l")
    state = serializers.ChoiceField(choices=["main", "bg"], default="main")
    x = serializers.FloatField()
    y = serializers.FloatField()
    scale = serializers.FloatField(default=1.0)
    rotation = serializers.FloatField(default=0.0)
    z_index = serializers.IntegerField(default=0)
    width = serializers.FloatField(required=False)
    height = serializers.FloatField(required=False)


class MetaphorComposeSerializer(serializers.Serializer):
    metaphor = serializers.CharField(max_length=500)
    format = serializers.ChoiceField(choices=["1200x630", "1000x1000", "800x1200"], default="1200x630")
    size = serializers.ChoiceField(choices=["l", "s"], default="l")
    palette = serializers.CharField(default="purple")
    layout = serializers.ChoiceField(choices=["under_headline", "offset", "clustered"], required=False, allow_null=True)
    use_bg_objects = serializers.BooleanField(default=True)
    custom_palette = serializers.DictField(required=False, allow_null=True)


class ManualComposeSerializer(serializers.Serializer):
    components = ComponentItemSerializer(many=True)
    format = serializers.ChoiceField(choices=["1200x630", "1000x1000", "800x1200"], default="1200x630")
    size = serializers.ChoiceField(choices=["l", "s"], default="l")
    palette = serializers.CharField(default="purple")
    layout = serializers.ChoiceField(choices=["under_headline", "offset", "clustered"], default="clustered")
    custom_palette = serializers.DictField(required=False, allow_null=True)


class UpdateCompositionSerializer(serializers.Serializer):
    objects = PlacedObjectSerializer(many=True)
    format = serializers.ChoiceField(choices=["1200x630", "1000x1000", "800x1200"], default="1200x630")
    size = serializers.ChoiceField(choices=["l", "s"], default="l")
    palette = serializers.CharField(default="purple")
    custom_palette = serializers.DictField(required=False, allow_null=True)


class RecolorSerializer(serializers.Serializer):
    objects = PlacedObjectSerializer(many=True)
    from_palette = serializers.CharField(default="purple")
    to_palette = serializers.CharField(default="purple")
    format = serializers.ChoiceField(choices=["1200x630", "1000x1000", "800x1200"], default="1200x630")
    custom_palette = serializers.DictField(required=False, allow_null=True)


class CompositionModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Composition
        fields = "__all__"
