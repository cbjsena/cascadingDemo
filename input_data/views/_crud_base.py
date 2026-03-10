"""
시나리오 기반 목록 조회 + 모달 추가 + 체크박스 삭제 패턴 화면을 위한 공통 모듈
공통 로직을 이 모듈에 모아 두고 config 딕셔너리만 정의하면 뷰 함수가 자동 생성.

■ 작동 원리 (팩토리 + 클로저 패턴)
  1. 서버 시작 시 (모듈 로드 시점)
     ┌──────────────────────────────────────────────────┐
     │ # cost.py                                        │
     │canal_fee_list = scenario_crud_view({ ...config })│
     │                  ─────────────┬──────────────────│
     │                               │                  │
     │          scenario_crud_view()가 내부에 view() 함수를│
     │            정의하고, config를 클로저로 캡처한 뒤 반환  │
     │                               │                  │
     │   canal_fee_list ← view (일반 함수처럼 동작)        │
     └──────────────────────────────────────────────────┘

  2. URL 매핑 (urls.py)
     path("cost/canal-fee/", views.canal_fee_list, name="canal_fee_list")
     → Django는 canal_fee_list를 일반 뷰 함수로 인식

  3. 요청 처리 (런타임)
     HTTP Request → canal_fee_list(request)
       │
       ├─ POST action="delete"
       │    → _handle_delete(): 체크박스로 선택된 pk 삭제 → redirect
       │
       ├─ POST action="save"
       │    → _handle_save(): 모달 폼 데이터 파싱 → DB 저장 → redirect
       │    ├─ unique_fields 설정 시: exists() 중복 체크 → create() (중복 skip)
       │    └─ lookup_fields 설정 시: update_or_create() (upsert)
       │
       └─ GET
            → _handle_get(): 시나리오/검색 필터 → queryset → render

■ 새 화면 추가 방법
  1. 템플릿 HTML 작성 (기존 템플릿 복사 후 필드만 변경)
  2. 뷰 파일에 config 딕셔너리 정의
  3. urls.py에 path() 추가
  4. menus.py에 메뉴 항목 추가

■ 현재 화면은 하나의 URL에서 GET(목록) + POST(생성·삭제)를 모두 처리한다.
  Django의 ListView는 GET 전용이라 POST 처리를 위해 FormMixin을 조합하면 복잡
"""

import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuSection,
)
from input_data.models import ScenarioInfo


# =========================================================
# 1. DELETE 처리 (공통)
# =========================================================
def _handle_delete(request, *, model, url_name, scenario_id):
    """
    체크박스로 선택된 행을 삭제한다.

    HTML 테이블의 각 행에 <input name="selected_pks" value="{{ item.pk }}">가 있고,
    Delete 버튼 클릭 시 이 값들이 POST로 전송된다.

    흐름: selected_pks 수집 → Model.objects.filter(pk__in=pks).delete() → redirect
    """
    pks = request.POST.getlist("selected_pks")
    if pks:
        deleted_count, _ = model.objects.filter(pk__in=pks).delete()
        label = model._meta.verbose_name
        messages.success(request, f"{deleted_count} {label}(s) deleted.")
    return _redirect_with_scenario(url_name, scenario_id)


