from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    # --- Swagger Schema & UI ---
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # --- Data APIs ---
    path("port/distance/", views.port_distance, name="port_distance"),
    path("proforma/options/", views.proforma_options, name="proforma_options"),
    path("proforma/info/", views.proforma_detail, name="proforma_detail"),
    path("vessel/list/", views.vessel_list, name="vessel_list"),
    path("vessel/options/", views.vessel_options, name="vessel_options"),
    path("vessel/lane/check/", views.vessel_lane_check, name="vessel_lane_check"),
]
