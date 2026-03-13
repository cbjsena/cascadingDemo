from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from common import constants as const, messages as msg
from common.menus import (
    CREATION_MENU_STRUCTURE,
    MENU_STRUCTURE,
    MenuGroup,
    MenuItem,
    MenuSection,
)
from input_data.models import ProformaSchedule, ScenarioInfo
from input_data.services.proforma_service import ProformaService


@login_required
def proforma_create(request):
    """
    Proforma Schedule 생성 및 수정 View
    """
    service = ProformaService()

    # 초기 컨텍스트 설정
    context = {
        "scenarios": ScenarioInfo.objects.all().order_by("-created_at"),
        "rows": [],
        "header": {},
        "days": const.DAYS,
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.CREATION,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.PROFORMA_CREATE,
    }

    # =========================================================
    # [1] GET 요청 처리: 데이터 조회 (Edit Mode)
    # =========================================================
    if request.method == "GET":
        # URL 파라미터 수신 (예: ?scenario_id=2026021501&lane_code=KRP&...)
        q_scenario = request.GET.get("scenario_id")
        q_lane = request.GET.get("lane_code")
        q_proforma = request.GET.get("proforma_name")

        # 3가지 키가 모두 존재하면 DB 조회 (수정 모드 진입)
        if q_scenario and q_lane and q_proforma:
            try:
                # Service에 구현된 조회 메서드 호출
                fetched_header, fetched_rows = service.get_schedule_data(
                    q_scenario, q_lane, q_proforma
                )
                context["header"] = fetched_header
                context["rows"] = fetched_rows
            except Exception as e:
                # 조회 실패 시 에러 메시지 후 빈 폼 출력
                messages.error(
                    request, msg.LOAD_ERROR.format(target="Schedule", error=str(e))
                )

    # =========================================================
    # [2] POST 요청 처리: 데이터 조작 (Save, Add Row, etc.)
    # =========================================================
    elif request.method == "POST":
        action = request.POST.get("action")

        # 1. 화면 데이터 파싱 (모든 액션 공통)
        rows = service.parse_rows(request)
        header = service.parse_header(request)

        # 2. 액션별 로직 수행
        if action == "add_row":
            # 행 추가 후 재계산
            rows = service.add_row(rows, header.get("scenario_id"))

        elif action == "insert_row":
            try:
                idx = int(request.POST.get("selected_index", -1))
                rows = service.insert_row(rows, idx)
            except ValueError:
                pass

        elif action == "delete_row":
            indices = request.POST.getlist("row_check")
            rows = service.delete_rows(rows, indices)

        elif action == "new":
            # 화면 초기화 (리다이렉트)
            messages.info(request, msg.SCHEDULE_NEW_STARTED)
            return redirect("input_data:proforma_create")

        elif action == "calculate":
            # [기능] 계산만 수행하고 화면 갱신
            rows = service.calculate_schedule(rows, header)
            messages.info(request, msg.SCHEDULE_CALCULATED)

        elif action == "save":
            # 데이터 정합성을 위해 저장 전 재계산
            rows = service.calculate_schedule(rows, header)

            try:
                # DB 저장
                service.save_schedule(header, rows, request.user)
                messages.success(request, msg.SCHEDULE_SAVE_SUCCESS)

                # [UX 개선] 저장 후, 계속 편집 모드로 남기 위해 GET 파라미터를 유지한 채 리다이렉트
                # 이렇게 하면 저장 후에도 화면이 초기화되지 않고 방금 저장한 데이터를 다시 불러옵니다.
                base_url = reverse("input_data:proforma_create")
                query_string = f"?scenario_id={header.get('scenario_id')}&lane_code={header.get('lane_code')}&proforma_name={header.get('proforma_name')}"
                return redirect(f"{base_url}{query_string}")
            except Exception as e:
                messages.error(request, msg.SAVE_ERROR.format(error=str(e)))

        elif action == "export":
            # 엑셀 Export 기능 연결

            # Export 전에 최신 계산을 반영하고 싶다면:
            rows = service.calculate_schedule(rows, header)

            # 엑셀 파일 생성
            excel_file = service.export_proforma(header, rows)

            # 응답 생성
            response = HttpResponse(
                excel_file,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            filename = f"{header.get('lane_code', 'Lane')}_{header.get('proforma_name', 'Schedule')}.xlsx"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        elif action == "csv":
            # DB Upload용 CSV 다운로드

            # 1. 계산 최신화
            rows = service.calculate_schedule(rows, header)

            # 2. Service 호출
            # export_grid_csv:화면 , generate_db_csv: DB
            # csv_content = service.export_grid_csv(rows)
            csv_content = service.generate_db_csv(header, rows)

            # 3. 응답 생성
            response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
            filename = f"{header.get('lane_code', 'Lane')}_{header.get('proforma_name', 'Schedule')}.csv"
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
            return response

        elif action == "close":
            # 수정 모드였다면 상세 화면으로, 아니면 홈으로 (또는 목록으로)
            if header.get("scenario_id"):
                base_url = reverse("input_data:proforma_detail")
                query_string = f"?scenario_id={header.get('scenario_id')}&lane_code={header.get('lane_code')}&proforma_name={header.get('proforma_name')}"
                return redirect(f"{base_url}{query_string}")
            return redirect("input_data:proforma_list")

        # POST 처리 결과 Context 반영
        context["rows"] = rows
        context["header"] = header

        # (선택) 계산 후 Summary 정보가 있다면 추가
        # context["summary"] = service.calculate_summary(rows)

    return render(request, "input_data/proforma_create.html", context)


@login_required
def proforma_upload(request):
    """
    엑셀 파일 업로드 처리 View
    """
    if request.method == "POST" and request.FILES.get("excel_file"):
        excel_file = request.FILES["excel_file"]
        service = ProformaService()

        try:
            # 1. 엑셀 파싱 및 기본 데이터 처리
            header, rows = service.upload_excel(excel_file)

            # 2. [신규] Summary 계산
            # summary = service.calculate_summary(rows)

            # 3. Context 설정
            context = {
                "scenarios": ScenarioInfo.objects.all().order_by("-created_at"),
                "rows": rows,
                "header": header,
                # "summary": summary,  # <--- 화면으로 전달
                "days": const.DAYS,
                "menu_structure": MENU_STRUCTURE,
                "creation_menu_structure": CREATION_MENU_STRUCTURE,
                "current_section": MenuSection.CREATION,
                "current_group": MenuGroup.SCHEDULE,
                "current_model": MenuItem.PROFORMA_CREATE,
            }

            messages.success(request, msg.UPLOAD_SUCCESS)
            return render(request, "input_data/proforma_create.html", context)

        except Exception as e:
            messages.error(
                request, msg.LOAD_ERROR.format(target="excel upload", error=str(e))
            )
            return redirect("input_data:proforma_create")

    return redirect("input_data:proforma_create")


@login_required
def proforma_template_download(request):
    """
    Proforma Schedule 엑셀 템플릿 다운로드
    """
    service = ProformaService()

    # 엑셀 파일 생성 (BytesIO 객체 반환)
    excel_file = service.generate_template()

    # HTTP 응답 설정
    response = HttpResponse(
        excel_file,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    # 다운로드 파일명 설정
    response["Content-Disposition"] = 'attachment; filename="Proforma_Template.xlsx"'

    return response


@login_required
def proforma_list(request):
    """
    Proforma Schedule 목록 조회 및 검색
    """
    scenario_id = request.GET.get("scenario_id", "")
    lane_code = request.GET.get("lane_code", "")

    # 1. 기본 QuerySet
    queryset = (
        ProformaSchedule.objects.select_related("scenario")
        .annotate(port_count=Count("details"))
        .order_by("-scenario__created_at", "lane_id", "effective_from_date")
    )

    # 2. 검색 필터 적용
    if scenario_id:
        queryset = queryset.filter(scenario_id=scenario_id)
    if lane_code:
        queryset = queryset.filter(lane__lane_code__icontains=lane_code)

    # 3. 셀렉트 박스용 시나리오 전체 목록 가져오기
    scenarios = ScenarioInfo.objects.all().order_by("-created_at")

    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.PROFORMA_SCHEDULE,
        "proforma_list": queryset,
        "scenarios": scenarios,  # 반드시 필요함
        "search_params": {
            "scenario_id": scenario_id,
            "lane_code": lane_code,
        },
    }
    return render(request, "input_data/proforma_list.html", context)


@login_required
def proforma_detail(request):
    """
    Proforma Schedule 상세 조회 View (Read-Only)
    """
    service = ProformaService()

    # 1. 파라미터 수신
    q_scenario = request.GET.get("scenario_id")
    q_lane = request.GET.get("lane_code")
    q_proforma = request.GET.get("proforma_name")

    # 2. 데이터 조회 (Service 재사용)
    if q_scenario and q_lane and q_proforma:
        try:
            header, rows = service.get_schedule_data(q_scenario, q_lane, q_proforma)
        except Exception as e:
            messages.error(request, msg.LOAD_ERROR.format(error=str(e)))
            return redirect("input_data:proforma_list")
    else:
        messages.error(request, msg.INVALID_PARAMETERS)
        return redirect("input_data:proforma_list")

    # 3. Context 구성
    context = {
        "menu_structure": MENU_STRUCTURE,
        "creation_menu_structure": CREATION_MENU_STRUCTURE,
        "current_section": MenuSection.INPUT_MANAGEMENT,
        "current_group": MenuGroup.SCHEDULE,
        "current_model": MenuItem.PROFORMA_SCHEDULE,
        "header": header,
        "rows": rows,
        # 권한 체크 로직을 위해 User 정보 전달 (Template에서 분기 처리 가능)
        "can_edit": request.user.is_superuser,  # 예시: 슈퍼유저만 수정 가능
    }
    return render(request, "input_data/proforma_detail.html", context)