# =========================================================
# 2. SAVE 처리 (공통)
# =========================================================
def _handle_save(request, *, config, scenario_id):
    """
    모달(Add Row) 폼의 POST 데이터를 파싱하여 DB에 저장한다.

    ■ POST name 규칙
      모달의 각 input은 "new_{post_key}_{index}" 형태이다.
      예: new_vessel_code_0, new_direction_0, new_canal_fee_0
      → index(여기서는 "0")로 같은 행의 필드를 묶는다.

    ■ 저장 방식 (config에서 결정)
      A) unique_fields 설정 시:
         exists()로 중복 체크 → 없으면 create(), 있으면 skip + 경고 메시지
         예: TSCost — 동일 (scenario, base_year_month, lane, port) 조합은 1개만 허용

      B) lookup_fields + defaults_fields 설정 시:
         update_or_create()로 upsert (있으면 update, 없으면 create)
         예: CharterCost — (scenario, vessel_code, hire_from_date)가 같으면 update

    ■ config["fields"] 구조
      [
          {"post_key": "new_vessel_code", "model_field": "vessel_code", "required": True},
          {"post_key": "new_canal_fee",   "model_field": "canal_fee",   "required": True},
      ]
      - post_key: HTML input의 name prefix (_{idx} 자동 추가)
      - model_field: Django ORM 필드명 (Model.objects.create()에 전달)
      - required: True이면 빈 값일 때 해당 행을 건너뜀 (기본값: True)
    """
    model = config["model"]
    fields_def = config["fields"]
    label = config.get("label", model._meta.verbose_name)

    # ---- Step 1: POST에서 인덱스 수집 ----
    # 첫 번째 필드의 post_key를 기준으로 "new_vessel_code_0" → "0" 추출
    first_key = fields_def[0]["post_key"]
    prefix_indices = set()
    for key in request.POST:
        if key.startswith(f"{first_key}_"):
            prefix_indices.add(key[len(first_key) + 1 :])

    created = 0
    duplicated = 0

    # ---- Step 2: 각 인덱스(행)별로 필드 파싱 → row 딕셔너리 구성 ----
    for idx in sorted(prefix_indices):
        row = {}
        all_required_ok = True

        for fdef in fields_def:
            val = request.POST.get(f"{fdef['post_key']}_{idx}", "").strip()
            if fdef.get("required", True) and not val:
                all_required_ok = False
                break
            row[fdef["model_field"]] = val if val else None

        if not all_required_ok or not scenario_id:
            continue

        # ---- Step 3: DB 저장 ----
        unique_fields = config.get("unique_fields")
        if unique_fields:
            # 방식 A: 중복 체크 → create (중복이면 skip)
            lookup = {"scenario_id": scenario_id}
            for uf in unique_fields:
                lookup[uf] = row[uf]
            if model.objects.filter(**lookup).exists():
                duplicated += 1
                continue
            model.objects.create(scenario_id=scenario_id, **row)
            created += 1
        else:
            # 방식 B: update_or_create (upsert)
            lookup_fields = config.get("lookup_fields", [])
            defaults_fields = config.get("defaults_fields", [])
            lookup = {"scenario_id": scenario_id}
            for lf in lookup_fields:
                lookup[lf] = row[lf]
            defaults = {df: row[df] for df in defaults_fields}
            model.objects.update_or_create(**lookup, defaults=defaults)
            created += 1

    # ---- Step 4: 결과 메시지 ----
    if created:
        messages.success(request, f"{created} {label}(s) added.")
    if duplicated:
        messages.warning(
            request,
            f"{duplicated} {label}(s) skipped (already exists in this scenario).",
        )

    return _redirect_with_scenario(config["url_name"], scenario_id)


# =========================================================
# 2-b. CSV 다운로드 (공통)
# =========================================================
def _handle_csv_download(request, *, config, scenario_id):
    """
    현재 화면에 표시된 데이터(시나리오 필터 적용)를 CSV 파일로 다운로드한다.

    config["csv_map"]: common/csv_configs.py에 정의된 튜플 리스트
      [(db_column_name, model_field, required), ...]
      - db_column_name : CSV 헤더로 사용
      - model_field    : "scenario_code"이면 obj.scenario.code 출력,
                         그 외에는 getattr(obj, model_field) 출력
    """
    csv_map = config.get("csv_map", [])
    if not csv_map:
        messages.warning(request, "CSV export is not configured.")
        return _redirect_with_scenario(config["url_name"], scenario_id)

    # 쿼리셋 구성 (화면과 동일한 필터)
    queryset = config["queryset_fn"]()
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)

    # CSV 생성
    output = io.StringIO()
    output.write("\ufeff")  # BOM (Excel 한글 깨짐 방지)
    writer = csv.writer(output)

    # 헤더: DB 컬럼명 사용
    writer.writerow([col[0] for col in csv_map])

    # 데이터
    for obj in queryset:
        row = []
        for db_col, model_field, _required in csv_map:
            if model_field == "scenario_code":
                val = obj.scenario.code
            else:
                val = getattr(obj, model_field, None)
            row.append("" if val is None else str(val))
        writer.writerow(row)

    # 파일명: {page_title}_{scenario_code 또는 all}.csv
    page_title = config["page_title"].replace(" ", "_").lower()
    filename = f"{page_title}_{scenario_id or 'all'}.csv"

    response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# =========================================================
