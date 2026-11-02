from django.urls import path
from .views import (
    index_view,
    ComponentsListView,
    PalettesListView,
    ComposeMetaphorView,
    ComposeManualView,
    UpdateCompositionView,
    RecolorView,
    ExportSvgView,
    SaveCompositionView,
    ListSavedCompositionsView,
)

urlpatterns = [
    path("", index_view, name="index"),
    path("api/components/", ComponentsListView.as_view(), name="components_list"),
    path("api/palettes/", PalettesListView.as_view(), name="palettes_list"),
    path("api/compose/metaphor/", ComposeMetaphorView.as_view(), name="compose_metaphor"),
    path("api/compose/manual/", ComposeManualView.as_view(), name="compose_manual"),
    path("api/composition/update/", UpdateCompositionView.as_view(), name="composition_update"),
    path("api/composition/recolor/", RecolorView.as_view(), name="composition_recolor"),
    path("api/composition/export/", ExportSvgView.as_view(), name="composition_export"),
    path("api/composition/save/", SaveCompositionView.as_view(), name="composition_save"),
    path("api/compositions/", ListSavedCompositionsView.as_view(), name="saved_compositions"),
]
