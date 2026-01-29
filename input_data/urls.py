from django.urls import path
from . import views

app_name = 'input_data'

urlpatterns = [
    # 데이터 홈 (대시보드 형태)
    path('', views.input_home, name='input_home'),

    # [추가] 스냅샷 목록 전용 URL (반드시 동적 URL보다 위에 위치)
    path('snapshots/', views.snapshot_list, name='snapshot_list'),
    path('snapshots/create/', views.snapshot_create, name='snapshot_create'),
    path('snapshots/delete/<str:data_id>/', views.snapshot_delete, name='snapshot_delete'),

    # 동적 데이터 조회: /input/schedule/proforma/ 등
    path('<str:group_name>/<str:model_name>/', views.input_list, name='input_list'),
]