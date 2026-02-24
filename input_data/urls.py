from django.urls import path

# views 패키지(폴더)를 임포트합니다. __init__.py 덕분에 함수들을 바로 쓸 수 있습니다.
from input_data import views

app_name = "input_data"

urlpatterns = [
    #  데이터 홈 (대시보드 형태)
    path("", views.input_home, name="input_home"),
    # Scenario 목록 전용 URL (반드시 동적 URL보다 위에 위치)
    path("scenarios/", views.scenario_list, name="scenario_list"),
    path("scenarios/create/", views.scenario_create, name="scenario_create"),
    path(
        "scenarios/delete/<str:scenario_id>/",
        views.scenario_delete,
        name="scenario_delete",
    ),
    path(
        "scenario/create-base/",
        views.create_base_scenario_view,
        name="create_base_scenario",
    ),
    path(
        "scenarios/dashboard/<str:scenario_id>/",
        views.scenario_dashboard,
        name="scenario_dashboard",
    ),
    # Proforma Schedule  - views/proforma.py 에 정의된 함수들
    path("proforma/list/", views.proforma_list, name="proforma_list"),
    path("proforma/detail/", views.proforma_detail, name="proforma_detail"),
    path("proforma/create/", views.proforma_create, name="proforma_create"),
    path("proforma/upload/", views.proforma_upload, name="proforma_upload"),
    path(
        "proforma/template/", views.proforma_template_download, name="proforma_template"
    ),
    path("cascading/create/", views.cascading_create, name="cascading_create"),
    path("long_range/list/", views.long_range_list, name="long_range_list"),
    # AJAX용
    # Input List (Common)
    # 동적 데이터 조회: /input/schedule/proforma/ 등 형태
    # 상단에 위치하면 안됨(다른 URL과 충돌 가능성)
    path("<str:group_name>/<str:model_name>/", views.input_list, name="input_list"),
]
