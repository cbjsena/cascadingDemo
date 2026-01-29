from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from django.urls import path

urlpatterns = [
    # --- Swagger Schema & UI ---
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # --- Data APIs ---

]
