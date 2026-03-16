"""
Master 데이터 관리 뷰 (Config 기반 공통 팩토리 패턴).

■ 작동 원리
  scenario_crud_view (시나리오 기반)와 동일한 팩토리 + 클로저 패턴이지만,
  시나리오 없이 동작하는 Master 테이블 전용 버전이다.

  master_trade_list = master_crud_view({ ...config })
  → 내부에서 view() 함수를 정의하고 config를 클로저로 캡처한 뒤 반환
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from input_data.models import BaseWeekPeriod, MasterLane, MasterPort, MasterTrade


# =========================================================
# Master 공통 팩토리
# =========================================================
def master_crud_view(config):
    """
    config 딕셔너리를 받아 Master CRUD 뷰 함수를 반환한다.

    Config Keys:
    ──────────────────────────────────────────────────────────
    [필수]
      model            : Django Model 클래스
      url_name         : URL reverse 이름 (예: "input_data:master_trade_list")
      template         : 템플릿 경로
      page_title       : 페이지 제목
      menu_item        : MenuItem enum
      pk_field         : DELETE 시 사용할 PK 필드명 (예: "trade_code")
      queryset_fn      : () → QuerySet (기본 정렬 포함)
      search_fields    : 검색 대상 필드 리스트 (icontains 적용)
      save_fn          : (request) → int : POST save 처리 함수, 생성 건수 반환
      serialize_fn     : (item) → dict : DataTables JSON 직렬화 함수

    [선택]
      label            : 메시지용 레이블 (기본: model.verbose_name)
      extra_filters    : AJAX 추가 필터 리스트
                         [{"param": "continent", "filter_kwarg": "continent_code__icontains"}]
      extra_context_fn : (request) → dict : GET 렌더링 시 추가 context
      dt_columns       : DataTables 정렬용 컬럼 매핑 리스트
    ──────────────────────────────────────────────────────────
    """

    @login_required
    def view(request):
        model = config["model"]
        url_name = config["url_name"]
        label = config.get("label", model._meta.verbose_name)

        # ── POST 처리 ──
        if request.method == "POST":
            action = request.POST.get("action")

            if action == "delete":
                pks = request.POST.getlist("selected_pks")
                if pks:
                    pk_field = config["pk_field"]
                    deleted_count, _ = model.objects.filter(
                        **{f"{pk_field}__in": pks}
                    ).delete()
                    messages.success(request, f"{deleted_count} {label}(s) deleted.")
                return redirect(url_name)

            elif action == "save":
                created = config["save_fn"](request)
                if created:
                    messages.success(request, f"{created} {label}(s) added.")
                return redirect(url_name)

        # ── AJAX 처리 (DataTables 서버사이드) ──
        if request.GET.get("draw"):
            return _handle_master_ajax(request, config)

        # ── GET 처리 (초기 페이지 로드) ──
        search = request.GET.get("search", "").strip()

        context = {
            "menu_structure": MENU_STRUCTURE,
            "creation_menu_structure": CREATION_MENU_STRUCTURE,
            "current_section": MenuSection.INPUT_MANAGEMENT,
            "current_group": MenuGroup.MASTER,
            "current_model": config["menu_item"],
            "page_title": config["page_title"],
            "search": search,
            "reset_url": reverse(url_name),
        }

        # 추가 context (예: Port의 continent_codes)
        extra_context_fn = config.get("extra_context_fn")
        if extra_context_fn:
            context.update(extra_context_fn(request))

        return render(request, config["template"], context)

    view.__name__ = config.get("view_name", config["url_name"].split(":")[-1])
    view.__qualname__ = view.__name__
    return view


def _handle_master_ajax(request, config):
    """Master DataTables AJAX 공통 처리."""
    search = (
        request.GET.get("search[value]", "").strip()
        or request.GET.get("search", "").strip()
    )

    queryset = config["queryset_fn"]()
    total_count = queryset.count()

    # 추가 필터 적용 (예: continent)
    for ef in config.get("extra_filters", []):
        val = request.GET.get(ef["param"], "").strip()
        if val:
            queryset = queryset.filter(**{ef["filter_kwarg"]: val})

    # 텍스트 검색
    if search:
        q = Q()
        for field in config["search_fields"]:
            q |= Q(**{f"{field}__icontains": search})
        queryset = queryset.filter(q)

    filtered_count = queryset.count()

    # 정렬
    dt_columns = config.get("dt_columns", [])
    order_col_idx = request.GET.get("order[0][column]")
    order_dir = request.GET.get("order[0][dir]", "asc")
    if order_col_idx and order_col_idx.isdigit() and dt_columns:
        idx = int(order_col_idx)
        if 0 <= idx < len(dt_columns) and dt_columns[idx]:
            col_name = dt_columns[idx]
            if order_dir == "desc":
                col_name = "-" + col_name
            queryset = queryset.order_by(col_name)

    # 페이징
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 50))
    items = queryset[start : start + length]

    data = [config["serialize_fn"](item) for item in items]

    return JsonResponse(
        {
            "draw": int(request.GET.get("draw", 0)),
            "recordsTotal": total_count,
            "recordsFiltered": filtered_count,
            "data": data,
        }
    )


# =========================================================
# Save 헬퍼: POST 데이터를 파싱하여 update_or_create 수행
# =========================================================
def _parse_and_save(request, *, model, fields, lookup_keys, defaults_keys):
    """
    모달 폼의 POST 데이터를 파싱하여 DB에 저장한다.

    Args:
        model: Django Model 클래스
        fields: POST 필드 정의 리스트
                [{"post_key": "new_trade_code", "model_field": "trade_code", "required": True}, ...]
        lookup_keys: update_or_create의 lookup 대상 model_field 리스트
        defaults_keys: update_or_create의 defaults 대상 model_field 리스트

    Returns:
        생성된 레코드 수
    """
    first_key = fields[0]["post_key"]
    prefix_indices = set()
    for key in request.POST:
        if key.startswith(f"{first_key}_"):
            prefix_indices.add(key[len(first_key) + 1 :])

    created = 0
    for idx in sorted(prefix_indices):
        row = {}
        all_required_ok = True
        for fdef in fields:
            val = request.POST.get(f"{fdef['post_key']}_{idx}", "").strip()
            if fdef.get("required", True) and not val:
                all_required_ok = False
                break
            row[fdef["model_field"]] = val if val else None

        if not all_required_ok:
            continue

        lookup = {k: row[k] for k in lookup_keys}
        defaults = {k: row[k] for k in defaults_keys if k in row}
        model.objects.update_or_create(**lookup, defaults=defaults)
        created += 1

    return created


# =========================================================
# 1. Trade Info
# =========================================================
def _save_trade(request):
    return _parse_and_save(
        request,
        model=MasterTrade,
        fields=[
            {"post_key": "new_trade_code", "model_field": "trade_code"},
            {"post_key": "new_trade_name", "model_field": "trade_name"},
            {
                "post_key": "new_from_continent",
                "model_field": "from_continent_code",
                "required": False,
            },
            {
                "post_key": "new_to_continent",
                "model_field": "to_continent_code",
                "required": False,
            },
        ],
        lookup_keys=["trade_code"],
        defaults_keys=["trade_name", "from_continent_code", "to_continent_code"],
    )


# =========================================================
# 2. Port Info
# =========================================================
def _save_port(request):
    return _parse_and_save(
        request,
        model=MasterPort,
        fields=[
            {"post_key": "new_port_code", "model_field": "port_code"},
            {"post_key": "new_port_name", "model_field": "port_name"},
            {
                "post_key": "new_continent_code",
                "model_field": "continent_code",
                "required": False,
            },
            {
                "post_key": "new_country_code",
                "model_field": "country_code",
                "required": False,
            },
        ],
        lookup_keys=["port_code"],
        defaults_keys=["port_name", "continent_code", "country_code"],
    )


def _port_extra_context(request):
    continent = request.GET.get("continent", "").strip()
    continent_codes = (
        MasterPort.objects.exclude(continent_code__isnull=True)
        .exclude(continent_code="")
        .values_list("continent_code", flat=True)
        .distinct()
        .order_by("continent_code")
    )
    return {"continent": continent, "continent_codes": continent_codes}


# =========================================================
# 3. Lane Info
# =========================================================
def _save_lane(request):
    return _parse_and_save(
        request,
        model=MasterLane,
        fields=[
            {"post_key": "new_lane_code", "model_field": "lane_code"},
            {"post_key": "new_lane_name", "model_field": "lane_name"},
            {
                "post_key": "new_service_type",
                "model_field": "vessel_service_type_code",
                "required": False,
            },
            {
                "post_key": "new_eff_from",
                "model_field": "effective_from_date",
                "required": False,
            },
            {
                "post_key": "new_eff_to",
                "model_field": "effective_to_date",
                "required": False,
            },
            {
                "post_key": "new_feeder_div",
                "model_field": "feeder_division_code",
                "required": False,
            },
        ],
        lookup_keys=["lane_code"],
        defaults_keys=[
            "lane_name",
            "vessel_service_type_code",
            "effective_from_date",
            "effective_to_date",
            "feeder_division_code",
        ],
    )


# =========================================================
# 4. Week Period
# =========================================================
def _save_week_period(request):
    return _parse_and_save(
        request,
        model=BaseWeekPeriod,
        fields=[
            {"post_key": "new_base_year", "model_field": "base_year"},
            {"post_key": "new_base_week", "model_field": "base_week"},
            {
                "post_key": "new_base_month",
                "model_field": "base_month",
                "required": False,
            },
            {"post_key": "new_week_start_date", "model_field": "week_start_date"},
            {"post_key": "new_week_end_date", "model_field": "week_end_date"},
        ],
        lookup_keys=["base_year", "base_week"],
        defaults_keys=["base_month", "week_start_date", "week_end_date"],
    )


master_trade_list = master_crud_view(
    {
        "model": MasterTrade,
        "url_name": "input_data:master_trade_list",
        "view_name": "master_trade_list",
        "template": "input_data/master_trade_list.html",
        "page_title": "Trade Info",
        "label": "trade",
        "menu_item": MenuItem.TRADE_INFO,
        "pk_field": "trade_code",
        "queryset_fn": lambda: MasterTrade.objects.all().order_by("trade_code"),
        "search_fields": ["trade_code", "trade_name"],
        "save_fn": _save_trade,
        "serialize_fn": lambda item: {
            "id": item.trade_code,
            "trade_code": item.trade_code,
            "trade_name": item.trade_name,
            "from_continent_code": item.from_continent_code or "-",
            "to_continent_code": item.to_continent_code or "-",
        },
        "dt_columns": [
            "",
            "",
            "trade_code",
            "trade_name",
            "from_continent_code",
            "to_continent_code",
        ],
    }
)


master_port_list = master_crud_view(
    {
        "model": MasterPort,
        "url_name": "input_data:master_port_list",
        "view_name": "master_port_list",
        "template": "input_data/master_port_list.html",
        "page_title": "Port Info",
        "label": "port",
        "menu_item": MenuItem.PORT_INFO,
        "pk_field": "port_code",
        "queryset_fn": lambda: MasterPort.objects.all().order_by("port_code"),
        "search_fields": ["port_code", "port_name"],
        "save_fn": _save_port,
        "serialize_fn": lambda item: {
            "id": item.port_code,
            "port_code": item.port_code,
            "port_name": item.port_name,
            "continent_code": item.continent_code or "-",
            "country_code": item.country_code or "-",
        },
        "extra_filters": [
            {"param": "continent", "filter_kwarg": "continent_code__icontains"},
        ],
        "extra_context_fn": _port_extra_context,
        "dt_columns": [
            "",
            "",
            "port_code",
            "port_name",
            "continent_code",
            "country_code",
        ],
    }
)


master_lane_list = master_crud_view(
    {
        "model": MasterLane,
        "url_name": "input_data:master_lane_list",
        "view_name": "master_lane_list",
        "template": "input_data/master_lane_list.html",
        "page_title": "Lane Info",
        "label": "lane",
        "menu_item": MenuItem.LANE_INFO,
        "pk_field": "lane_code",
        "queryset_fn": lambda: MasterLane.objects.all().order_by("lane_code"),
        "search_fields": ["lane_code", "lane_name"],
        "save_fn": _save_lane,
        "serialize_fn": lambda item: {
            "id": item.lane_code,
            "lane_code": item.lane_code,
            "lane_name": item.lane_name,
            "vessel_service_type_code": item.vessel_service_type_code or "-",
            "effective_from_date": (
                item.effective_from_date.strftime("%Y-%m-%d")
                if item.effective_from_date
                else "-"
            ),
            "effective_to_date": (
                item.effective_to_date.strftime("%Y-%m-%d")
                if item.effective_to_date
                else "-"
            ),
            "feeder_division_code": item.feeder_division_code or "-",
        },
        "dt_columns": [
            "",
            "",
            "lane_code",
            "lane_name",
            "vessel_service_type_code",
            "effective_from_date",
            "effective_to_date",
            "feeder_division_code",
        ],
    }
)

master_week_period_list = master_crud_view(
    {
        "model": BaseWeekPeriod,
        "url_name": "input_data:master_week_period_list",
        "view_name": "master_week_period_list",
        "template": "input_data/master_week_period_list.html",
        "page_title": "Week Period",
        "label": "week period",
        "menu_item": MenuItem.WEEK_PERIOD,
        "pk_field": "pk",
        "queryset_fn": lambda: BaseWeekPeriod.objects.all().order_by(
            "base_year", "base_week"
        ),
        "search_fields": ["base_year", "base_week"],
        "save_fn": _save_week_period,
        "serialize_fn": lambda item: {
            "id": item.id,
            "base_year": item.base_year,
            "base_week": item.base_week,
            "base_month": item.base_month or "-",
            "week_start_date": item.week_start_date.strftime("%Y-%m-%d"),
            "week_end_date": item.week_end_date.strftime("%Y-%m-%d"),
        },
        "dt_columns": [
            "",
            "",
            "base_year",
            "base_week",
            "base_month",
            "week_start_date",
            "week_end_date",
        ],
    }
)
