from django.urls import path

from . import views

app_name = "simulation"

urlpatterns = [
    path("", views.simulation_list, name="simulation_list"),
    path("monitoring/", views.simulation_monitoring, name="simulation_monitoring"),
    path(
        "monitoring/data/",
        views.simulation_monitoring_data,
        name="simulation_monitoring_data",
    ),
    path("create/", views.simulation_create, name="simulation_create"),
    path("run/", views.simulation_run, name="simulation_run"),
    path("<int:pk>/cancel/", views.simulation_cancel, name="simulation_cancel"),
    path("<int:pk>/", views.simulation_detail, name="simulation_detail"),
    path("<int:pk>/delete/", views.simulation_delete, name="simulation_delete"),
]