# 2-c. CSV 업로드 (공통)
# =========================================================
def _handle_csv_upload(request, *, config, scenario_id):
    """
    CSV 파일을 업로드하여 DB에 저장한다.

    CSV 파일의 첫 행은 헤더(무시), 두 번째 행부터 데이터.
    각 행의 컬럼 순서는 config["csv_map"]와 동일해야 한다.
    첫 번째 컬럼(scenario_code)은 무시하고, POST의 scenario_id를 사용한다.

    config["csv_map"]: common/csv_configs.py에 정의된 튜플 리스트
      [(db_column_name, model_field, required), ...]

    저장 방식은 _handle_save와 동일 (unique_fields → create, lookup_fields → upsert).
    """
    csv_map = config.get("csv_map", [])
    if not csv_map:
        messages.warning(request, "CSV import is not configured.")
        return _redirect_with_scenario(config["url_name"], scenario_id)

    csv_file = request.FILES.get("csv_file")
    if not csv_file:
        messages.error(request, "No file selected.")
        return _redirect_with_scenario(config["url_name"], scenario_id)

    if not csv_file.name.endswith(".csv"):
        messages.error(request, "Please upload a .csv file.")
        return _redirect_with_scenario(config["url_name"], scenario_id)

    if not scenario_id:
        messages.error(request, "Please select a scenario before uploading.")
        return _redirect_with_scenario(config["url_name"], scenario_id)

    model = config["model"]
    label = config.get("label", model._meta.verbose_name)

    try:
        # CSV 파일 읽기 (BOM 제거)
        content = csv_file.read().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content))
        header_row = next(reader, None)  # 첫 행 (헤더) 건너뜀
        if not header_row:
            messages.error(request, "CSV file is empty.")
            return _redirect_with_scenario(config["url_name"], scenario_id)

        # csv_map에서 첫 번째(scenario_code)를 제외한 컬럼 매핑
        # csv_map[0]은 항상 ("scenario_code", "scenario_code", False) → 업로드 시 무시
        data_columns = csv_map[1:]  # [(db_col, model_field, required), ...]

        created = 0
        duplicated = 0
        skipped = 0

        for row_num, row in enumerate(reader, start=2):
            if not row or all(cell.strip() == "" for cell in row):
                continue  # 빈 행 건너뜀

            # 첫 번째 컬럼(scenario_code) 무시, 나머지 컬럼 → model_field 매핑
            if len(row) < len(csv_map):
                skipped += 1
                continue

            obj_data = {}
            all_required_ok = True

            for i, (db_col, model_field, required) in enumerate(data_columns):
                val = row[i + 1].strip() if (i + 1) < len(row) else ""
                if not val:
                    obj_data[model_field] = None
                else:
                    obj_data[model_field] = val
                if required and not val:
                    all_required_ok = False
                    break

            if not all_required_ok:
                skipped += 1
                continue

            # DB 저장 (save 로직과 동일)
            unique_fields = config.get("unique_fields")
            if unique_fields:
                lookup = {"scenario_id": scenario_id}
                for uf in unique_fields:
                    lookup[uf] = obj_data.get(uf)
                if model.objects.filter(**lookup).exists():
                    duplicated += 1
                    continue
                model.objects.create(scenario_id=scenario_id, **obj_data)
                created += 1
            else:
                lookup_fields = config.get("lookup_fields", [])
                defaults_fields = config.get("defaults_fields", [])
                lookup = {"scenario_id": scenario_id}
                for lf in lookup_fields:
                    lookup[lf] = obj_data.get(lf)
                defaults = {df: obj_data.get(df) for df in defaults_fields}
                model.objects.update_or_create(**lookup, defaults=defaults)
                created += 1

        if created:
            messages.success(request, f"{created} {label}(s) imported from CSV.")
        if duplicated:
            messages.warning(
                request,
                f"{duplicated} {label}(s) skipped (already exists).",
            )
        if skipped:
            messages.warning(request, f"{skipped} row(s) skipped (invalid data).")

    except Exception as e:
        messages.error(request, f"CSV import failed: {e}")

    return _redirect_with_scenario(config["url_name"], scenario_id)


