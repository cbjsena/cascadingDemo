from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from input_data.models import ScenarioInfo
from input_data.services.proforma_service import ProformaService
from common import messages as msg
from common import constants as const
from common.menus import MENU_STRUCTURE

@login_required
def proforma_create(request):
    """Proforma Schedule 생성 View"""
    service = ProformaService()

    # 초기 컨텍스트
    context = {
        "scenarios": ScenarioInfo.objects.all().order_by('-created_at'),
        "rows": [],
        "header": {},
        "days": const.DAYS,

        "menu_structure": MENU_STRUCTURE,
        # "current_group": "Schedule",  # 사이드바에서 펼쳐놓을 그룹 (선택사항)
        "current_model": "proforma_schedule",  # 현재 활성화된 메뉴 (선택사항)
    }

    if request.method == "POST":
        action = request.POST.get('action')

        # 1. 파싱 (모든 액션 공통)
        rows = service.parse_rows(request)
        header = service.parse_header(request)

        # 2. 액션 처리
        if action == "add_row":
            rows = service.add_row(rows, header.get('scenario_id'))

        elif action == "insert_row":
            try:
                idx = int(request.POST.get('selected_index', -1))
                rows = service.insert_row(rows, idx)
            except ValueError:
                pass  # 인덱스 없음/오류 무시

        elif action == "delete_row":
            indices = request.POST.getlist('row_check')
            rows = service.delete_rows(rows, indices)

        elif action == "new":
            rows = []
            # Header 정보는 유지할지 초기화할지 정책에 따름 (여기선 유지)
            messages.info(request, msg.SCHEDULE_NEW_STARTED)

        elif action == "calculate":
            # [기능] 계산만 수행하고 화면 갱신
            rows = service.calculate_schedule(rows, header)
            messages.info(request, msg.SCHEDULE_CALCULATED)

        elif action == "save":
            # TODO save
            # [기능] 계산 수행 후 결과 저장
            # 1. 데이터 정합성을 위해 저장 전 한 번 더 계산
            rows = service.calculate_schedule(rows, header)

            try:
                # 2. DB 저장
                service.save_to_db(header, rows, request.user)
                messages.success(request, msg.SCHEDULE_SAVE_SUCCESS)
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
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            # 파일명: Lane_ProformaName_Schedule.xlsx
            lane = header.get('lane_code', 'Lane')
            pf_name = header.get('proforma_name', 'Schedule')
            filename = f"{lane}_{pf_name}_Proforma.xlsx"

            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        elif action == "csv":
            # Grid 형태의 CSV 다운로드

            # 1. 계산 최신화
            rows = service.calculate_schedule(rows, header)

            # 2. Service 호출
            # export_grid_csv:화면 , generate_db_csv: DB
            # csv_content = service.export_grid_csv(rows)
            csv_content = service.generate_db_csv(header, rows)

            # 3. 응답 생성
            response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')

            # 파일명: Lane_ProformaName_List.csv
            lane = header.get('lane_code', 'Lane')
            pf_name = header.get('proforma_name', 'Schedule')
            filename = f"{lane}_{pf_name}_List.csv"

            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        elif action == "close":
            return redirect('input_data:input_home')

        context['rows'] = rows
        context['header'] = header

    return render(request, 'input_data/proforma_create.html', context)


@login_required
def proforma_export(request):
    # Export Logic Placeholder
    messages.info(request, msg.FUNC_NOT_IMPLEMENTED.format(func_name="Export"))
    return redirect('input_data:proforma_create')

@login_required
def proforma_csv(request):
    # Export Logic Placeholder
    messages.info(request, msg.FUNC_NOT_IMPLEMENTED.format(func_name="Csv"))
    return redirect('input_data:proforma_csv')

@login_required
def proforma_upload(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        service = ProformaService()

        try:
            # 1. 엑셀 파싱
            header, rows = service.upload_excel(excel_file)

            # 2. [신규] Summary 계산
            # summary = service.calculate_summary(rows)

            # 3. Context에 summary 추가
            context = {
                "scenarios": ScenarioInfo.objects.all().order_by('-created_at'),
                "rows": rows,
                "header": header,
                # "summary": summary,  # <--- 화면으로 전달
                "days": const.DAYS,
                "menu_structure": MENU_STRUCTURE,
                "current_model": "proforma_schedule",
            }

            messages.success(request, msg.UPLOAD_SUCCESS)
            return render(request, 'input_data/proforma_create.html', context)

        except Exception as e:
            messages.error(request, msg.UPLOAD_FAIL.format(error=str(e)))
            return redirect('input_data:proforma_create')

    return redirect('input_data:proforma_create')


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
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    # 다운로드 파일명 설정
    response['Content-Disposition'] = 'attachment; filename="Proforma_Template.xlsx"'

    return response