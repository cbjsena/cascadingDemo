from django.contrib.auth.decorators import login_required
from django.http import request
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.apps import apps
from django.utils import timezone

from common import messages as msg
from input_data.models import InputDataSnapshot

# 메뉴 구조 정의 (상수)
MENU_STRUCTURE = {
    "Schedule": [
        {"name": "Proforma Schedule", "key": "proforma_schedule"},
        {"name": "Long Range Schedule", "key": "long_range_schedule"},
    ],
    "Vessel": [
        {"name": "Vessel Info", "key": "vessel_info"},
        {"name": "Charter Cost", "key": "charter_cost"},
        {"name": "Vessel Capacity", "key": "vessel_capacity"},
    ],
    "Cost": [
        {"name": "Port Charge", "key": "port_charge"},
        {"name": "Exchange Rate", "key": "exchange_rate"},
        {"name": "Canal Fee", "key": "canal_fee"},
        {"name": "Distance", "key": "distance"},
        {"name": "Own Vessel Cost", "key": "own_vessel_cost"},
        {"name": "TS Cost", "key": "ts_cost"},
    ],
    "Bunker": [
        {"name": "Bunker Consumption Sea", "key": "bunker_consumption_sea"},
        {"name": "Bunker Consumption Port", "key": "bunker_consumption_port"},
        {"name": "Bunkering Port", "key": "bunkering_port"},
        {"name": "Bunker Price", "key": "bunker_price"},
    ],
    "ETS & Fuel EU": [
        {"name": "ETS TS Port", "key": "ets_ts_port"},
        {"name": "ETS Country", "key": "ets_country"},
        {"name": "ETS Bunker Consumption", "key": "ets_bunker_consumption"},
        {"name": "ETS EUA", "key": "ets_eua"},
        {"name": "FUEL EU", "key": "fuel_eu"},
        {"name": "Fuel EU Bunker", "key": "fuel_eu_bunker"},
        {"name": "Greenhouse Gas Target", "key": "greenhouse_gas_target"},
    ],
}

@login_required
def input_home(request):
    """
        대시보드: 데이터 현황 요약 및 최근 스냅샷 노출
        """
    # 1. 전체 스냅샷 개수
    total_snapshots = InputDataSnapshot.objects.count()

    # 2. 최근 생성된 스냅샷 5개 (테이블 표시용)
    recent_snapshots = InputDataSnapshot.objects.order_by('-created_at')[:5]

    # 3. 가장 최근 업데이트 날짜 (카드 표시용)
    if recent_snapshots.exists():
        last_update = recent_snapshots.first().created_at
    else:
        last_update = None

    context = {
        "menu_structure": MENU_STRUCTURE,  # 사이드바용
        "total_snapshots": total_snapshots,
        "recent_snapshots": recent_snapshots,
        "last_update": last_update,
    }
    return render(request, 'input_data/input_home.html', context)


@login_required
def input_list(request, group_name, model_name):
    # 나중에 실제 모델 데이터를 여기서 조회 (getattr 등 활용)
    context = {
        "menu_structure": MENU_STRUCTURE,
        "current_group": group_name,
        "current_model": model_name,
        "page_title": model_name.replace("_", " ").title()
    }
    return render(request, 'input_data/input_list.html', context)


@login_required
def snapshot_list(request):
    """
    저장된 입력 데이터 스냅샷 목록을 보여주는 뷰
    """
    # 최신 생성순으로 조회
    snapshots = InputDataSnapshot.objects.all().order_by('-created_at')

    # 기본값 계산 (Data ID, Base YM)
    default_data_id = _generate_default_data_id()
    default_base_ym = timezone.now().strftime('%Y%m')

    context = {
        # 사이드바 메뉴 렌더링을 위해 필요 (Context Processor를 설정했다면 생략 가능하지만 안전하게 포함)
        "menu_structure": MENU_STRUCTURE,
        "snapshots": snapshots,
        "default_data_id": default_data_id,
        "default_base_ym": default_base_ym,
    }
    return render(request, 'input_data/snapshot_list.html', context)