# =========================================================
# 3. GET 처리 (공통)
# =========================================================
def _handle_get(request, *, config):
    """
    목록 조회 (GET 요청) 처리.

    흐름:
      1. URL 파라미터에서 scenario_id, search 추출
      2. config["queryset_fn"]()으로 기본 QuerySet 생성
      3. scenario_id 필터 적용
      4. extra_search_fields 필터 적용 (base_year_month 등)
      5. search_filter_fn으로 텍스트 검색 필터 적용
      6. extra_context로 모달 드롭다운용 추가 데이터 로드 (ports, lanes 등)
      7. context 구성 → render
    """
    # ---- Step 1: 검색 파라미터 추출 ----
    scenario_id = request.GET.get("scenario_id", "")
    search = request.GET.get("search", "").strip()
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    # ---- Step 2: 기본 QuerySet ----
    queryset = config["queryset_fn"]()

    # ---- Step 3: 시나리오 필터 ----
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)

    # ---- Step 4: 추가 검색 필드 필터 (예: base_year_month) ----
    search_params = {"scenario_id": scenario_id, "search": search}
    extra_context = {}

    for ef in config.get("extra_search_fields", []):
        val = request.GET.get(ef["param"], "").strip()
        if val:
            queryset = queryset.filter(**{ef["filter_kwarg"]: val})
        search_params[ef["param"]] = val
        extra_context[ef["param"]] = val

    # ---- Step 5: 텍스트 검색 필터 ----
    if search and "search_filter_fn" in config:
        queryset = config["search_filter_fn"](queryset, search)

    # ---- Step 6: 추가 context (모달 드롭다운용 데이터) ----
    for key, loader_fn in config.get("extra_context", {}).items():
        try:
            # 함수가 scenario_id 파라미터를 받을 수 있는지 확인
            import inspect

            sig = inspect.signature(loader_fn)
            if "scenario_id" in sig.parameters:
                extra_context[key] = loader_fn(scenario_id=scenario_id)
            else:
                extra_context[key] = loader_fn()
        except Exception:
            # 에러 발생 시 파라미터 없이 호출
            extra_context[key] = loader_fn()

    # ---- Step 7: 템플릿 렌더링 ----
    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": config["menu_group"],
        "current_model": config["menu_item"],
        "page_title": config["page_title"],
        "items": queryset,
        "scenarios": scenarios,
        "search": search,
        "search_params": search_params,
        "has_csv": bool(config.get("csv_map")),
        **extra_context,
    }
    return render(request, config["template"], context)


# =========================================================
# 4. 뷰 팩토리 (핵심)
# =========================================================
def scenario_crud_view(config):
    """
    config 딕셔너리를 받아 login_required 뷰 함수를 반환한다.

    ■ 작동 원리 (클로저 패턴)
      이 함수는 내부에 view()를 정의하고, config를 클로저로 캡처한 뒤 반환한다.
      반환된 view()는 일반 Django 뷰 함수와 동일하게 동작한다.

      canal_fee_list = scenario_crud_view({ ...config })
      ↓
      canal_fee_list는 view() 함수 자체 (config를 기억하고 있음)
      ↓
      urls.py에서 path("...", canal_fee_list) 로 등록 가능

    ■ 하나의 URL에서 GET(목록 조회) + POST(생성/삭제)를 모두 처리하는 패턴이므로,
      Django의 표준 CBV(ListView/CreateView 분리)보다 이 팩토리 패턴이 적합하다.

    Config Keys:
    ──────────────────────────────────────────────────────────
    [필수]
      model           : Django Model 클래스 (예: CanalFee)
      url_name        : URL reverse 이름 (예: "input_data:canal_fee_list")
      template        : 템플릿 경로 (예: "input_data/canal_fee_list.html")
      page_title      : 페이지 제목 (예: "Canal Fee")
      menu_group      : MenuGroup enum (예: MenuGroup.COST)
      menu_item       : MenuItem enum (예: MenuItem.CANAL_FEE)
      queryset_fn     : () → QuerySet. GET 시 기본 쿼리셋 반환 함수
      fields          : 모달 필드 정의 리스트. 각 항목:
                        {
                            "post_key": "new_vessel_code",  # HTML name prefix
                            "model_field": "vessel_code",   # ORM 필드명
                            "required": True,               # (기본 True)
                        }

    [저장 방식 — 둘 중 하나 선택]
      A) unique_fields   : list[str] — exists() 체크 → create (중복 skip)
      B) lookup_fields   : list[str] — update_or_create의 lookup 대상
         defaults_fields : list[str] — update_or_create의 defaults 대상

    [선택]
      view_name           : 디버깅용 함수명 (기본: url_name에서 추출)
      label               : 메시지용 레이블 (기본: model.verbose_name)
      search_filter_fn    : (qs, search) → QuerySet. 검색 필터
      extra_search_fields : 추가 검색 필드 리스트. 각 항목:
                            {"param": "base_year_month", "filter_kwarg": "base_year_month"}
      extra_context       : dict[str, () → Any]. 추가 context 데이터 로더
                            예: {"ports": lambda: MasterPort.objects.all()}
      csv_map             : common/csv_configs.py에 정의된 CSV 컬럼 매핑 리스트.
                            [(db_column_name, model_field, required), ...]
                            미지정 시 CSV 버튼이 표시되지 않음

    사용 예시:
      from common.csv_configs import CANAL_FEE_CSV_MAP

      canal_fee_list = scenario_crud_view({
          ...
          "csv_map": CANAL_FEE_CSV_MAP,
      })
    ──────────────────────────────────────────────────────────
    """

    @login_required
    def view(request):
        if request.method == "POST":
            action = request.POST.get("action")
            scenario_id = request.POST.get("scenario_id", "")

            if action == "delete":
                return _handle_delete(
                    request,
                    model=config["model"],
                    url_name=config["url_name"],
                    scenario_id=scenario_id,
                )
            elif action == "save":
                return _handle_save(request, config=config, scenario_id=scenario_id)
            elif action == "csv_download":
                return _handle_csv_download(
                    request, config=config, scenario_id=scenario_id
                )
            elif action == "csv_upload":
                return _handle_csv_upload(
                    request, config=config, scenario_id=scenario_id
                )

            # fallback: 알 수 없는 action → 목록으로 돌아감
            return _redirect_with_scenario(config["url_name"], scenario_id)

        # GET → 목록 조회
        return _handle_get(request, config=config)

    # 디버깅 시 스택트레이스에 함수명이 표시되도록 설정
    # (기본값은 모두 "view"이므로 구분이 어려움)
    view.__name__ = config.get("view_name", config["url_name"].split(":")[-1])
    view.__qualname__ = view.__name__
    return view


# =========================================================
# Helper
# =========================================================
def _redirect_with_scenario(url_name, scenario_id):
    """redirect 시 scenario_id를 URL 파라미터로 유지한다."""
    url = reverse(url_name)
    if scenario_id:
        return redirect(f"{url}?scenario_id={scenario_id}")
    return redirect(url)