@login_required
@transaction.atomic
def snapshot_create(request):
    """
        스냅샷 생성 및 데이터 복제 처리 (POST)
        """
    if request.method == "POST":
        new_data_id = request.POST.get("data_id")
        source_data_id = request.POST.get("source_data_id")
        description = request.POST.get("description")
        base_ym = request.POST.get("base_year_month")

        # 1. 중복 ID 체크
        if InputDataSnapshot.objects.filter(data_id=new_data_id).exists():
            messages.error(request, msg.SNAPSHOT_ID_DUPLICATE.format(data_id=new_data_id))
            return redirect("input_data:snapshot_list")

        # 2. 새 스냅샷 생성
        new_snapshot = InputDataSnapshot.objects.create(
            data_id=new_data_id,
            description=description,
            base_year_month=base_ym,
            created_by=request.user,
            updated_by=request.user
        )

        # 3. 데이터 복제 (Source가 있는 경우)
        if source_data_id:
            try:
                _clone_snapshot_data(source_data_id, new_snapshot)
                messages.success(request, msg.SNAPSHOT_CLONE_SUCCESS.format(
                    data_id=new_data_id, source_id=source_data_id
                ))
            except Exception as e:
                # 에러 발생 시 롤백됨 (atomic)
                messages.error(request, msg.SNAPSHOT_CLONE_ERROR.format(error=str(e)))
                # 필요 시 new_snapshot은 자동 롤백되거나 여기서 처리
                return redirect("input_data:snapshot_list")
        else:
            messages.success(request, msg.SNAPSHOT_CREATE_SUCCESS.format(data_id=new_data_id))

        return redirect("input_data:snapshot_list")

    # GET 요청은 리스트로 리다이렉트 (팝업 방식이므로 별도 페이지 없음)
    return redirect("input_data:snapshot_list")


@login_required
@transaction.atomic
# [중요] GET 접근 차단 (주소창 입력 삭제 방지)
def snapshot_delete(request, data_id):
    """
    특정 스냅샷 삭제 처리
    """
    # 존재하지 않는 ID면 404 에러 발생
    snapshot = get_object_or_404(InputDataSnapshot, data_id=data_id)

    # 본인이 만든 것만 삭제
    is_creator = (snapshot.created_by == request.user)
    is_superuser = request.user.is_superuser
    if not (is_creator or is_superuser):
        messages.error(request, msg.PERMISSION_DENIED)
        return redirect("input_data:snapshot_list")

    try:
        # Cascade 설정에 의해 하위 데이터도 모두 삭제됨
        snapshot.delete()
        messages.success(request, msg.SNAPSHOT_DELETE_SUCCESS.format(data_id=data_id))
    except Exception as e:
        messages.error(request, msg.SNAPSHOT_DELETE_ERROR.format(error=str(e)))

    return redirect("input_data:snapshot_list")


def _clone_snapshot_data(source_id, target_snapshot):
    """
    [Helper] 모든 하위 모델의 데이터를 source_id에서 조회하여 target_snapshot으로 복제
    """
    # 복제할 대상 모델 리스트 (models.py에 정의된 하위 모델들)
    # 앱 설정에서 모든 모델을 가져와서 필터링하거나, 명시적으로 리스트업 가능
    # 여기서는 명시적 리스트업을 추천 (순서 제어 및 예외 제외 가능)

    # input_data 앱의 모든 모델 중 InputDataSnapshot을 제외한 모델들 가져오기
    app_config = apps.get_app_config('input_data')
    models_to_clone = [
        model for model in app_config.get_models()
        if model.__name__ != 'InputDataSnapshot'
    ]

    for model_class in models_to_clone:
        # 1. 원본 데이터 조회 (data_id가 source_id인 것들)
        # 주의: BaseModel을 상속받았으므로 data_id 필드가 있음
        # filter 조건: data_id_id (ForeignKey의 실제 컬럼값) = source_id
        original_objects = model_class.objects.filter(data_id=source_id)

        if not original_objects.exists():
            continue

        # 2. 대량 생성(bulk_create)을 위한 리스트 준비
        new_objects = []
        for obj in original_objects:
            # PK(id)는 None으로 설정하여 새로 생성되게 함
            obj.pk = None
            # FK(data_id)를 새 스냅샷 객체로 교체
            obj.data_id = target_snapshot
            new_objects.append(obj)

        # 3. 저장
        model_class.objects.bulk_create(new_objects)

def _generate_default_data_id():
    """
    오늘 날짜 기준 YYYYMMDD + 2자리 시퀀스(00~99) ID 생성
    예: 2025012901, 2025012902 ...
    """
    today_str = timezone.now().strftime('%Y%m%d')
    # 오늘 날짜로 시작하는 ID 중 가장 큰 것 검색
    last_snapshot = InputDataSnapshot.objects.filter(
        data_id__startswith=today_str
    ).order_by('-data_id').first()

    if last_snapshot:
        try:
            # 뒷 2자리만 잘라서 +1 (예: 2025012905 -> 05 -> 06)
            last_seq = int(last_snapshot.data_id[8:])
            new_seq = last_seq + 1
        except (ValueError, IndexError):
            # 형식이 다르면 00부터 다시 시작
            new_seq = 1
    else:
        new_seq = 1

    return f"{today_str}{new_seq:02d}"


